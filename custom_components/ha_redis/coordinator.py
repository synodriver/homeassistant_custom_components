"""DataUpdateCoordinator for the Redis integration."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from redis import exceptions as redis_exceptions
import redis.asyncio as aioredis

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RedisData:
    """Runtime data shared by all Redis platforms."""

    client: aioredis.Redis
    lock: asyncio.Lock
    coordinator: DataUpdateCoordinator[dict[str, str]] | None = None
    last_updated: datetime | None = None


type RedisConfigEntry = ConfigEntry[RedisData]


def parse_redis_info(info: Mapping[str, Any] | str) -> dict[str, str]:
    """Parse a Redis INFO response into a flat string dictionary."""
    if isinstance(info, str):
        lines = info.splitlines()
    else:
        lines = [f"{key}:{value}" for key, value in info.items()]

    parsed: dict[str, str] = {}
    for line in lines:
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()

    keyspace_keys = 0
    keyspace_expires = 0
    database_count = 0
    for key, value in parsed.items():
        if not key.startswith("db") or not key[2:].isdigit():
            continue
        database_count += 1
        for item in value.split(","):
            if item.startswith("keys="):
                keyspace_keys += _to_int(item.removeprefix("keys="))
            elif item.startswith("expires="):
                keyspace_expires += _to_int(item.removeprefix("expires="))

    if database_count:
        parsed["keyspace_keys"] = str(keyspace_keys)
        parsed["keyspace_expires"] = str(keyspace_expires)
    parsed["database_count"] = str(database_count)
    return parsed


def _to_int(value: str) -> int:
    """Convert a Redis metric string to an int, treating parse failures as zero."""
    try:
        return int(value)
    except ValueError:
        return 0


class RedisUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Fetch Redis INFO data on an interval."""

    def __init__(
        self, hass: HomeAssistant, entry: RedisConfigEntry, data: RedisData
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=SCAN_INTERVAL,
        )
        self.redis_data = data

    async def _async_update_data(self) -> dict[str, str]:
        """Send INFO to Redis and return the parsed response."""
        try:
            async with self.redis_data.lock:
                info = await self.redis_data.client.info()
        except redis_exceptions.AuthenticationError as err:
            raise ConfigEntryAuthFailed("Redis authentication failed") from err
        except (redis_exceptions.RedisError, OSError) as err:
            raise UpdateFailed(f"Failed to query Redis: {err}") from err

        self.redis_data.last_updated = dt_util.utcnow()
        return parse_redis_info(info)

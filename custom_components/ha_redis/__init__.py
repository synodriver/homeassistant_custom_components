"""Support for monitoring a Redis server."""

import asyncio

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .client import create_redis_client
from .const import DOMAIN, MANUFACTURER, PLATFORMS
from .coordinator import RedisConfigEntry, RedisData, RedisUpdateCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Redis integration."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RedisConfigEntry) -> bool:
    """Set up Redis from a config entry."""
    assert entry.unique_id is not None
    client = create_redis_client(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
    )
    try:
        data = RedisData(client=client, lock=asyncio.Lock())
        coordinator = RedisUpdateCoordinator(hass, entry, data)
        data.coordinator = coordinator

        # Do not fail setup when Redis is unreachable: the device tracker reports
        # not_home and the coordinator keeps retrying in the background.
        await coordinator.async_refresh()

        entry.runtime_data = data

        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={
                (DOMAIN, entry.entry_id),
                (DOMAIN, entry.unique_id),
            },
            manufacturer=MANUFACTURER,
            model="Redis Server",
            name=entry.title,
            sw_version=(
                coordinator.data.get("redis_version") if coordinator.data else None
            ),
        )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await client.aclose()
        if hasattr(entry, "runtime_data"):
            object.__delattr__(entry, "runtime_data")
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RedisConfigEntry) -> bool:
    """Unload a Redis config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.aclose()
    return unload_ok

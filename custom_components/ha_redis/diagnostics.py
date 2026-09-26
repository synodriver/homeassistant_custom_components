"""Diagnostics support for the Redis integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import SCAN_INTERVAL
from .coordinator import RedisConfigEntry

TO_REDACT = {CONF_HOST, CONF_PASSWORD, CONF_USERNAME, "title", "unique_id"}

DIAGNOSTIC_INFO_KEYS = {
    "connected_clients",
    "database_count",
    "keyspace_expires",
    "keyspace_keys",
    "redis_mode",
    "redis_version",
    "role",
    "uptime_in_seconds",
    "used_memory",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RedisConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a Redis config entry."""
    data = entry.runtime_data
    coordinator = data.coordinator

    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "connection": {
            "connected": coordinator.last_update_success
            if coordinator is not None
            else None,
            "last_update": data.last_updated,
            "last_exception": type(coordinator.last_exception).__name__
            if coordinator is not None and coordinator.last_exception
            else None,
            "poll_interval_seconds": SCAN_INTERVAL.total_seconds(),
        },
        "info": {
            key: value
            for key, value in (coordinator.data or {}).items()
            if key in DIAGNOSTIC_INFO_KEYS
        }
        if coordinator is not None
        else {},
    }

"""Diagnostics for USTONE BLE devices."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .coordinator import UstoneCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[UstoneCoordinator]
) -> dict[str, Any]:
    """Return the latest parsed advertisement and coordinator state."""
    coordinator = entry.runtime_data
    advertisement = coordinator.latest
    return {
        "entry_id": entry.entry_id,
        "address": "**REDACTED**",
        "available": coordinator.available,
        "last_seen": coordinator.last_seen,
        "advertisement": (
            {
                "name": advertisement.name,
                "model": advertisement.model.value,
                "rssi": advertisement.rssi,
                "connectable": advertisement.connectable,
                "service_uuids": advertisement.service_uuids,
                "values": advertisement.values,
                "raw_data": advertisement.raw_data.hex(),
            }
            if advertisement is not None
            else None
        ),
    }

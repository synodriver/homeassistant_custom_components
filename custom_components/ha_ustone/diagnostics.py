"""Diagnostics for USTONE BLE devices."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from .coordinator import UstoneCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry[UstoneCoordinator]
) -> dict[str, Any]:
    """Return the latest parsed advertisement and coordinator state."""
    coordinator = entry.runtime_data
    advertisement = coordinator.latest
    if advertisement is not None:
        name = advertisement.name
        # HA 在没有本地名时会以地址作名称，macOS 的地址也可能是 UUID。
        if format_mac(name.casefold()) in {
            format_mac(entry.data[CONF_ADDRESS].casefold()),
            format_mac(advertisement.address.casefold()),
        }:
            name = "**REDACTED**"
    return {
        "entry_id": entry.entry_id,
        "address": "**REDACTED**",
        "available": coordinator.available,
        "last_seen": coordinator.last_seen,
        "advertisement": (
            {
                "name": name,
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

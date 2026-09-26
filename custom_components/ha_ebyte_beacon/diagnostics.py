"""Diagnostics support for Ebyte beacons."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from . import EbyteBeaconConfigEntry

TO_REDACT = {CONF_ADDRESS, "address", "mac", "known_devices", "last_seen"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: EbyteBeaconConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    client = coordinator.client
    adv = coordinator.data

    data = {
        "address": coordinator.address,
        "last_update_success": coordinator.last_update_success,
        "known_devices": list(client.get_seen_addresses()),
        "last_seen": client.last_seen_all(),
        "current_advertisement": asdict(adv) if adv else None,
    }
    return async_redact_data(data, TO_REDACT)

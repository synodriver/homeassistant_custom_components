"""The Ebyte Beacon integration.

Receives and parses the proprietary BLE advertising frame of the Chengdu Ebyte
EWD104-BT58 family of beacons (battery, temperature, humidity, acceleration)
and exposes them as Home Assistant entities.  Each discovered beacon becomes its
own config entry keyed on its Bluetooth address.
"""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import EbyteBeaconConfigEntry, EbyteBeaconCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ebyte Beacon integration services."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EbyteBeaconConfigEntry) -> bool:
    """Set up an Ebyte beacon from a config entry."""
    coordinator = EbyteBeaconCoordinator(hass, entry)
    entry.runtime_data = coordinator

    # Wire teardown before starting, so a failure mid-start is still cleaned up.
    entry.async_on_unload(coordinator.async_stop)

    # Start listening before the first refresh so Bluetooth history replay can
    # seed initial entity data when Home Assistant still has a recent packet.
    await coordinator.async_start()
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EbyteBeaconConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

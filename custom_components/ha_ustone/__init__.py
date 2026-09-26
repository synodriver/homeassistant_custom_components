"""The USTONE BLE integration."""

import logging

from homeassistant.config import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import UstoneCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-wide services."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one USTONE BLE device."""
    address = entry.unique_id
    if address is None:
        _LOGGER.error("USTONE config entry %s has no unique id", entry.entry_id)
        return False
    entry.runtime_data = coordinator = UstoneCoordinator(hass, address)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one USTONE BLE device."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

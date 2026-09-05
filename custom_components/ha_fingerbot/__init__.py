"""Support for Fingerbot HTTP devices."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import FingerbotConfigEntry, FingerbotCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-level services."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FingerbotConfigEntry) -> bool:
    """Set up one Fingerbot endpoint."""
    entry.runtime_data = FingerbotCoordinator(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: FingerbotConfigEntry
) -> bool:
    """Unload one Fingerbot endpoint."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

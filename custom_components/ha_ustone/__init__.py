"""The USTONE BLE integration."""

from homeassistant.config import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from .const import PLATFORMS
from .coordinator import UstoneCoordinator
from .services import async_setup_services


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-wide services."""
    async_setup_services(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entries to canonical Bluetooth unique IDs."""
    if entry.version < 2:
        hass.config_entries.async_update_entry(
            entry,
            unique_id=format_mac(entry.data[CONF_ADDRESS]),
            version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one USTONE BLE device."""
    address = entry.data[CONF_ADDRESS]
    entry.runtime_data = coordinator = UstoneCoordinator(hass, address)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one USTONE BLE device."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

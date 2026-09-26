# -*- coding: utf-8 -*-
"""
Copyright (c) 2008-2026 synodriver <diguohuangjiajinweijun@gmail.com>
"""

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_ADDRESS, DOMAIN, PLATFORMS
from .coordinator import GalakuConfigEntry, GalakuCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from config entries."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GalakuConfigEntry) -> bool:
    """Set up one GALAKU device."""
    service_info = bluetooth.async_last_service_info(
        hass, entry.data[CONF_ADDRESS], connectable=True
    )
    coordinator = GalakuCoordinator(hass, entry, service_info)
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_stop)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry[GalakuCoordinator]
) -> bool:
    """Unload one GALAKU device."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

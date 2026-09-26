"""Bluetooth presence tracker for GALAKU."""

from typing import override

from homeassistant.components.device_tracker import BaseScannerEntity, SourceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GalakuConfigEntry
from .entity import GalakuEntity

DESCRIPTION = EntityDescription(key="device_tracker", translation_key="device_tracker")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GalakuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the GALAKU presence tracker."""
    async_add_entities([GalakuTracker(entry.runtime_data, DESCRIPTION)])


class GalakuTracker(GalakuEntity, BaseScannerEntity):
    """Represent recent Bluetooth presence as home/not_home."""

    _attr_name = None
    _attr_source_type = SourceType.BLUETOOTH_LE
    _attr_translation_key = "device_tracker"

    @property
    @override
    def available(self) -> bool:
        """Keep the entity available when the device is away."""
        return True

    @property
    @override
    def is_connected(self) -> bool:
        """Return recent advertisement presence."""
        return self.coordinator.advertisement_available

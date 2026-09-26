"""Device tracker platform for Ebyte beacons."""

from __future__ import annotations

from typing import override

from homeassistant.components.device_tracker import BaseScannerEntity, SourceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EbyteBeaconConfigEntry, EbyteBeaconCoordinator
from .entity import EbyteBeaconEntity

TRACKER_DESCRIPTION = EntityDescription(key="device_tracker")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EbyteBeaconConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Ebyte beacon tracker."""
    coordinator = entry.runtime_data
    async_add_entities([EbyteBeaconTrackerEntity(coordinator)])


class EbyteBeaconTrackerEntity(EbyteBeaconEntity, BaseScannerEntity):
    """Representation of an Ebyte beacon tracker."""

    _attr_name = None
    _attr_source_type: SourceType = SourceType.BLUETOOTH_LE
    _attr_translation_key = "device_tracker"

    def __init__(self, coordinator: EbyteBeaconCoordinator) -> None:
        """Initialise the tracker entity."""
        super().__init__(coordinator, TRACKER_DESCRIPTION)
        self._attr_unique_id = format_mac(coordinator.address)

    @property
    @override
    def available(self) -> bool:
        """Return whether the tracker can report presence."""
        return self._advertisement is not None

    @property
    @override
    def is_connected(self) -> bool:
        """Return true if the beacon is currently considered present."""
        return self.coordinator.last_update_success and self._advertisement is not None

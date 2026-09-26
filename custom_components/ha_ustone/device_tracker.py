"""Bluetooth device tracker for USTONE devices."""

from typing import override

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import UstoneConfigEntry, UstoneCoordinator
from .entity import device_info_from_coordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UstoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one always-available USTONE tracker."""
    async_add_entities([UstoneDeviceTracker(entry.runtime_data)])


class UstoneDeviceTracker(TrackerEntity):
    """Represent online/offline status without becoming unavailable."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "device_tracker"
    _attr_source_type = SourceType.BLUETOOTH_LE
    _attr_should_poll = False

    def __init__(self, coordinator: UstoneCoordinator) -> None:
        """Initialize the tracker."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_device_tracker"

    @override
    async def async_added_to_hass(self) -> None:
        """Subscribe to online-state changes."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the shared USTONE device record."""
        return device_info_from_coordinator(self.coordinator)

    @property
    @override
    def available(self) -> bool:
        """The tracker stays available so offline is represented by not_home."""
        return True

    @property
    @override
    def state(self) -> str:
        """Return the current tracker state."""
        return STATE_HOME if self.coordinator.available else STATE_NOT_HOME

"""Device tracker reporting whether the Redis server is online."""

from typing import override

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import BaseScannerEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import RedisConfigEntry, RedisUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RedisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a Redis device tracker from a config entry."""
    coordinator = entry.runtime_data.coordinator
    assert isinstance(coordinator, RedisUpdateCoordinator)
    async_add_entities([RedisDeviceTracker(coordinator, entry)])


class RedisDeviceTracker(BaseScannerEntity):
    """Track whether the Redis server is connected."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_source_type = SourceType.ROUTER
    _attr_translation_key = "redis_server"

    def __init__(
        self, coordinator: RedisUpdateCoordinator, entry: RedisConfigEntry
    ) -> None:
        """Initialize the device tracker."""
        assert entry.unique_id is not None
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_server"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (DOMAIN, entry.entry_id),
                (DOMAIN, entry.unique_id),
            },
        )

    @property
    @override
    def available(self) -> bool:
        """Keep the tracker available so an offline server shows not_home."""
        return True

    @property
    @override
    def is_connected(self) -> bool:
        """Return True when the last Redis INFO query succeeded."""
        return self.coordinator.last_update_success

    @override
    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update the tracker when the connection state changes."""
        self.async_write_ha_state()

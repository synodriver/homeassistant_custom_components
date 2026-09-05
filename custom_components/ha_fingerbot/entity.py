"""Shared entity implementation for Fingerbot platforms."""

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import FingerbotCoordinator


class FingerbotEntity(CoordinatorEntity[FingerbotCoordinator]):
    """Base entity backed by the single Fingerbot coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: FingerbotCoordinator, description: EntityDescription
    ) -> None:
        """Initialize a translated entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.endpoint}_{description.key}"
        self._attr_device_info = coordinator.device_info


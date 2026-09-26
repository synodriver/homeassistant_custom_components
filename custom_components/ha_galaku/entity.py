"""Shared entity base for GALAKU platforms."""

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import GalakuCoordinator


class GalakuEntity(CoordinatorEntity[GalakuCoordinator]):
    """Base class ensuring every platform uses the one coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GalakuCoordinator, description: EntityDescription
    ) -> None:
        """Initialise a translated entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._attr_device_info = coordinator.device_info

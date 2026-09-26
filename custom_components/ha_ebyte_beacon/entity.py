"""Base entity for Ebyte Beacon.

All entities are backed by :class:`EbyteBeaconCoordinator` and share the same
device-registry entry, keyed on the beacon's Bluetooth address.  Availability
follows the coordinator: a beacon is available while it keeps advertising and
is marked offline (unavailable) once it falls silent past the timeout.
"""

from __future__ import annotations

from typing import override

from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EbyteBeaconCoordinator
from .ebyte_beacon import EbyteBeaconAdvertisement


class EbyteBeaconEntity(CoordinatorEntity[EbyteBeaconCoordinator]):
    """Common base class for Ebyte beacon entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EbyteBeaconCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        formatted_mac = format_mac(coordinator.address)
        self._attr_unique_id = f"{formatted_mac}_{entity_description.key}"

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device information for the beacon."""
        formatted_mac = format_mac(self.coordinator.address)
        return DeviceInfo(
            identifiers={(DOMAIN, formatted_mac)},
            name=self.coordinator.name,
            manufacturer="Ebyte",
            model=self._device_model,
            connections={(CONNECTION_BLUETOOTH, self.coordinator.address)},
        )

    @property
    def _advertisement(self) -> EbyteBeaconAdvertisement | None:
        """Return the latest parsed advertisement, if any."""
        return self.coordinator.data

    @property
    def _device_model(self) -> str | None:
        """Return the device model, inferred from the frame when possible."""
        adv = self._advertisement
        if adv and adv.has_sensors:
            return "EWD104-BT58 (sensor)"
        return "EWD104-BT58"

    @property
    @override
    def available(self) -> bool:
        """Return whether the beacon is currently considered online."""
        if self._attr_translation_key == "device_tracker":
            return True
        return self.coordinator.last_update_success and self._advertisement is not None

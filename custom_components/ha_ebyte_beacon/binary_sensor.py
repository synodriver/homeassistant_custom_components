"""Binary sensor platform for Ebyte beacons."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)

from .const import DOMAIN
from .coordinator import EbyteBeaconConfigEntry, EbyteBeaconCoordinator
from .ebyte_beacon import EbyteBeaconAdvertisement
from .entity import EbyteBeaconEntity


@dataclass(kw_only=True, frozen=True)
class EbyteBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Description for Ebyte beacon binary sensors."""

    #: Whether this measurement is only present on sensor-bearing variants.
    sensor_variant_only: bool = False
    value_fn: Callable[[EbyteBeaconAdvertisement], bool | None]


BINARY_SENSORS: tuple[EbyteBinarySensorEntityDescription, ...] = (
    EbyteBinarySensorEntityDescription(
        key="connectable",
        translation_key="connectable",
        sensor_variant_only=True,
        value_fn=lambda adv: adv.connectable,
    ),
    EbyteBinarySensorEntityDescription(
        key="encrypted",
        translation_key="encrypted",
        sensor_variant_only=True,
        value_fn=lambda adv: adv.encrypted,
    ),
)

BINARY_SENSOR_DESCRIPTIONS_BY_KEY = {
    description.key: description for description in BINARY_SENSORS
}
SENSOR_VARIANT_BINARY_SENSOR_KEYS = {
    description.key for description in BINARY_SENSORS if description.sensor_variant_only
}


def _description_applies(
    description: EbyteBinarySensorEntityDescription,
    advertisement: EbyteBeaconAdvertisement | None,
) -> bool:
    """Return whether a binary sensor description applies to the latest model."""
    if advertisement is None:
        return not description.sensor_variant_only
    if description.sensor_variant_only:
        return advertisement.has_sensors
    return True


def _unique_id(coordinator: EbyteBeaconCoordinator, description_key: str) -> str:
    """Return the stable unique id for a binary sensor description."""
    return f"{format_mac(coordinator.address)}_{description_key}"


def _remove_registry_entity(
    hass: HomeAssistant,
    coordinator: EbyteBeaconCoordinator,
    description_key: str,
) -> None:
    """Remove a stale binary sensor entity registry entry if one exists."""
    entity_registry: er.EntityRegistry = er.async_get(hass)  # type: ignore[no-untyped-call]
    if entity_id := entity_registry.async_get_entity_id(
        BINARY_SENSOR_DOMAIN, DOMAIN, _unique_id(coordinator, description_key)
    ):
        entity_registry.async_remove(entity_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EbyteBeaconConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Ebyte beacon binary sensors."""
    coordinator = entry.runtime_data
    platform = async_get_current_platform()
    added_keys: set[str] = set()
    pending_remove_tasks: dict[str, asyncio.Task[None]] = {}

    @callback
    def _async_still_applies(key: str) -> bool:
        """Return whether a key still applies to the latest advertisement."""
        return _description_applies(
            BINARY_SENSOR_DESCRIPTIONS_BY_KEY[key], coordinator.data
        )

    @callback
    def _async_remove_entity(key: str, entity_id: str) -> None:
        """Remove a stale loaded entity and its registry entry."""
        if key in pending_remove_tasks:
            return

        async def _async_remove_loaded_entity() -> None:
            removed = False
            try:
                if _async_still_applies(key):
                    return
                if entity_id in platform.entities:
                    await platform.async_remove_entity(entity_id)
                    removed = True
                if _async_still_applies(key):
                    return
                _remove_registry_entity(hass, coordinator, key)
                removed = True
            finally:
                if pending_remove_tasks.get(key) is task:
                    pending_remove_tasks.pop(key, None)
                if removed:
                    added_keys.discard(key)
                    if _async_still_applies(key):
                        _async_add_current_model_entities()

        task = hass.async_create_task(_async_remove_loaded_entity())
        pending_remove_tasks[key] = task

    @callback
    def _async_add_current_model_entities() -> None:
        """Add/remove entities so they match the latest advertised model."""
        advertisement = coordinator.data
        applicable_keys = {
            description.key
            for description in BINARY_SENSORS
            if _description_applies(description, advertisement)
        }

        new_keys = applicable_keys - added_keys
        if new_keys:
            added_keys.update(new_keys)
            async_add_entities(
                EbyteBeaconBinarySensor(
                    coordinator, BINARY_SENSOR_DESCRIPTIONS_BY_KEY[key]
                )
                for key in new_keys
            )

        stale_keys = added_keys - applicable_keys
        for key in stale_keys:
            entity_id = er.async_get(hass).async_get_entity_id(
                BINARY_SENSOR_DOMAIN, DOMAIN, _unique_id(coordinator, key)
            )
            if entity_id is None:
                added_keys.discard(key)
                continue
            _async_remove_entity(key, entity_id)

        if advertisement is None:
            return

        for key in SENSOR_VARIANT_BINARY_SENSOR_KEYS:
            if (
                key not in applicable_keys
                and key not in added_keys
                and key not in pending_remove_tasks
            ):
                _remove_registry_entity(hass, coordinator, key)

    _async_add_current_model_entities()
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_current_model_entities)
    )


class EbyteBeaconBinarySensor(EbyteBeaconEntity, BinarySensorEntity):
    """Representation of an Ebyte beacon binary sensor."""

    entity_description: EbyteBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        adv = self._advertisement
        if adv is None:
            return None
        return self.entity_description.value_fn(adv)

    @property
    @override
    def available(self) -> bool:
        """Return whether this binary sensor is available."""
        adv = self._advertisement
        if adv is None:
            return False
        return self.coordinator.last_update_success

"""Sensor platform for Ebyte beacons."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import EbyteBeaconConfigEntry, EbyteBeaconCoordinator
from .ebyte_beacon import EbyteBeaconAdvertisement
from .entity import EbyteBeaconEntity


@dataclass(kw_only=True, frozen=True)
class EbyteSensorEntityDescription(SensorEntityDescription):
    """Description for Ebyte beacon sensor entities."""

    #: Whether this measurement is only present on sensor-bearing variants.
    sensor_variant_only: bool = False
    #: Whether this measurement is only present on no-sensor/iBeacon-style frames.
    no_sensor_variant_only: bool = False
    #: Callable returning whether the latest parsed advertisement includes this value.
    available_fn: Callable[[EbyteBeaconAdvertisement], bool] | None = None
    #: Callable extracting the value from the parsed advertisement.
    value_fn: Callable[[EbyteBeaconAdvertisement], StateType]


SENSORS: tuple[EbyteSensorEntityDescription, ...] = (
    EbyteSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,  # type: ignore[assignment]
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda adv: adv.sensors.battery_percent,
    ),
    EbyteSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        sensor_variant_only=True,
        available_fn=lambda adv: adv.sensors.temperature is not None,
        value_fn=lambda adv: adv.sensors.temperature,
    ),
    EbyteSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,  # type: ignore[assignment]
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        sensor_variant_only=True,
        available_fn=lambda adv: adv.sensors.humidity is not None,
        value_fn=lambda adv: adv.sensors.humidity,
    ),
    EbyteSensorEntityDescription(
        key="acceleration_x",
        translation_key="acceleration_x",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="g",
        sensor_variant_only=True,
        available_fn=lambda adv: adv.sensors.acceleration_x is not None,
        value_fn=lambda adv: (
            adv.sensors.acceleration_x / 16384
            if adv.sensors.acceleration_x is not None
            else None
        ),
    ),
    EbyteSensorEntityDescription(
        key="acceleration_y",
        translation_key="acceleration_y",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="g",
        sensor_variant_only=True,
        available_fn=lambda adv: adv.sensors.acceleration_y is not None,
        value_fn=lambda adv: (
            adv.sensors.acceleration_y / 16384
            if adv.sensors.acceleration_y is not None
            else None
        ),
    ),
    EbyteSensorEntityDescription(
        key="acceleration_z",
        translation_key="acceleration_z",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="g",
        sensor_variant_only=True,
        available_fn=lambda adv: adv.sensors.acceleration_z is not None,
        value_fn=lambda adv: (
            adv.sensors.acceleration_z / 16384
            if adv.sensors.acceleration_z is not None
            else None
        ),
    ),
    EbyteSensorEntityDescription(
        key="signal_strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda adv: adv.rssi,
    ),
    # iBeacon-style fields carried by the no-sensor frame.
    EbyteSensorEntityDescription(
        key="major",
        translation_key="major",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        no_sensor_variant_only=True,
        value_fn=lambda adv: adv.major,
    ),
    EbyteSensorEntityDescription(
        key="minor",
        translation_key="minor",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        no_sensor_variant_only=True,
        value_fn=lambda adv: adv.minor,
    ),
    EbyteSensorEntityDescription(
        key="tx_power_index",
        translation_key="tx_power_index",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        no_sensor_variant_only=True,
        value_fn=lambda adv: adv.tx_power_index,
    ),
    EbyteSensorEntityDescription(
        key="advertising_interval",
        translation_key="advertising_interval",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        no_sensor_variant_only=True,
        value_fn=lambda adv: adv.advertising_interval_ms,
    ),
)

SENSOR_DESCRIPTIONS_BY_KEY = {description.key: description for description in SENSORS}
SENSOR_VARIANT_KEYS = {
    description.key for description in SENSORS if description.sensor_variant_only
}
NO_SENSOR_VARIANT_KEYS = {
    description.key for description in SENSORS if description.no_sensor_variant_only
}


def _description_applies(
    description: EbyteSensorEntityDescription,
    advertisement: EbyteBeaconAdvertisement | None,
) -> bool:
    """Return whether a sensor description applies to the latest known model."""
    if advertisement is None:
        return (
            not description.sensor_variant_only
            and not description.no_sensor_variant_only
        )
    if description.sensor_variant_only and not advertisement.has_sensors:
        return False
    if description.no_sensor_variant_only and advertisement.has_sensors:
        return False
    if description.available_fn is not None:
        return description.available_fn(advertisement)
    return True


def _unique_id(coordinator: EbyteBeaconCoordinator, description_key: str) -> str:
    """Return the stable unique id for a sensor description."""
    return f"{format_mac(coordinator.address)}_{description_key}"


def _entity_id(
    entity_registry: er.EntityRegistry,
    coordinator: EbyteBeaconCoordinator,
    description_key: str,
) -> str | None:
    """Return the entity id for a sensor description if one exists."""
    return entity_registry.async_get_entity_id(
        SENSOR_DOMAIN, DOMAIN, _unique_id(coordinator, description_key)
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EbyteBeaconConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Ebyte beacon sensors."""
    coordinator = entry.runtime_data
    platform = async_get_current_platform()
    entity_registry: er.EntityRegistry = er.async_get(hass)  # type: ignore[assignment]
    added_keys: set[str] = set()
    pending_remove_tasks: dict[str, asyncio.Task[None]] = {}

    @callback
    def _async_still_applies(key: str) -> bool:
        """Return whether a key still applies to the latest advertisement."""
        return _description_applies(SENSOR_DESCRIPTIONS_BY_KEY[key], coordinator.data)

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
                if entity_registry.async_get(entity_id) is not None:
                    entity_registry.async_remove(entity_id)
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
            for description in SENSORS
            if _description_applies(description, advertisement)
        }

        new_keys = applicable_keys - added_keys
        if new_keys:
            added_keys.update(new_keys)
            async_add_entities(
                EbyteBeaconSensor(coordinator, SENSOR_DESCRIPTIONS_BY_KEY[key])
                for key in new_keys
            )

        stale_keys = added_keys - applicable_keys
        for key in stale_keys:
            entity_id = _entity_id(entity_registry, coordinator, key)
            if entity_id is None:
                added_keys.discard(key)
                continue
            _async_remove_entity(key, entity_id)

        if advertisement is None:
            return

        for key in SENSOR_VARIANT_KEYS | NO_SENSOR_VARIANT_KEYS:
            if (
                key not in applicable_keys
                and key not in added_keys
                and key not in pending_remove_tasks
                and (entity_id := _entity_id(entity_registry, coordinator, key))
                and entity_id not in platform.entities
            ):
                entity_registry.async_remove(entity_id)

    _async_add_current_model_entities()
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_current_model_entities)
    )


class EbyteBeaconSensor(EbyteBeaconEntity, SensorEntity):
    """Representation of an Ebyte beacon sensor."""

    entity_description: EbyteSensorEntityDescription

    @property
    @override
    def native_value(self) -> StateType:
        """Return the sensor's value."""
        adv = self._advertisement
        if adv is None:
            return None
        return self.entity_description.value_fn(adv)

    @property
    @override
    def available(self) -> bool:
        """Return whether the sensor is available."""
        adv = self._advertisement
        if adv is None:
            return False
        return self.coordinator.last_update_success

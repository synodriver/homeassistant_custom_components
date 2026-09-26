"""Sensor entities for USTONE BLE advertisements."""

from collections.abc import Callable
from typing import Any, override

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
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
    LIGHT_LUX,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import UstoneConfigEntry
from .entity import device_info_from_advertisement
from .ustone_ble import UstoneAdvertisement


SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "battery": SensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "humidity": SensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "illuminance": SensorEntityDescription(
        key="illuminance",
        translation_key="illuminance",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "pressure": SensorEntityDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.PA,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "signal_strength": SensorEntityDescription(
        key="signal_strength",
        translation_key="signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
}

SENSOR_VALUE_FNS: dict[str, Callable[[UstoneAdvertisement], int | float | None]] = {
    "battery": lambda adv: _number(adv.values.get("battery")),
    "temperature": lambda adv: _number(adv.values.get("temperature")),
    "humidity": lambda adv: _number(adv.values.get("humidity")),
    "illuminance": lambda adv: _number(adv.values.get("illuminance")),
    "pressure": lambda adv: _number(adv.values.get("pressure")),
    "signal_strength": lambda adv: adv.rssi,
}


def _number(value: Any) -> int | float | None:
    """Return numeric values while dropping absent protocol fields."""
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def sensor_update_to_bluetooth_data_update(
    advertisement: UstoneAdvertisement,
) -> PassiveBluetoothDataUpdate[int | float]:
    """Convert a decoded advertisement to passive sensor data."""
    entity_data: dict[PassiveBluetoothEntityKey, int | float] = {}
    descriptions: dict[PassiveBluetoothEntityKey, SensorEntityDescription] = {}
    for key, description in SENSOR_DESCRIPTIONS.items():
        value = SENSOR_VALUE_FNS[key](advertisement)
        if value is None:
            continue
        entity_key = PassiveBluetoothEntityKey(key, None)
        entity_data[entity_key] = value
        descriptions[entity_key] = description
    return PassiveBluetoothDataUpdate(
        devices={None: device_info_from_advertisement(advertisement)},
        entity_descriptions=descriptions,
        entity_data=entity_data,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UstoneConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up USTONE sensor entities."""
    processor = PassiveBluetoothDataProcessor(sensor_update_to_bluetooth_data_update)
    entry.async_on_unload(
        processor.async_add_entities_listener(UstoneSensorEntity, async_add_entities)
    )
    entry.async_on_unload(
        entry.runtime_data.async_register_processor(processor, SensorEntityDescription)
    )


class UstoneSensorEntity(
    PassiveBluetoothProcessorEntity[
        PassiveBluetoothDataProcessor[int | float, UstoneAdvertisement]
    ],
    SensorEntity,
):
    """A USTONE sensor backed by passive advertisement data."""

    @property
    @override
    def native_value(self) -> int | float | None:
        """Return the latest sensor value."""
        return self.processor.entity_data.get(self.entity_key)

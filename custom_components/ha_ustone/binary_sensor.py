"""Binary sensors for USTONE BLE devices."""

from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import UstoneConfigEntry
from .entity import device_info_from_advertisement
from .ustone_ble import UstoneAdvertisement


STATIC_DESCRIPTIONS: dict[str, BinarySensorEntityDescription] = {
    "occupancy": BinarySensorEntityDescription(
        key="occupancy",
        translation_key="occupancy",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
    "door": BinarySensorEntityDescription(
        key="door",
        translation_key="door",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
    "water_leak": BinarySensorEntityDescription(
        key="water_leak",
        translation_key="water_leak",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
}


def _description(key: str) -> BinarySensorEntityDescription:
    """Return a matching binary description, including dynamic buttons."""
    if key in STATIC_DESCRIPTIONS:
        return STATIC_DESCRIPTIONS[key]
    return BinarySensorEntityDescription(
        key=key,
        translation_key="button",
    )


def binary_sensor_update_to_bluetooth_data_update(
    advertisement: UstoneAdvertisement,
) -> PassiveBluetoothDataUpdate[bool]:
    """Convert a decoded advertisement to passive binary sensor data."""
    values = {
        key: value
        for key, value in advertisement.values.items()
        if isinstance(value, bool)
    }
    entity_data = {
        PassiveBluetoothEntityKey(key, None): value for key, value in values.items()
    }
    descriptions = {
        PassiveBluetoothEntityKey(key, None): _description(key)
        for key in values
    }
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
    """Set up USTONE binary sensors."""
    processor = PassiveBluetoothDataProcessor(
        binary_sensor_update_to_bluetooth_data_update
    )
    entry.async_on_unload(
        processor.async_add_entities_listener(
            UstoneBinarySensorEntity, async_add_entities
        )
    )
    entry.async_on_unload(
        entry.runtime_data.async_register_processor(
            processor, BinarySensorEntityDescription
        )
    )


class UstoneBinarySensorEntity(
    PassiveBluetoothProcessorEntity[
        PassiveBluetoothDataProcessor[bool, UstoneAdvertisement]
    ],
    BinarySensorEntity,
):
    """A USTONE binary sensor."""

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the latest boolean value."""
        return self.processor.entity_data.get(self.entity_key)

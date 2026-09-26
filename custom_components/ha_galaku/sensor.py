"""Diagnostic sensors for GALAKU."""

from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import GalakuConfigEntry
from .entity import GalakuEntity

DESCRIPTION = SensorEntityDescription(
    key="signal_strength",
    translation_key="signal_strength",
    device_class=SensorDeviceClass.SIGNAL_STRENGTH,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GalakuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the signal-strength sensor."""
    async_add_entities([GalakuSignalStrengthSensor(entry.runtime_data, DESCRIPTION)])


class GalakuSignalStrengthSensor(GalakuEntity, SensorEntity):
    """Report the latest Bluetooth RSSI."""

    @property
    @override
    def native_value(self) -> StateType:
        """Return RSSI in dBm, if an advertisement is available."""
        return self.coordinator.rssi

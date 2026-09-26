"""Vibration intensity number entity."""

from typing import override

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GalakuConfigEntry, GalakuCoordinator
from .entity import GalakuEntity

DESCRIPTION = NumberEntityDescription(
    key="intensity",
    translation_key="vibration_intensity",
    native_min_value=0,
    native_max_value=100,
    native_step=1,
    native_unit_of_measurement=PERCENTAGE,
)

ELECTRIC_DESCRIPTION = NumberEntityDescription(
    key="electric_intensity",
    translation_key="electric_intensity",
    native_min_value=0,
    native_max_value=100,
    native_step=1,
    native_unit_of_measurement=PERCENTAGE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GalakuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the intensity control."""
    async_add_entities(
        [
            GalakuVibrationNumber(entry.runtime_data, DESCRIPTION),
            GalakuElectricNumber(entry.runtime_data, ELECTRIC_DESCRIPTION),
        ]
    )


class GalakuVibrationNumber(GalakuEntity, NumberEntity):
    """Set the GK36 vibration intensity."""

    @property
    @override
    def native_value(self) -> float:
        """Return the locally commanded intensity."""
        return float(self.coordinator.vibration_level)

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Send a new intensity to the device."""
        await self.coordinator.async_set_vibration_level(value)


class GalakuElectricNumber(GalakuEntity, NumberEntity):
    """Set the GK36 electric stimulation intensity."""

    @property
    @override
    def native_value(self) -> float:
        """Return the locally commanded electric intensity."""
        return float(self.coordinator.electric_level)

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Send a new electric intensity to the device."""
        await self.coordinator.async_set_electric_level(value)

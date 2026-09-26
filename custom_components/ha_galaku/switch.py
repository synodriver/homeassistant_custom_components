"""Output switch entity for GALAKU."""

from typing import override, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GalakuConfigEntry
from .entity import GalakuEntity

DESCRIPTION = SwitchEntityDescription(key="output", translation_key="output")
ELECTRIC_DESCRIPTION = SwitchEntityDescription(
    key="electric_output", translation_key="electric_output"
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GalakuConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the output switch."""
    async_add_entities(
        [
            GalakuVibrationSwitch(entry.runtime_data, DESCRIPTION),
            GalakuElectricSwitch(entry.runtime_data, ELECTRIC_DESCRIPTION),
        ]
    )


class GalakuVibrationSwitch(GalakuEntity, SwitchEntity):
    """Turn GALAKU vibration on or off."""

    @property
    @override
    def is_on(self) -> bool:
        """Return whether a non-zero level is active."""
        return self.coordinator.vibration_level > 0

    @override
    async def async_turn_on(self, **kwargs: object) -> None:
        """Restore the most recently used non-zero level."""
        del kwargs
        await self.coordinator.async_set_vibration_level(
            self.coordinator.last_active_vibration_level
        )

    @override
    async def async_turn_off(self, **kwargs: object) -> None:
        """Stop all output."""
        del kwargs
        await self.coordinator.async_set_vibration_level(0)


class GalakuElectricSwitch(GalakuEntity, SwitchEntity):
    """Turn GALAKU electric stimulation on or off."""

    @property
    @override
    def is_on(self) -> bool:
        """Return whether electric stimulation is active."""
        return self.coordinator.electric_level > 0

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Restore the most recently used electric level."""
        await self.coordinator.async_set_electric_level(
            self.coordinator.last_active_electric_level
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop electric stimulation only."""
        await self.coordinator.async_set_electric_level(0)

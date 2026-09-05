"""Fingerbot action button."""

from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FingerbotConfigEntry
from .entity import FingerbotEntity

DESCRIPTION = ButtonEntityDescription(
    key="press",
    translation_key="press",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FingerbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Fingerbot action button."""
    async_add_entities([FingerbotButton(entry.runtime_data, DESCRIPTION)])


class FingerbotButton(FingerbotEntity, ButtonEntity):
    """Press the Fingerbot with the configured number values."""

    @override
    async def async_press(self) -> None:
        """Send the current parameters to the device."""
        await self.coordinator.async_press()

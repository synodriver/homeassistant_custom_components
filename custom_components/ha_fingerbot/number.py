"""Number entities used to configure Fingerbot presses."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    PARAM_CONTINUE_NUM,
    PARAM_CONTINUE_TIME,
    PARAM_LAST_TIME,
    PARAM_PUSH_DEPTH,
)
from .coordinator import FingerbotConfigEntry
from .entity import FingerbotEntity


@dataclass(frozen=True, kw_only=True)
class FingerbotNumberDescription(NumberEntityDescription):
    """Describe a Fingerbot parameter number."""

    parameter: str


NUMBER_DESCRIPTIONS: tuple[FingerbotNumberDescription, ...] = (
    FingerbotNumberDescription(
        key="push_depth",
        translation_key="push_depth",
        parameter=PARAM_PUSH_DEPTH,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
    ),
    FingerbotNumberDescription(
        key="last_time",
        translation_key="last_time",
        parameter=PARAM_LAST_TIME,
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
    FingerbotNumberDescription(
        key="continue_num",
        translation_key="continue_num",
        parameter=PARAM_CONTINUE_NUM,
        native_min_value=1,
        native_max_value=20,
        native_step=1,
    ),
    FingerbotNumberDescription(
        key="continue_time",
        translation_key="continue_time",
        parameter=PARAM_CONTINUE_TIME,
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FingerbotConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up all four Fingerbot parameter controls."""
    async_add_entities(
        FingerbotNumber(entry.runtime_data, description)
        for description in NUMBER_DESCRIPTIONS
    )


class FingerbotNumber(FingerbotEntity, NumberEntity):
    """Edit one parameter used by the next press."""

    entity_description: FingerbotNumberDescription

    @property
    @override
    def native_value(self) -> float:
        """Return the current configured value."""
        values = {
            PARAM_PUSH_DEPTH: self.coordinator.data.push_depth,
            PARAM_LAST_TIME: self.coordinator.data.last_time,
            PARAM_CONTINUE_NUM: self.coordinator.data.continue_num,
            PARAM_CONTINUE_TIME: self.coordinator.data.continue_time,
        }
        return float(values[self.entity_description.parameter])

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Store a parameter for the next press."""
        await self.coordinator.async_set_parameter(
            self.entity_description.parameter, value
        )

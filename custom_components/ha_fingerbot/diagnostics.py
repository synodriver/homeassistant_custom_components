"""Diagnostics for Fingerbot HTTP devices."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_ENDPOINT
from .coordinator import FingerbotConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FingerbotConfigEntry
) -> dict[str, Any]:
    """Return safe state without exposing the configured endpoint host."""
    coordinator = entry.runtime_data
    return {
        "config_entry": async_redact_data(
            entry.as_dict(), {CONF_ENDPOINT, "title", "unique_id"}
        ),
        "coordinator": {
            "last_command_success": coordinator.last_command_success,
            "parameters": coordinator.data.as_query(),
        },
    }

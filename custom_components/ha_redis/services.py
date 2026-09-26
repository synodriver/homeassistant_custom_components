"""Services for the Redis integration."""

import shlex
from typing import Any, cast

from redis import exceptions as redis_exceptions
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_COMMAND, ATTR_DEVICE_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    selector,
)
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN, SERVICE_SEND_COMMAND
from .coordinator import RedisConfigEntry, RedisData

SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): selector.DeviceSelector({"integration": DOMAIN}),
        vol.Required(ATTR_COMMAND): cv.string,
    },
    extra=vol.PREVENT_EXTRA,
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the Redis integration."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SEND_COMMAND,
        async_send_command,
        SEND_COMMAND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def _get_config_entry(hass: HomeAssistant, device_id: str) -> RedisConfigEntry:
    """Return the Redis config entry owning a device."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
        )

    # TODO: Use this when Home Assistant 2026.8 is the minimum supported version.
    # entry = hass.config_entries.async_get_entry(device.config_entry_id)
    entry = None
    for domain, unique_id in device.identifiers:
        if domain == DOMAIN and (
            entry := hass.config_entries.async_entry_for_domain_unique_id(
                DOMAIN, unique_id
            )
        ):
            break
    if entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
        )

    return cast(RedisConfigEntry, entry)


def _get_runtime_data(entry: RedisConfigEntry) -> RedisData:
    """Return runtime data for a loaded Redis config entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    if entry.state is not ConfigEntryState.LOADED or runtime_data is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_loaded",
        )
    return cast(RedisData, runtime_data)


def _to_json_value(value: Any) -> Any:
    """Convert a Redis response to a JSON serializable value."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            _to_json_value(key): _to_json_value(item) for key, item in value.items()
        }
    return str(value)


async def async_send_command(call: ServiceCall) -> ServiceResponse:
    """Send an arbitrary Redis command and return its response."""
    entry = _get_config_entry(call.hass, call.data[ATTR_DEVICE_ID])
    data = _get_runtime_data(entry)

    try:
        args = shlex.split(call.data[ATTR_COMMAND])
    except ValueError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_command",
        ) from err

    if not args:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="empty_command",
        )

    try:
        async with data.lock:
            response = await data.client.execute_command(*args)
    except redis_exceptions.ResponseError as err:
        raise HomeAssistantError(f"Redis command failed: {err}") from err
    except (redis_exceptions.RedisError, OSError) as err:
        raise HomeAssistantError(f"Redis connection failed: {err}") from err

    return cast(JsonObjectType, {"response": _to_json_value(response)})

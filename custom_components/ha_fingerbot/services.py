"""Services for controlling Fingerbot devices."""

from typing import cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import DeviceSelector

from .const import (
    DOMAIN,
    PARAM_CONTINUE_NUM,
    PARAM_CONTINUE_TIME,
    PARAM_LAST_TIME,
    PARAM_PUSH_DEPTH,
    SERVICE_PRESS,
)
from .coordinator import FingerbotConfigEntry, FingerbotParameters

PRESS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): DeviceSelector({"integration": DOMAIN}),
        vol.Required(PARAM_PUSH_DEPTH): vol.All(vol.Coerce(int), vol.Range(0, 100)),
        vol.Required(PARAM_LAST_TIME): vol.All(vol.Coerce(int), vol.Range(0, 60)),
        vol.Required(PARAM_CONTINUE_NUM): vol.All(vol.Coerce(int), vol.Range(1, 20)),
        vol.Required(PARAM_CONTINUE_TIME): vol.All(vol.Coerce(int), vol.Range(0, 60)),
    }
)


def _entry_for_device(call: ServiceCall) -> FingerbotConfigEntry:
    """Resolve a Home Assistant device to its loaded Fingerbot entry."""
    registry = dr.async_get(call.hass)
    device_id = call.data[ATTR_DEVICE_ID]
    device = registry.async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device_id",
            translation_placeholders={"device_id": device_id},
        )
    identifier = next(
        (
            identifier
            for domain, identifier in device.identifiers
            if domain == DOMAIN
        ),
        None,
    )
    if identifier is not None:  # endpoint就是identifier
        # 通过集成标识查找，避免依赖 Home Assistant 2026.8 变更的设备归属字段。
        entry = call.hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, identifier
        )
        if entry is not None and entry.state is ConfigEntryState.LOADED:
            return cast(FingerbotConfigEntry, entry)
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="config_entry_not_found",
        translation_placeholders={"device_id": device_id},
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the unrestricted Fingerbot control service."""
    if hass.services.has_service(DOMAIN, SERVICE_PRESS):
        return

    async def _handle_press(call: ServiceCall) -> None:
        entry = _entry_for_device(call)
        await entry.runtime_data.async_press(
            FingerbotParameters(
                push_depth=call.data[PARAM_PUSH_DEPTH],
                last_time=call.data[PARAM_LAST_TIME],
                continue_num=call.data[PARAM_CONTINUE_NUM],
                continue_time=call.data[PARAM_CONTINUE_TIME],
            )
        )

    # 该服务不要求管理员权限，便于自动化和普通用户直接调用。
    hass.services.async_register(
        DOMAIN,
        SERVICE_PRESS,
        _handle_press,
        schema=PRESS_SCHEMA,
    )

"""Services for one-shot USTONE GATT configuration writes."""

from typing import cast

import voluptuous as vol
from bleak import BleakError

from homeassistant.components.bluetooth import (
    BluetoothReachabilityIntent,
    async_address_reachability_diagnostics,
    async_ble_device_from_address,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, format_mac
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ATTR_CONFIG,
    ATTR_DEVICE_ID,
    ATTR_TIMEOUT,
    DEFAULT_COMMAND_TIMEOUT,
    DOMAIN,
    SERVICE_SET_CONFIG,
)
from .coordinator import UstoneConfigEntry
from .ustone_ble import UstoneClientError, UstoneCharacteristicNotFoundError

_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional("adv_interval"): vol.All(
            vol.Coerce(int), vol.Range(min=20, max=10240), str
        ),
        vol.Optional("adv_timeout"): vol.All(
            vol.Coerce(int), vol.Range(min=1000, max=160000), str
        ),
        vol.Optional("work_mode"): cv.boolean,
        vol.Optional("respond_delay"): vol.All(
            vol.Coerce(int), vol.Range(min=20, max=400), str
        ),
        vol.Optional("det_range"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=16), str
        ),
        vol.Optional("micro_threshold"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=31), str
        ),
        vol.Optional("det_capability"): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=6), str
        ),
        vol.Optional("micro_filter"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=4), str
        ),
        vol.Optional("hold_time"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=600), str
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


def _validate_config_intervals(config: dict[str, object]) -> dict[str, object]:
    """Validate the interval relation when both values are supplied."""
    if (
        "adv_interval" in config
        and "adv_timeout" in config
        and int(cast(str, config["adv_interval"]))
        >= int(cast(str, config["adv_timeout"]))
    ):
        raise vol.Invalid("adv_interval must be less than adv_timeout")
    return config


_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_CONFIG): vol.All(
            dict, _CONFIG_SCHEMA, _validate_config_intervals
        ),
        vol.Optional(ATTR_TIMEOUT, default=DEFAULT_COMMAND_TIMEOUT): vol.All(
            vol.Coerce(float), vol.Range(min=5, max=60)
        ),
    }
)


def _entry_and_address(call: ServiceCall) -> tuple[UstoneConfigEntry, str]:
    """Resolve a Home Assistant device to its loaded USTONE entry."""
    registry = dr.async_get(call.hass)
    device = registry.async_get(call.data[ATTR_DEVICE_ID])
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device_id",
        )
    address = next(
        (value for kind, value in device.connections if kind == CONNECTION_BLUETOOTH),
        None,
    )
    if address is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device_id",
        )
    address = format_mac(address)
    entry = call.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, address)
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={"address": address},
        )
    return cast(UstoneConfigEntry, entry), address


async def _handle_set_config(call: ServiceCall) -> ServiceResponse:
    """Connect, write the JSON config, return the device response, disconnect."""
    entry, address = _entry_and_address(call)
    device = async_ble_device_from_address(call.hass, address, connectable=True)
    if device is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "address": address,
                "reason": async_address_reachability_diagnostics(
                    call.hass,
                    address,
                    BluetoothReachabilityIntent.CONNECTION,
                ),
            },
        )
    try:
        response = await entry.runtime_data.client.async_write_config(
            device,
            call.data[ATTR_CONFIG],
            call.data[ATTR_TIMEOUT],
        )
    except UstoneCharacteristicNotFoundError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="characteristic_not_found",
        ) from err
    except (UstoneClientError, BleakError, TimeoutError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="communication_error",
            translation_placeholders={"error": str(err)},
        ) from err
    return {
        "response": response.decode(errors="replace"),
        "response_hex": response.hex(),
    }


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the admin-only configuration service once."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_CONFIG):
        return
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_SET_CONFIG,
        _handle_set_config,
        schema=_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

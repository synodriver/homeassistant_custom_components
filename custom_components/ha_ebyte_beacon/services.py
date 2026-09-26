"""Services for the Ebyte Beacon integration."""

from __future__ import annotations

from typing import cast

import voluptuous as vol
from bleak import BleakError

from homeassistant.components.bluetooth import (
    BluetoothReachabilityIntent,
    async_address_reachability_diagnostics,
    async_ble_device_from_address,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
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

from .const import DOMAIN
from .coordinator import EbyteBeaconConfigEntry
from .ebyte_beacon import (
    EbyteBeaconAtCharacteristicNotFound,
    EbyteBeaconPasswordCharacteristicNotFound,
    EbyteBeaconPasswordError,
)

ATTR_COMMAND = "command"
ATTR_PASSWORD = "password"
ATTR_TIMEOUT = "timeout"
SERVICE_SEND_AT_COMMAND = "send_at_command"

SEND_AT_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_COMMAND): cv.string,
        vol.Optional(ATTR_PASSWORD): vol.Any(None, cv.string),
        vol.Optional(ATTR_TIMEOUT, default=5.0): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=60.0)
        ),
    }
)


def _get_entry_and_address_for_device(
    call: ServiceCall,
) -> tuple[EbyteBeaconConfigEntry, str]:
    """Return the config entry and Bluetooth address for the targeted device."""
    device_id: str = call.data[ATTR_DEVICE_ID]
    device_registry = dr.async_get(call.hass)

    if (device := device_registry.async_get(device_id)) is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device_id",
            translation_placeholders={"device_id": device_id},
        )

    address = next(
        (conn[1] for conn in device.connections if conn[0] == CONNECTION_BLUETOOTH),
        None,
    )
    if address is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_device_id",
            translation_placeholders={"device_id": device_id},
        )  # raw address

    # TODO: Use this when Home Assistant 2026.8 is the minimum supported version.
    # entry = call.hass.config_entries.async_get_entry(device.config_entry_id)
    entry = call.hass.config_entries.async_entry_for_domain_unique_id(
        DOMAIN, format_mac(address)
    )
    if entry is None or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={"address": address},
        )

    return cast(EbyteBeaconConfigEntry, entry), address


async def _async_send_at_command(
    hass: HomeAssistant,
    entry: EbyteBeaconConfigEntry,
    address: str,
    command: str,
    timeout: float,
    password: str | None,
) -> str:
    """Send an AT command to an Ebyte beacon and return its response."""
    ble_device = async_ble_device_from_address(hass, address, connectable=True)
    if ble_device is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "address": address,
                "reason": async_address_reachability_diagnostics(
                    hass,
                    address.upper(),
                    BluetoothReachabilityIntent.CONNECTION,
                ),
            },
        )

    try:
        return await entry.runtime_data.client.send_at_command(
            ble_device, command, timeout, password
        )
    except EbyteBeaconPasswordCharacteristicNotFound as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="password_characteristic_not_found",
        ) from err
    except EbyteBeaconPasswordError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="invalid_password",
        ) from err
    except EbyteBeaconAtCharacteristicNotFound as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="at_characteristic_not_found",
        ) from err
    except TimeoutError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="at_command_timeout",
        ) from err
    except BleakError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="at_command_failed",
            translation_placeholders={"error": str(err)},
        ) from err


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Ebyte Beacon services."""

    async def _handle_send_at_command(call: ServiceCall) -> ServiceResponse:
        entry, address = _get_entry_and_address_for_device(call)
        response = await _async_send_at_command(
            call.hass,
            entry,
            address,
            call.data[ATTR_COMMAND],
            call.data[ATTR_TIMEOUT],
            call.data.get(ATTR_PASSWORD),
        )
        return {"response": response}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_AT_COMMAND,
        _handle_send_at_command,
        schema=SEND_AT_COMMAND_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

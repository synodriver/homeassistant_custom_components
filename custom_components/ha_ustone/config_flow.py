"""Config flow for USTONE BLE devices."""

from typing import Any, override

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN
from .ustone_ble import UstoneProtocolError, parse_advertisement


def _normalise_address(value: str) -> str:
    """Validate and normalize a Bluetooth MAC address."""
    address = format_mac(value.strip())
    parts = address.split(":")
    if len(parts) != 6 or any(len(part) != 2 for part in parts):
        raise vol.Invalid("invalid Bluetooth address")
    try:
        bytes.fromhex("".join(parts))
    except ValueError as err:
        raise vol.Invalid("invalid Bluetooth address") from err
    return address


class UstoneConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle automatic discovery and manual MAC setup."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovery_title: str | None = None
        self._discovered_devices: dict[str, str] = {}

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Confirm an automatically discovered USTONE advertisement."""
        try:
            advertisement = parse_advertisement(discovery_info)
        except UstoneProtocolError:
            return self.async_abort(reason="not_supported")
        address = discovery_info.address
        self._discovery_info = discovery_info
        self._discovery_title = advertisement.model_name
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        return await self.async_step_bluetooth_confirm(
            title=advertisement.model_name,
        )

    async def async_step_bluetooth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
        *,
        title: str | None = None,
    ) -> ConfigFlowResult:
        """Confirm the discovered device."""
        if user_input is not None:
            assert self._discovery_info is not None
            return self.async_create_entry(
                title=(
                    title
                    or self._discovery_title
                    or self._discovery_info.name
                    or "USTONE BLE"
                ),
                data={CONF_ADDRESS: self._discovery_info.address},
            )
        self._set_confirm_only()
        assert self._discovery_info is not None
        placeholders = {
            "name": (
                title
                or self._discovery_title
                or self._discovery_info.name
                or "USTONE BLE"
            ),
        }
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=placeholders,
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow selecting a discovered device or entering a MAC manually."""
        if user_input is not None:
            address = _normalise_address(user_input[CONF_ADDRESS])
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            title = self._discovered_devices.get(address)
            if title is None:
                title = f"USTONE BLE {address.replace(':', '')[-6:]}"
            return self.async_create_entry(
                title=title,
                data={CONF_ADDRESS: address},
            )

        for discovery_info in async_discovered_service_info(self.hass, False):
            try:
                advertisement = parse_advertisement(discovery_info)
            except UstoneProtocolError:
                continue
            address = discovery_info.address
            self._discovered_devices[address] = (
                f"{advertisement.model_name} {address[-5:].replace(':', '')}"
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.All(
                        vol.Coerce(str), _normalise_address
                    )
                }
            ),
        )

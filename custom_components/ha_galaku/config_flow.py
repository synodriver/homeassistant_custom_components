"""Config flow for the GALAKU Bluetooth integration."""

from typing import Any, override

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN
from .galaku_ble import parse_advertisement


class GalakuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle automatic and manual GALAKU discovery."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    @staticmethod
    def _title(info: BluetoothServiceInfoBleak) -> str:
        """Build a stable, human-readable device title."""
        return f"{info.name or 'GALAKU GK36'} {format_mac(info.address)[-5:].replace(':', '')}"

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle automatic Bluetooth discovery."""
        if parse_advertisement(discovery_info) is None:
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        await self.async_set_unique_id(
            format_mac(discovery_info.address), raise_on_progress=False
        )
        self._abort_if_unique_id_configured()
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding an automatically discovered device."""
        assert self._discovery_info is not None
        info = self._discovery_info
        title = self._title(info)
        if user_input is not None:
            return self.async_create_entry(
                title=title,
                data={CONF_ADDRESS: format_mac(info.address)},
            )
        self._set_confirm_only()
        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm", description_placeholders=placeholders
        )

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose a device seen by the shared Bluetooth scanner."""
        if user_input is not None:
            address = format_mac(user_input[CONF_ADDRESS])
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address],
                data={CONF_ADDRESS: address},
            )

        await bluetooth.async_request_active_scan(self.hass)
        current_ids = self._async_current_ids(include_ignore=False)
        for info in async_discovered_service_info(self.hass, connectable=True):
            address = format_mac(info.address)
            if address in current_ids or address in self._discovered_devices:
                continue
            if parse_advertisement(info) is None:
                continue
            self._discovered_devices[address] = self._title(info)
        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )

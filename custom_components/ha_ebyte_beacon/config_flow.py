"""Config flow for the Ebyte Beacon integration.

Supports two discovery paths:

* ``async_step_bluetooth``: Home Assistant fires this when its Bluetooth
  scanner sees a device matching the manifest's ``bluetooth`` matcher (one of
  the two Ebyte pseudo manufacturer ids).  This is the automatic-discovery
  path the requirements call for.
* ``async_step_user``: manual pick from devices that have already been seen.
"""

from __future__ import annotations

import logging
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
from .ebyte_beacon import parse_advertisement

_LOGGER = logging.getLogger(__name__)


class EbyteBeaconConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ebyte beacons."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, str] = {}

    @staticmethod
    def _device_name(service_info: BluetoothServiceInfoBleak) -> str:
        """Return a friendly name for a discovered beacon."""
        formatted_mac = format_mac(service_info.address)
        short_address = formatted_mac[-5:].replace(":", "")
        name = service_info.name or ""
        # When the advertised name is just the raw address, fall back to a
        # generic label so the user sees something meaningful.
        if not name or name.replace("-", ":") in (
            service_info.address,
            service_info.address.replace("-", ":"),
        ):
            name = "Ebyte Beacon"
        return f"{name} {short_address}"

    @override
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle automatic discovery via the Bluetooth scanner."""
        # Only proceed if the advertisement actually contains an Ebyte frame.
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
        """Confirm adding a discovered beacon."""
        assert self._discovery_info is not None
        discovery_info = self._discovery_info
        title = self._device_name(discovery_info)
        if user_input is not None:
            return self.async_create_entry(
                title=title,
                data={CONF_ADDRESS: discovery_info.address},
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
        """Manual setup: pick a discovered Ebyte beacon from a list."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(format_mac(address), raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address],
                data={CONF_ADDRESS: address},
            )

        await bluetooth.async_request_active_scan(self.hass)
        current_ids = self._async_current_ids(include_ignore=False)
        discovered_ids = {format_mac(address) for address in self._discovered_devices}
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            formatted_address = format_mac(address)
            if formatted_address in current_ids or formatted_address in discovered_ids:
                continue
            if parse_advertisement(discovery_info) is None:
                continue
            self._discovered_devices[address] = self._device_name(discovery_info)
            discovered_ids.add(formatted_address)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices)}
            ),
        )

"""DataUpdateCoordinator for the Ebyte Beacon integration.

Each config entry is keyed on a single BLE address.  The coordinator owns an
:class:`ebyte_beacon.EbyteBeaconClient` bound to Home Assistant's shared
``BleakScanner`` (via :func:`homeassistant.components.bluetooth.async_get_scanner`)
and routes advertisements through it.  Because the beacon is a passive
broadcaster, the coordinator is *push-driven*: the detection callback (or the
``async_register_callback`` path) calls :meth:`async_set_updated_data` the
moment a new advertisement arrives. Home Assistant's Bluetooth manager tracks
address availability and notifies us when the beacon falls silent.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, override

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import OFFLINE_TIMEOUT
from .ebyte_beacon import EbyteBeaconAdvertisement, EbyteBeaconClient

if TYPE_CHECKING:
    from bleak import BleakScanner

_LOGGER = logging.getLogger(__name__)

EbyteBeaconConfigEntry = ConfigEntry["EbyteBeaconCoordinator"]


class EbyteBeaconCoordinator(DataUpdateCoordinator[EbyteBeaconAdvertisement | None]):
    """Coordinate a single Ebyte beacon."""

    config_entry: EbyteBeaconConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: EbyteBeaconConfigEntry,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            config_entry=entry,
            always_update=False,
        )
        self._address: str = entry.data[CONF_ADDRESS]
        self._scanner: BleakScanner = bluetooth.async_get_scanner(hass)

        # The client is the reusable library object; Home Assistant owns the
        # scanner and delivers advertisements through async_register_callback.
        self._client = EbyteBeaconClient(
            self._scanner,
            callback=self._on_advertisement,
            loop=hass.loop,
        )
        self._unsub_callbacks: list[Callable[[], None]] = []

    @property
    def address(self) -> str:
        """Return the tracked BLE address."""
        return self._address

    @property
    def client(self) -> EbyteBeaconClient:
        """Return the underlying library client (exposed for diagnostics)."""
        return self._client

    @callback
    def _on_advertisement(self, advertisement: EbyteBeaconAdvertisement) -> None:
        """Handle a freshly parsed advertisement from the client."""
        if advertisement.address.upper().replace(
            "-", ":"
        ) != self._address.upper().replace("-", ":"):
            return
        # ``async_set_updated_data`` dispatches listeners (the entities) and
        # marks the coordinator available.
        self.async_set_updated_data(advertisement)

    @callback
    def _async_handle_unavailable(
        self,
        service_info: BluetoothServiceInfoBleak,  # noqa: ARG002
    ) -> None:
        """Handle Home Assistant marking the beacon address unavailable."""
        self.last_update_success = False
        self.async_update_listeners()

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Receive advertisements via Home Assistant's bluetooth callback.

        This is the primary push path: HA's scanner dedupes and dispatches
        matching advertisements here, we feed them through the library client
        so parsing/caching is identical to the raw-scanner path.
        """
        self._client.inject_service_info(service_info)

    @override
    async def _async_update_data(self) -> EbyteBeaconAdvertisement | None:
        """Return the latest cached advertisement for initial setup refresh."""
        return self._client.get_device(self._address)

    async def async_start(self) -> None:
        """Start listening for advertisements.

        The caller (the integration setup) is responsible for wiring
        :meth:`async_stop` onto ``entry.async_on_unload`` so everything is torn
        down when the entry is unloaded.
        """
        bluetooth.async_set_fallback_availability_interval(
            self.hass, self._address, OFFLINE_TIMEOUT.total_seconds()
        )
        self._unsub_callbacks.append(
            bluetooth.async_register_callback(
                self.hass,
                self._async_handle_bluetooth_event,
                BluetoothCallbackMatcher(
                    address=self._address,
                    connectable=False,
                ),
                BluetoothScanningMode.ACTIVE,
            )
        )
        self._unsub_callbacks.append(
            bluetooth.async_track_unavailable(
                self.hass,
                self._async_handle_unavailable,
                self._address,
                connectable=False,
            )
        )

    @callback
    def async_stop(self) -> None:
        """Stop listening for advertisements.

        Safe to call from a synchronous ``async_on_unload`` callback: the
        detection-callback unregistration is scheduled on the event loop.
        """
        for unsub in self._unsub_callbacks:
            unsub()
        self._unsub_callbacks.clear()
        self._client.unregister()

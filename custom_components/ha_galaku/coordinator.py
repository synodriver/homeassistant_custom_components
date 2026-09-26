"""Coordinate GALAKU Bluetooth advertisements and commands."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import logging
import time
from typing import override

from bleak.backends.device import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.match import BluetoothCallbackMatcher
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import COMMAND_TIMEOUT, DOMAIN, OFFLINE_TIMEOUT
from .galaku_ble import (
    GalakuAdvertisement,
    GalakuClient,
    GalakuError,
    GalakuState,
    parse_advertisement,
)

type GalakuConfigEntry = ConfigEntry[GalakuCoordinator]

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GalakuData:
    """Combined advertisement and locally commanded state."""

    advertisement: GalakuAdvertisement | None
    state: GalakuState


class GalakuCoordinator(DataUpdateCoordinator[GalakuData]):
    """Track one GK36 and provide serialised BLE writes for all entities."""

    config_entry: GalakuConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GalakuConfigEntry,
        service_info: BluetoothServiceInfoBleak | None = None,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            config_entry=entry,
            update_interval=None,
            always_update=False,
        )
        self._address = str(entry.data[CONF_ADDRESS]).upper()
        self._client = GalakuClient()
        self._last_device: BLEDevice | None = None
        self._last_seen_monotonic: float | None = None
        self._unsub_callbacks: list[Callable[[], None]] = []
        self._last_active_vibration_level = 50
        self._last_active_electric_level = 50
        self.data = GalakuData(None, GalakuState())
        self.last_update_success = False

        if service_info is not None:
            self._set_advertisement(service_info, notify=False)

    @property
    def address(self) -> str:
        """Return the configured Bluetooth address."""
        return self._address

    @property
    def available(self) -> bool:
        """Return whether a recent Bluetooth update was received."""
        return self.last_update_success

    @property
    def advertisement(self) -> GalakuAdvertisement | None:
        """Return the latest advertisement metadata."""
        return self.data.advertisement

    @property
    def state(self) -> GalakuState:
        """Return the latest locally commanded state."""
        return self.data.state

    @property
    def vibration_level(self) -> int:
        """Return the current vibration level."""
        return self.state.vibration_level

    @property
    def electric_level(self) -> int:
        """Return the current electric stimulation level."""
        return self.state.electric_level

    @property
    def last_active_vibration_level(self) -> int:
        """Return the vibration level restored when enabled."""
        return self._last_active_vibration_level

    @property
    def last_active_electric_level(self) -> int:
        """Return the electric level restored when enabled."""
        return self._last_active_electric_level

    @property
    def rssi(self) -> int | None:
        """Return the latest received signal strength."""
        return self.advertisement.rssi if self.advertisement else None

    @property
    def advertisement_available(self) -> bool:
        """Return whether a recent advertisement was received."""
        if self._last_seen_monotonic is None:
            return False
        return (
            time.monotonic() - self._last_seen_monotonic
            <= OFFLINE_TIMEOUT.total_seconds()
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata shared by all entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._address)},
            connections={(CONNECTION_BLUETOOTH, self._address)},
            name=self.config_entry.title,
            manufacturer="GALAKU",
            model="GK36",
        )

    @callback
    def _set_advertisement(
        self, service_info: BluetoothServiceInfoBleak, *, notify: bool
    ) -> None:
        """Store an advertisement and the freshest BLEDevice object."""
        advertisement = parse_advertisement(service_info)
        if advertisement is None:
            # The configured address is already user-selected; retain presence
            # when a platform omits the local name from a later advertisement.
            advertisement = GalakuAdvertisement(
                address=service_info.address,
                name=service_info.name,
                rssi=service_info.rssi,
                connectable=service_info.connectable,
                service_uuids=tuple(service_info.service_uuids),
                manufacturer_data=dict(service_info.manufacturer_data),
                service_data=dict(service_info.service_data),
                time=service_info.time,
            )
        self._last_device = service_info.device
        self._last_seen_monotonic = time.monotonic()
        self.data = replace(self.data, advertisement=advertisement)
        self.last_update_success = True
        if notify:
            self.async_set_updated_data(self.data)

    @callback
    def _async_handle_bluetooth_event(
        self, service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        """Handle a fresh advertisement from Home Assistant's scanner."""
        del change
        self._set_advertisement(service_info, notify=True)

    @callback
    def _async_handle_unavailable(
        self, service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Mark controls unavailable while retaining tracker state."""
        del service_info
        self._last_seen_monotonic = time.monotonic() - OFFLINE_TIMEOUT.total_seconds()
        self.last_update_success = False
        self.async_update_listeners()

    @callback
    def async_start(self) -> None:
        """Start listening for advertisements."""
        bluetooth.async_set_fallback_availability_interval(
            self.hass, self._address, OFFLINE_TIMEOUT.total_seconds()
        )
        self._unsub_callbacks.extend(
            (
                bluetooth.async_register_callback(
                    self.hass,
                    self._async_handle_bluetooth_event,
                    BluetoothCallbackMatcher(address=self._address, connectable=True),
                    BluetoothScanningMode.ACTIVE,
                ),
                bluetooth.async_track_unavailable(
                    self.hass,
                    self._async_handle_unavailable,
                    self._address,
                    True,
                ),
            )
        )

    @callback
    def async_stop(self) -> None:
        """Stop Bluetooth callbacks when the config entry unloads."""
        for unsubscribe in self._unsub_callbacks:
            unsubscribe()
        self._unsub_callbacks.clear()

    async def _async_get_device(self) -> BLEDevice:
        """Return the freshest connectable device or raise a client error."""
        device = self._last_device or bluetooth.async_ble_device_from_address(
            self.hass, self._address
        )
        if device is None:
            raise GalakuError("GALAKU device is not currently visible")
        return device

    async def async_set_level(self, level: int | float) -> int:
        """Set both output channels for backwards-compatible callers."""
        value = await self._async_set_channel_level(level, channel="both")
        return value

    async def _async_set_channel_level(
        self, level: int | float, *, channel: str
    ) -> int:
        """Write one or both output channels and update the local snapshot."""
        device = await self._async_get_device()
        try:
            if channel == "vibration":
                value = await self._client.async_set_vibration_level(
                    device, level, COMMAND_TIMEOUT
                )
            elif channel == "electric":
                value = await self._client.async_set_electric_level(
                    device, level, COMMAND_TIMEOUT
                )
            else:
                value = await self._client.async_set_level(
                    device, level, COMMAND_TIMEOUT
                )
        except Exception:
            self.last_update_success = False
            self.async_update_listeners()
            raise
        vibration_level = self.vibration_level
        electric_level = self.electric_level
        if channel in ("vibration", "both"):
            vibration_level = value
            if value > 0:
                self._last_active_vibration_level = value
        if channel in ("electric", "both"):
            electric_level = value
            if value > 0:
                self._last_active_electric_level = value
        self.data = replace(
            self.data,
            state=GalakuState(vibration_level, electric_level, datetime.now(UTC)),
        )
        self.async_set_updated_data(self.data)
        return value

    async def async_set_vibration_level(self, level: int | float) -> int:
        """Set vibration without changing electric stimulation."""
        return await self._async_set_channel_level(level, channel="vibration")

    async def async_set_electric_level(self, level: int | float) -> int:
        """Set electric stimulation without changing vibration."""
        return await self._async_set_channel_level(level, channel="electric")

    async def async_stop_output(self) -> None:
        """Stop both output channels and update the local state."""
        await self.async_set_level(0)

    @override
    async def _async_update_data(self) -> GalakuData:
        """Return cached data; GK36 exposes no readable state characteristic."""
        return self.data

"""Bluetooth advertisement coordinator for USTONE devices."""

from collections.abc import Callable
import logging
from typing import Any, override

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .ustone_ble import (
    UstoneAdvertisement,
    UstoneClient,
    UstoneProtocolError,
    parse_advertisement,
)
from .ustone_ble.protocol import MANUFACTURER_ID

_LOGGER = logging.getLogger(__name__)


class UstoneCoordinator(PassiveBluetoothProcessorCoordinator[UstoneAdvertisement]):
    """Dispatch parsed USTONE advertisements and track online state."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        """Initialize the coordinator."""
        self.latest: UstoneAdvertisement | None = None
        self.client = UstoneClient()
        self._state_listeners: list[Callable[[], None]] = []
        super().__init__(
            hass,
            _LOGGER,
            address=address,
            mode=BluetoothScanningMode.PASSIVE,
            connectable=False,
            update_method=self._parse_update,
        )

    @callback
    def _parse_update(
        self, service_info: BluetoothServiceInfoBleak
    ) -> UstoneAdvertisement:
        """Parse an incoming BLE advertisement."""
        advertisement = parse_advertisement(service_info)
        self.latest = advertisement
        return advertisement

    @callback
    @override
    def _async_handle_bluetooth_event(
        self, service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        """Dispatch the update before refreshing tracker state."""
        if MANUFACTURER_ID not in service_info.manufacturer_data:
            return
        try:
            parse_advertisement(service_info)
        except UstoneProtocolError:
            return
        super()._async_handle_bluetooth_event(service_info, change)
        self._notify_state_listeners()

    @callback
    @override
    def _async_handle_unavailable(
        self, service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Mark the device offline while retaining the last parsed values."""
        super()._async_handle_unavailable(service_info)
        self._notify_state_listeners()

    @callback
    def async_add_listener(
        self, listener: Callable[[], None], context: Any = None
    ) -> Callable[[], None]:
        """Register a listener for online-state changes."""
        self._state_listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._state_listeners:
                self._state_listeners.remove(listener)

        return _remove

    @callback
    def _notify_state_listeners(self) -> None:
        """Notify non-passive entities such as the device tracker."""
        for listener in self._state_listeners:
            listener()


type UstoneConfigEntry = ConfigEntry[UstoneCoordinator]

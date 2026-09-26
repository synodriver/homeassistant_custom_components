"""Client/cache for Ebyte beacon advertisements from a shared ``BleakScanner``.

The :class:`EbyteBeaconClient` is the high-level entry point of this library.
Following the same pattern as ``aioacaia`` (https://github.com/zweckj/aioacaia),
its constructor accepts a ``bleak.BleakScanner`` instance.  In Home Assistant
this is the shared Bluetooth scanner obtained from
``homeassistant.components.bluetooth.async_get_scanner``; it is *already*
scanning and managed by Home Assistant, so this client must **not** start/stop
it or register its own scanner callback.

Two styles of use are supported:

* push: feed advertisements into :meth:`inject_service_info` (Home Assistant) or
  :meth:`inject_bleak` (plain bleak); an optional callback is invoked for every
  parsed Ebyte advertisement.
* pull: call :meth:`find_device_by_address` or
  :meth:`find_device_by_manufacturer_data` to locate a device from the scanner's
  current ``discovered_devices_and_advertisement_data`` snapshot or from
  advertisements already injected into the client.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .models import EbyteBeaconAdvertisement
from .parser import (
    EBYTE_NO_SENSOR_MANUFACTURER_ID,
    EBYTE_SENSOR_MANUFACTURER_ID,
    parse_advertisement,
    parse_bleak,
)

if TYPE_CHECKING:
    from bleak import AdvertisementData, BleakClient, BleakScanner, BLEDevice
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)

#: Callable invoked for every fresh Ebyte advertisement.
EbyteBeaconCallback = Callable[[EbyteBeaconAdvertisement], None]

AT_CHARACTERISTIC_UUID = "000066AA-0000-1000-8000-00805F9B34FB"
PASSWORD_CHARACTERISTIC_UUID = "000077AA-0000-1000-8000-00805F9B34FB"


class EbyteBeaconError(Exception):
    """Base error for Ebyte beacon client failures."""


class EbyteBeaconAtCharacteristicNotFound(EbyteBeaconError):
    """Raised when the AT command characteristic is not available."""


class EbyteBeaconPasswordCharacteristicNotFound(EbyteBeaconError):
    """Raised when the password characteristic is not available."""


class EbyteBeaconPasswordError(EbyteBeaconError):
    """Raised when the beacon rejects the AT command password."""


class EbyteBeaconClient:
    """Consume a shared ``bleak.BleakScanner`` for Ebyte beacons.

    The client keeps a per-address cache of the most recently parsed
    advertisement, which is what :meth:`find_device_by_address` queries.  It
    also tracks the monotonic time each address was last seen so the Home
    Assistant integration can declare a beacon offline once it stops
    advertising.
    """

    def __init__(
        self,
        scanner: BleakScanner,
        *,
        callback: EbyteBeaconCallback | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Initialise the client.

        :param scanner: a running ``bleak.BleakScanner`` (in Home Assistant,
            ``async_get_scanner(hass)``).  The client never starts or stops it.
        :param callback: optional callback invoked (from the scanner thread /
            event loop) for every fresh Ebyte advertisement.  May be ``None``
            if the caller only wants to poll via the ``find_device_by_*``
            helpers.
        :param loop: the event loop to use for ``call_soon``-scheduling the
            caller's callback.  Defaults to the running loop when available;
            captured again on :meth:`async_register` if still ``None``.
        """
        self._scanner = scanner
        self._callback = callback
        # ``loop`` may be None if the client is constructed outside a running
        # loop; it is resolved the first time an advertisement is injected.
        # ``loop.time()`` is safe to call from any thread (it is just the
        # monotonic clock), which matters because raw scanner callbacks may run
        # off-loop in non-Home Assistant callers.
        self._loop = loop
        # address -> most recent parsed advertisement
        self._devices: dict[str, EbyteBeaconAdvertisement] = {}
        # address -> monotonic seconds of last reception
        self._last_seen: dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # detection-callback plumbing
    # ------------------------------------------------------------------ #
    def inject_bleak(
        self, device: BLEDevice, advertisement: AdvertisementData
    ) -> EbyteBeaconAdvertisement | None:
        """Feed a raw ``bleak`` advertisement into the client.

        This lets non-Home Assistant callers wire the client to their own
        scanner callback or ``advertisement_data()`` consumer without this
        library owning the scanner lifecycle.
        """
        try:
            parsed = parse_bleak(device, advertisement)
        except Exception:  # pragma: no cover - defensive, never crash scanner
            _LOGGER.exception("Failed to parse Ebyte advertisement from %s", device)
            return None
        if parsed is None:
            return None
        self._handle_advertisement(parsed)
        return parsed

    def _handle_advertisement(self, advertisement: EbyteBeaconAdvertisement) -> None:
        """Record the advertisement and invoke the user callback."""
        address = advertisement.address
        self._devices[address] = advertisement
        # Record the monotonic time of reception for diagnostics and library
        # callers that inspect cached device metadata.
        # ``loop.time()`` is safe from any thread; fall back to the wall-clock
        # monotonic if no loop is known yet (e.g. a detection arriving before
        # :meth:`async_register` ran, which should not happen in practice but
        # is guarded against anyway).
        loop = self._loop
        if loop is not None:
            self._last_seen[address] = loop.time()
        else:  # pragma: no cover - defensive, async_register sets the loop
            import time

            self._last_seen[address] = time.monotonic()
        if self._callback is None:
            return
        if loop is None:
            # No loop yet: invoke synchronously.  ``async_register`` runs the
            # the first time the client is used and always sets ``_loop``, so
            # this branch only covers defensive edge cases.
            try:
                self._callback(advertisement)
            except Exception:  # pragma: no cover - defensive
                _LOGGER.exception("Ebyte beacon callback raised")
            return
        # Schedule on the chosen loop so the caller does not need to be
        # thread-safe (scanner callbacks may run off-loop).
        loop.call_soon_threadsafe(self._invoke_callback, advertisement)

    def _invoke_callback(self, advertisement: EbyteBeaconAdvertisement) -> None:
        try:
            self._callback(advertisement)  # type: ignore[misc]
        except Exception:  # pragma: no cover - defensive
            _LOGGER.exception("Ebyte beacon callback raised")

    async def async_register(self) -> None:
        """Compatibility no-op for older callers.

        The client intentionally does not start scanning, stop scanning, or
        register a detection callback on the supplied scanner.  Callers should
        feed advertisements through :meth:`inject_service_info` or
        :meth:`inject_bleak` from the scanner mechanism they own.
        """
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

    def unregister(self) -> None:
        """Drop the advertisement callback."""
        self._callback = None

    async def async_unregister(self) -> None:
        """Compatibility no-op for older callers."""
        self.unregister()

    # ------------------------------------------------------------------ #
    # snapshot / pull helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _scanner_advertisement_record(
        scanner: BleakScanner, address: str
    ) -> tuple[BLEDevice, AdvertisementData] | None:
        """Return the scanner's latest raw advertisement tuple for ``address``.

        Home Assistant returns a ``HaBleakScannerWrapper`` cast to
        ``BleakScanner`` for library compatibility.  That wrapper, and plain
        bleak scanners, expose the ``discovered_devices_and_advertisement_data``
        snapshot property.  This client only uses that snapshot property and does
        not rely on wrapper-private history or lower-level scanner helpers.
        """
        records = getattr(scanner, "discovered_devices_and_advertisement_data", None)
        if records is None:
            return None
        with contextlib.suppress(Exception):
            return records.get(address)
        return None

    @staticmethod
    def _scanner_advertisement_records(
        scanner: BleakScanner,
    ) -> dict[str, tuple[BLEDevice, AdvertisementData]]:
        """Return the scanner's current discovered-device advertisement snapshot."""
        records = getattr(scanner, "discovered_devices_and_advertisement_data", None)
        if records is None:
            return {}
        with contextlib.suppress(Exception):
            return dict(records)
        return {}

    def get_device(self, address: str) -> EbyteBeaconAdvertisement | None:
        """Return the most recent advertisement for ``address``, or ``None``."""
        return self._devices.get(address)

    def last_seen(self, address: str) -> float | None:
        """Return the monotonic timestamp ``address`` was last received."""
        return self._last_seen.get(address)

    def last_seen_all(self) -> dict[str, float]:
        """Return a snapshot of the monotonic last-seen timestamps per address."""
        return dict(self._last_seen)

    def get_seen_addresses(self) -> set[str]:
        """Return the set of Ebyte addresses the client knows about."""
        return set(self._devices)

    def is_address_for_ebyte_beacon(self, address: str) -> bool:
        """Return ``True`` if we have parsed an Ebyte frame from ``address``."""
        return address in self._devices

    def inject_service_info(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Feed a Home Assistant ``BluetoothServiceInfoBleak`` into the client.

        Home Assistant integrations usually receive advertisements via
        ``bluetooth.async_register_callback``; calling this from that callback
        routes them through the same parsing / caching / user-callback path
        as the raw scanner detection callback.
        """
        parsed = parse_advertisement(service_info)
        if parsed is None:
            return
        self._handle_advertisement(parsed)

    async def find_device_by_address(
        self, address: str, timeout: float = 10.0
    ) -> EbyteBeaconAdvertisement | None:
        """Locate the Ebyte beacon at ``address`` within ``timeout`` seconds.

        First checks the client cache and scanner's discovered-advertisement
        snapshot; if not present, polls until the timeout elapses.  Never starts
        the scanner.
        """
        if (parsed := self._devices.get(address)) is not None:
            return parsed
        record = self._scanner_advertisement_record(self._scanner, address)
        if record is not None:
            with contextlib.suppress(Exception):
                parsed = self._from_advertisement_record(record)
                if parsed is not None:
                    self._handle_advertisement(parsed)
                    return parsed
        loop = self._loop or asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if (parsed := self._devices.get(address)) is not None:
                return parsed
            record = self._scanner_advertisement_record(self._scanner, address)
            if record is not None:
                with contextlib.suppress(Exception):
                    parsed = self._from_advertisement_record(record)
                    if parsed is not None:
                        self._handle_advertisement(parsed)
                        return parsed
            await asyncio.sleep(0.5)
        return self._devices.get(address)

    async def find_device_by_manufacturer_data(
        self, timeout: float = 10.0
    ) -> EbyteBeaconAdvertisement | None:
        """Locate any Ebyte beacon within ``timeout`` seconds.

        Useful for config-flow discovery when no address is known yet.
        """
        if self._devices:
            return next(iter(self._devices.values()))
        for record in self._scanner_advertisement_records(self._scanner).values():
            with contextlib.suppress(Exception):
                parsed = self._from_advertisement_record(record)
                if parsed is not None:
                    self._handle_advertisement(parsed)
                    return parsed
        loop = self._loop or asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if self._devices:
                return next(iter(self._devices.values()))
            for record in self._scanner_advertisement_records(self._scanner).values():
                with contextlib.suppress(Exception):
                    parsed = self._from_advertisement_record(record)
                    if parsed is not None:
                        self._handle_advertisement(parsed)
                        return parsed
            await asyncio.sleep(0.5)
        return next(iter(self._devices.values()), None)

    @staticmethod
    async def _write_command_and_wait_for_response(
        client: BleakClient,
        characteristic: BleakGATTCharacteristic,
        command: str,
        timeout: float,
        end_markers: tuple[bytes, ...],
    ) -> str:
        """Write a command and collect notify chunks until an end marker arrives."""
        queue: asyncio.Queue[bytes] = asyncio.Queue()

        def _on_notify(
            sender: BleakGATTCharacteristic,
            data: bytearray,  # noqa: ARG001
        ) -> None:
            queue.put_nowait(bytes(data))

        await client.start_notify(characteristic, _on_notify)
        try:
            await client.write_gatt_char(
                characteristic, command.encode("ascii"), response=True
            )
            response = bytearray()
            while True:
                response.extend(await asyncio.wait_for(queue.get(), timeout=timeout))
                if any(marker in response for marker in end_markers):
                    return response.decode(errors="replace")
        finally:
            await client.stop_notify(characteristic)

    async def send_at_command(
        self,
        device: BLEDevice,
        command: str,
        timeout: float = 5.0,
        password: str | None = None,
    ) -> str:
        """Send an AT command to an Ebyte beacon and return its response."""
        client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            name=device.name or device.address,
            timeout=timeout,
        )
        try:
            if password is not None:
                password_characteristic = client.services.get_characteristic(
                    PASSWORD_CHARACTERISTIC_UUID
                )
                if password_characteristic is None:
                    raise EbyteBeaconPasswordCharacteristicNotFound

                password_response = await self._write_command_and_wait_for_response(
                    client,
                    password_characteristic,
                    password,
                    timeout,
                    (b"OK", b"ERR"),
                )
                if "ERR" in password_response:
                    raise EbyteBeaconPasswordError

            characteristic = client.services.get_characteristic(AT_CHARACTERISTIC_UUID)
            if characteristic is None:
                raise EbyteBeaconAtCharacteristicNotFound

            return await self._write_command_and_wait_for_response(
                client,
                characteristic,
                command,
                timeout,
                (b"+OK", b"+ERR"),
            )
        finally:
            await client.disconnect()

    @staticmethod
    def _from_advertisement_record(
        record: tuple[BLEDevice, AdvertisementData]
    ) -> EbyteBeaconAdvertisement | None:
        """Parse a scanner ``(BLEDevice, AdvertisementData)`` snapshot record."""
        device, advertisement = record
        return parse_bleak(device, advertisement)

    @property
    def manufacturer_ids(self) -> tuple[int, ...]:
        """The Ebyte manufacturer ids this client recognises."""
        return (
            EBYTE_SENSOR_MANUFACTURER_ID,
            EBYTE_NO_SENSOR_MANUFACTURER_ID,
        )

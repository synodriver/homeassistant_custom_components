"""Reusable BLE client for GALAKU/GK36 devices."""

import asyncio
from collections.abc import Callable
import logging

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import WRITE_CHARACTERISTIC_UUID
from .exceptions import GalakuCharacteristicNotFoundError
from .protocol import build_electric_packet, build_vibrate_packet, clamp_level

_LOGGER = logging.getLogger(__name__)
_COMMAND_GAP_SECONDS = 0.1


class GalakuClient:
    """Connect to a GK36 and send independent output commands."""

    def __init__(self) -> None:
        """Initialise the serialisable client."""
        self._command_lock = asyncio.Lock()

    async def _async_write_packet(
        self,
        device: BLEDevice,
        level: int | float,
        timeout: float = 15.0,
        packet_builder: Callable[[int | float], bytes] = build_vibrate_packet,
    ) -> int:
        """Write one output packet and return its clamped level."""
        value = clamp_level(level)
        async with self._command_lock:
            async with asyncio.timeout(timeout):
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    name=device.name or device.address,
                )
                try:
                    characteristic = client.services.get_characteristic(
                        WRITE_CHARACTERISTIC_UUID
                    )
                    if characteristic is None:
                        raise GalakuCharacteristicNotFoundError(
                            WRITE_CHARACTERISTIC_UUID
                        )
                    await client.write_gatt_char(
                        characteristic,
                        packet_builder(value),
                        response=True,
                    )
                finally:
                    if client.is_connected:
                        await client.disconnect()
        _LOGGER.debug("Set GALAKU %s output to level %s", device.address, value)
        return value

    async def async_set_vibration_level(
        self, device: BLEDevice, level: int | float, timeout: float = 15.0
    ) -> int:
        """Set vibration without changing electric stimulation."""
        return await self._async_write_packet(
            device, level, timeout, build_vibrate_packet
        )

    async def async_set_electric_level(
        self, device: BLEDevice, level: int | float, timeout: float = 15.0
    ) -> int:
        """Set electric stimulation without changing vibration."""
        return await self._async_write_packet(
            device, level, timeout, build_electric_packet
        )

    async def async_set_level(
        self, device: BLEDevice, level: int | float, timeout: float = 15.0
    ) -> int:
        """Set both output channels for backwards-compatible callers."""
        value = clamp_level(level)
        await self.async_set_electric_level(device, value, timeout)
        await asyncio.sleep(_COMMAND_GAP_SECONDS)
        await self.async_set_vibration_level(device, value, timeout)
        return value

    async def async_stop(self, device: BLEDevice, timeout: float = 15.0) -> None:
        """Stop both output channels."""
        await self.async_set_level(device, 0, timeout)

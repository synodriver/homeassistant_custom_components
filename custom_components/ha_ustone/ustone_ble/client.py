"""Short-lived GATT client for USTONE configuration writes."""

import asyncio
import json

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    UART_RX_CHARACTERISTIC_UUID,
    UART_TX_CHARACTERISTIC_UUID,
)

RESPONSE_QUIET_PERIOD = 0.5


class UstoneClientError(Exception):
    """Base exception for USTONE GATT operations."""


class UstoneCharacteristicNotFoundError(UstoneClientError):
    """The device does not expose the documented Nordic UART characteristics."""


class UstoneClient:
    """Connect, write one JSON command, collect a response, and disconnect."""

    async def async_write_config(
        self,
        device: BLEDevice,
        config: dict[str, object],
        timeout: float = 30.0,
    ) -> bytes:
        """Write a BSH1-style configuration object over Nordic UART."""
        client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            device.name or "USTONE BLE",
        )
        # 配置完成后立即断开，避免电池设备长期维持 GATT 连接。
        response = bytearray()
        response_received = asyncio.Event()
        tx = None

        def _notification_callback(_: object, data: bytearray) -> None:
            response.extend(data)
            response_received.set()

        try:
            services = client.services
            rx = services.get_characteristic(UART_RX_CHARACTERISTIC_UUID)
            tx = services.get_characteristic(UART_TX_CHARACTERISTIC_UUID)
            if rx is None or tx is None:
                raise UstoneCharacteristicNotFoundError(
                    "USTONE Nordic UART service or characteristic is missing"
                )

            await client.start_notify(tx, _notification_callback)
            payload = json.dumps(
                {"config": config}, ensure_ascii=False, separators=(",", ":")
            ).encode()
            write_with_response = "write" in (getattr(rx, "properties", ()) or ())
            await client.write_gatt_char(rx, payload, response=write_with_response)
            try:
                async with asyncio.timeout(timeout):
                    await response_received.wait()
                    # 文档未定义结束标志；连续通知之间的静默期作为应答边界。
                    while True:
                        response_received.clear()
                        try:
                            await asyncio.wait_for(
                                response_received.wait(), RESPONSE_QUIET_PERIOD
                            )
                        except TimeoutError:
                            break
            except TimeoutError as err:
                raise UstoneClientError(
                    "timed out waiting for USTONE response"
                ) from err
            return bytes(response)
        finally:
            try:
                if tx is not None:
                    await client.stop_notify(tx)
            except (AttributeError, BleakError, OSError):
                pass
            try:
                await client.disconnect()
            except BleakError:
                pass

"""Decode USTONE BLE manufacturer data."""

from collections.abc import Mapping, Sequence
from typing import Any

from .models import UstoneAdvertisement, UstoneModel

MANUFACTURER_ID = 0xFF07
PREFIX_LENGTH = 3

_VALUE_LENGTHS = {
    0x01: 4,  # illuminance, lux
    0x02: 2,  # button count and bit mask
    0x03: 1,  # occupancy
    0x04: 2,  # temperature, 0.1 C
    0x05: 2,  # humidity, 0.1 %RH
    0x06: 1,  # door/magnet
    0x08: 3,  # pressure, Pa
    0x0A: 1,  # water leak
    0x63: 1,  # battery percentage
}


class UstoneProtocolError(ValueError):
    """Raised when a payload is not a supported USTONE frame."""


def _payload_from_raw_advertisement(data: bytes) -> bytes:
    """Extract manufacturer data from BLE advertising data (AD structures)."""
    position = 0
    while position < len(data):
        length = data[position]
        if length == 0:
            break
        end = position + length + 1
        if end > len(data):
            break
        if data[position + 1] == 0xFF and length >= 3:
            manufacturer_id = int.from_bytes(
                data[position + 2 : position + 4], "little"
            )
            if manufacturer_id == MANUFACTURER_ID:
                return data[position + 4 : end]
        position = end
    raise UstoneProtocolError("no USTONE manufacturer data found")


def _model_from_keys(values: dict[int, bytes]) -> UstoneModel:
    """Infer the product family from its data keys."""
    if 0x01 in values or 0x04 in values or 0x05 in values or 0x08 in values:
        return UstoneModel.BSE1
    if 0x06 in values:
        return UstoneModel.BSM1
    if 0x0A in values:
        return UstoneModel.BSW1
    if 0x03 in values:
        return UstoneModel.BSH1
    if 0x02 in values:
        return UstoneModel.BBS1 if values[0x02][0] > 1 else UstoneModel.BBB1
    return UstoneModel.UNKNOWN


def decode_payload(payload: bytes) -> tuple[UstoneModel, dict[str, int | float | bool]]:
    """Decode manufacturer data, including its three-byte prefix."""
    if len(payload) <= PREFIX_LENGTH:
        raise UstoneProtocolError("USTONE manufacturer data is too short")

    raw_values: dict[int, bytes] = {}
    position = PREFIX_LENGTH
    while position < len(payload):
        key = payload[position]
        value_length = _VALUE_LENGTHS.get(key)
        # 未知 Key 没有可靠的长度；尾部还可能包含零填充和非协议字节。
        if value_length is None:
            break
        position += 1
        if position + value_length > len(payload):
            break
        raw_values[key] = payload[position : position + value_length]
        position += value_length

    model = _model_from_keys(raw_values)
    values: dict[str, int | float | bool] = {}
    if 0x02 in raw_values:
        button_count, button_mask = raw_values[0x02]
        values["button_count"] = button_count
        for index in range(min(button_count, 3)):
            values[f"button_{index + 1}"] = bool(button_mask & (1 << index))
    if 0x03 in raw_values:
        values["occupancy"] = bool(raw_values[0x03][0])
    if 0x06 in raw_values:
        values["door"] = bool(raw_values[0x06][0])
    if 0x0A in raw_values:
        values["water_leak"] = bool(raw_values[0x0A][0])
    if 0x01 in raw_values:
        values["illuminance"] = int.from_bytes(raw_values[0x01], "little")
    if 0x04 in raw_values:
        values["temperature"] = int.from_bytes(raw_values[0x04], "little") / 10
    if 0x05 in raw_values:
        values["humidity"] = int.from_bytes(raw_values[0x05], "little") / 10
    if 0x08 in raw_values:
        values["pressure"] = int.from_bytes(raw_values[0x08], "little")
    if 0x63 in raw_values:
        values["battery"] = raw_values[0x63][0]

    if model is UstoneModel.UNKNOWN and 0x63 not in raw_values:
        raise UstoneProtocolError("unsupported USTONE product data")
    return model, values


def _payload_from_source(source: Any) -> bytes:
    """Extract USTONE manufacturer data from raw bytes or service info."""
    if isinstance(source, (bytes, bytearray, memoryview)):
        data = bytes(source)
        if data[:2] == b"\x03\x08":
            return _payload_from_raw_advertisement(data)
        return data

    manufacturer_data = (
        source
        if isinstance(source, Mapping)
        else getattr(source, "manufacturer_data", {})
    )
    if isinstance(manufacturer_data, Mapping):
        payload = manufacturer_data.get(MANUFACTURER_ID)
        if isinstance(payload, (bytes, bytearray, memoryview)):
            return bytes(payload)
    raise UstoneProtocolError("no USTONE manufacturer data found")


def parse_advertisement(
    source: Any,
    *,
    address: str | None = None,
    name: str | None = None,
    rssi: int | None = None,
    connectable: bool | None = None,
    service_uuids: Sequence[str] | None = None,
) -> UstoneAdvertisement:
    """Parse manufacturer data or a Home Assistant Bluetooth service-info object."""
    payload = _payload_from_source(source)
    model, values = decode_payload(payload)
    return UstoneAdvertisement(
        address=address or str(getattr(source, "address", "")),
        name=name or str(getattr(source, "name", "USTONE BLE")),
        model=model,
        rssi=rssi if rssi is not None else int(getattr(source, "rssi", 0)),
        values=values,
        raw_data=payload,
        connectable=(
            connectable
            if connectable is not None
            else bool(getattr(source, "connectable", False))
        ),
        service_uuids=tuple(
            service_uuids
            if service_uuids is not None
            else getattr(source, "service_uuids", ())
        ),
    )

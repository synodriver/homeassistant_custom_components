"""Pure parsing helpers for the Ebyte EWD104-BT58 beacon manufacturer data frame.

The EWD104-BT58 family broadcasts, alongside a standard iBeacon / Eddystone
frame, a proprietary manufacturer-specific-data frame (AD type ``0xFF``) that
carries the device MAC, battery and (on sensor variants) temperature, humidity
and acceleration.  This module decodes that frame.  It has no Home Assistant or
``bleak`` dependency so it can be unit tested and reused independently.

Frame layout (section 5.3 of the EWD104-BT58 user manual):

No-sensor variant (manufacturer id ``0x0318``):

    +0  +1  company id (little-endian)        -> 0x0318
    +2  +7  MAC address (6 bytes, big-endian)
    +8  +9  Major (2 bytes, big-endian)
    +10 +11 Minor (2 bytes, big-endian)
    +12     tx-power index (1 byte)
    +13 +14 advertising interval in ms (2 bytes, big-endian)
    +15     battery percent (1 byte)

Sensor variant (manufacturer id ``0x4245``):

    +0  +1  company id (little-endian)        -> 0x4245
    +2      connectable flag: 0x13 connectable, 0x12 not connectable
    +3      encryption flag: 0 no, 1 yes
    +4  +9  acceleration, X/Y/Z each 2 bytes, big-endian, raw int16
    +10 +11 temperature: integer byte + decimal byte (see below)
    +12 +13 humidity:    integer byte + decimal byte
    +14     battery percent (1 byte)

Temperature encoding (per the manual): the first byte is the integer part, the
second byte the decimal part.  When the ambient temperature is below zero the
most-significant bit of the integer byte is set and the remaining bits use a
signed-byte/two's-complement representation.  For example ``0x16 0x24`` ->
+22.36 degC.  Humidity uses the same integer-plus-decimal layout but is
unsigned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import EbyteBeaconAdvertisement, EbyteBeaconSensorData

if TYPE_CHECKING:
    from bleak.backends.scanner import AdvertisementData, BLEDevice
    from home_assistant_bluetooth import BluetoothServiceInfoBleak

# Pseudo manufacturer ids used by the Ebyte frame.  These are NOT registered
# with the Bluetooth SIG (the Ebyte frame is a private, unregistered format), so
# they will not appear in the SIG company identifier list.  ``bleak`` exposes
# manufacturer ids as little-endian ints, which is the form used here.
EBYTE_NO_SENSOR_MANUFACTURER_ID = 0x0318
EBYTE_SENSOR_MANUFACTURER_ID = 0x4245

# Offset / size constants for the no-sensor frame (after the company id).
_NSE_MAC = 0
_NSE_MAJOR = 6
_NSE_MINOR = 8
_NSE_TX_POWER = 10
_NSE_INTERVAL = 11
_NSE_BATTERY = 13

# Offset / size constants for the sensor frame (after the company id).
_SE_FLAG_CONNECTABLE = 0
_SE_FLAG_ENCRYPTED = 1
_SE_ACCEL_X = 2
_SE_ACCEL_Y = 4
_SE_ACCEL_Z = 6
_SE_TEMP = 8
_SE_HUM = 10
_SE_BATTERY = 12

# Minimum payload length (excluding the 2-byte company id) for each variant.
_NSE_MIN_PAYLOAD = 14  # mac..battery
_SE_MIN_PAYLOAD = 13  # flags..battery

_CONNECTABLE_FLAG = 0x13


def _mac_bytes_to_str(data: bytes) -> str:
    """Format 6 big-endian MAC bytes as a colon-separated upper-case address."""
    return ":".join(f"{b:02X}" for b in data)


def _signed_int8(value: int) -> int:
    """Decode a two's-complement 8-bit integer."""
    return value - 0x100 if value & 0x80 else value


def _decode_temperature(temp_int: int, temp_frac: int) -> float:
    """Decode a temperature integer+decimal byte pair.

    The integer byte is a signed two's-complement value.  The decimal byte is
    hundredths and follows the sign of the integer byte.
    """
    integer = _signed_int8(temp_int)
    value = abs(integer) + temp_frac / 100.0
    return -value if integer < 0 else value


def _decode_humidity(hum_int: int, hum_frac: int) -> float:
    """Decode a humidity integer+decimal byte pair (unsigned, hundredths)."""
    return hum_int + hum_frac / 100.0


def _signed_int16_be(high: int, low: int) -> int:
    """Decode a big-endian two's-complement 16-bit integer."""
    value = (high << 8) | low
    return value - 0x10000 if value & 0x8000 else value


def parse_no_sensor_frame(payload: bytes) -> EbyteBeaconAdvertisement | None:
    """Parse a no-sensor Ebyte manufacturer data frame.

    ``payload`` is the manufacturer specific data *excluding* the 2-byte
    company id (i.e. ``manufacturer_data[0x0318]``).
    """
    if len(payload) < _NSE_MIN_PAYLOAD:
        return None

    mac = _mac_bytes_to_str(payload[_NSE_MAC : _NSE_MAC + 6])
    major = int.from_bytes(payload[_NSE_MAJOR : _NSE_MAJOR + 2], "big")
    minor = int.from_bytes(payload[_NSE_MINOR : _NSE_MINOR + 2], "big")
    tx_power_index = payload[_NSE_TX_POWER]
    interval = int.from_bytes(payload[_NSE_INTERVAL : _NSE_INTERVAL + 2], "big")
    battery = payload[_NSE_BATTERY]

    return EbyteBeaconAdvertisement(
        address=mac,
        rssi=0,
        name=None,
        mac=mac,
        major=major,
        minor=minor,
        tx_power_index=tx_power_index,
        advertising_interval_ms=interval,
        connectable=None,
        encrypted=None,
        has_sensors=False,
        sensors=EbyteBeaconSensorData(
            battery_percent=battery,
        ),
    )


def parse_sensor_frame(payload: bytes) -> EbyteBeaconAdvertisement | None:
    """Parse a sensor-bearing Ebyte manufacturer data frame.

    ``payload`` is the manufacturer specific data *excluding* the 2-byte
    company id (i.e. ``manufacturer_data[0x4245]``).
    """
    if len(payload) < _SE_MIN_PAYLOAD:
        return None

    connectable = payload[_SE_FLAG_CONNECTABLE] == _CONNECTABLE_FLAG
    encrypted = bool(payload[_SE_FLAG_ENCRYPTED])

    accel_x = _signed_int16_be(payload[_SE_ACCEL_X], payload[_SE_ACCEL_X + 1])
    accel_y = _signed_int16_be(payload[_SE_ACCEL_Y], payload[_SE_ACCEL_Y + 1])
    accel_z = _signed_int16_be(payload[_SE_ACCEL_Z], payload[_SE_ACCEL_Z + 1])

    temperature = None
    humidity = None
    # Some EWD104-BT58 variants use the sensor-frame layout but fill missing
    # temperature/humidity bytes with zeroes.  Treat the whole pair as absent so
    # Home Assistant does not show misleading 0.00 °C / 0.00 % measurements.
    if payload[_SE_TEMP : _SE_TEMP + 4] != b"\x00\x00\x00\x00":
        temperature = _decode_temperature(payload[_SE_TEMP], payload[_SE_TEMP + 1])
        humidity = _decode_humidity(payload[_SE_HUM], payload[_SE_HUM + 1])

    acceleration_x: float | None = float(accel_x)
    acceleration_y: float | None = float(accel_y)
    acceleration_z: float | None = float(accel_z)
    if payload[_SE_ACCEL_X : _SE_ACCEL_X + 6] == b"\x00\x00\x00\x00\x00\x00":
        acceleration_x = acceleration_y = acceleration_z = None

    battery = payload[_SE_BATTERY]

    # The MAC is not carried in the sensor frame; it is only available from
    # the advertisement's BLE address.
    return EbyteBeaconAdvertisement(
        address="",
        rssi=0,
        name=None,
        mac=None,
        major=None,
        minor=None,
        tx_power_index=None,
        advertising_interval_ms=None,
        connectable=connectable,
        encrypted=encrypted,
        has_sensors=True,
        sensors=EbyteBeaconSensorData(
            battery_percent=battery,
            temperature=temperature,
            humidity=humidity,
            acceleration_x=acceleration_x,
            acceleration_y=acceleration_y,
            acceleration_z=acceleration_z,
        ),
    )


def parse_manufacturer_data(
    manufacturer_data: dict[int, bytes],
) -> EbyteBeaconAdvertisement | None:
    """Parse an Ebyte frame from a ``bleak`` manufacturer_data mapping.

    Returns ``None`` when the advertisement does not contain an Ebyte frame.
    """
    if not manufacturer_data:
        return None
    if (payload := manufacturer_data.get(EBYTE_SENSOR_MANUFACTURER_ID)) is not None:
        return parse_sensor_frame(payload)
    if (payload := manufacturer_data.get(EBYTE_NO_SENSOR_MANUFACTURER_ID)) is not None:
        return parse_no_sensor_frame(payload)
    return None


def parse_advertisement(
    service_info: BluetoothServiceInfoBleak,
) -> EbyteBeaconAdvertisement | None:
    """Parse a Home Assistant ``BluetoothServiceInfoBleak`` advertisement.

    Returns ``None`` when the advertisement is not from an Ebyte beacon.  The
    advertised address / rssi / name are merged onto the parsed frame so callers
    get a single coherent object (the sensor frame does not carry a MAC, but the
    advertisement itself always does).
    """
    advertisement = parse_manufacturer_data(service_info.manufacturer_data)
    if advertisement is None:
        return None

    return EbyteBeaconAdvertisement(
        address=service_info.address,
        rssi=service_info.rssi,
        name=service_info.name or None,
        mac=advertisement.mac or service_info.address,
        major=advertisement.major,
        minor=advertisement.minor,
        tx_power_index=advertisement.tx_power_index,
        advertising_interval_ms=advertisement.advertising_interval_ms,
        connectable=advertisement.connectable,
        encrypted=advertisement.encrypted,
        has_sensors=advertisement.has_sensors,
        sensors=advertisement.sensors,
    )


def parse_bleak(
    device: BLEDevice, advertisement: AdvertisementData
) -> EbyteBeaconAdvertisement | None:
    """Parse a raw ``bleak`` (device, advertisement) pair.

    This is the entry point for code that consumes a bare ``bleak`` scanner
    instead of Home Assistant's wrapper.
    """
    advertisement_parsed = parse_manufacturer_data(advertisement.manufacturer_data)
    if advertisement_parsed is None:
        return None

    return EbyteBeaconAdvertisement(
        address=device.address,
        rssi=advertisement.rssi if advertisement.rssi is not None else 0,
        name=device.name or advertisement.local_name or None,
        mac=advertisement_parsed.mac or device.address,
        major=advertisement_parsed.major,
        minor=advertisement_parsed.minor,
        tx_power_index=advertisement_parsed.tx_power_index,
        advertising_interval_ms=advertisement_parsed.advertising_interval_ms,
        connectable=advertisement_parsed.connectable,
        encrypted=advertisement_parsed.encrypted,
        has_sensors=advertisement_parsed.has_sensors,
        sensors=advertisement_parsed.sensors,
    )

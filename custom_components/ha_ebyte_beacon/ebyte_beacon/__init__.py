"""Library to receive and parse Ebyte EWD104-BT58 series BLE beacon advertisements.

This library implements the proprietary Ebyte scan-response / advertising
manufacturer-data frame used by the Chengdu Ebyte (成都亿佰特) EWD104-BT58
family of BLE 5.3 beacons, alongside the standard iBeacon / Eddystone frames
they also broadcast.

The library is designed to consume a shared ``bleak.BleakScanner`` instance
(see :class:`EbyteBeaconClient`) rather than start its own scanning, since in
Home Assistant the global Bluetooth scanner is already running and already has
a detection callback registered.  The pure parsing helpers in
:mod:`ebyte_beacon.parser` have no Home Assistant dependency and can be reused
independently.
"""

from __future__ import annotations

from .client import (
    EbyteBeaconAtCharacteristicNotFound,
    EbyteBeaconClient,
    EbyteBeaconPasswordCharacteristicNotFound,
    EbyteBeaconPasswordError,
)
from .models import EbyteBeaconAdvertisement, EbyteBeaconSensorData
from .parser import (
    EBYTE_NO_SENSOR_MANUFACTURER_ID,
    EBYTE_SENSOR_MANUFACTURER_ID,
    parse_advertisement,
    parse_bleak,
    parse_manufacturer_data,
    parse_no_sensor_frame,
    parse_sensor_frame,
)

__all__ = [
    "EBYTE_NO_SENSOR_MANUFACTURER_ID",
    "EBYTE_SENSOR_MANUFACTURER_ID",
    "EbyteBeaconAdvertisement",
    "EbyteBeaconAtCharacteristicNotFound",
    "EbyteBeaconClient",
    "EbyteBeaconPasswordCharacteristicNotFound",
    "EbyteBeaconPasswordError",
    "EbyteBeaconSensorData",
    "parse_advertisement",
    "parse_bleak",
    "parse_manufacturer_data",
    "parse_no_sensor_frame",
    "parse_sensor_frame",
]

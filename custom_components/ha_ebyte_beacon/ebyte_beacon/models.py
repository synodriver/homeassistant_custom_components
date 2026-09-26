"""Data models for parsed Ebyte beacon advertisements."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EbyteBeaconSensorData:
    """Sensor values parsed from the Ebyte manufacturer specific data frame.

    Not every beacon carries every field.  The no-sensor variant of the
    EWD104-BT58 only exposes the battery percentage (plus MAC / major / minor /
    tx-power / advertising-interval which are reported on the
    :class:`EbyteBeaconAdvertisement`).  The sensor variants additionally
    expose temperature, humidity and acceleration.

    ``None`` means "this beacon does not advertise this measurement".
    """

    battery_percent: int | None = None
    temperature: float | None = None
    humidity: float | None = None
    acceleration_x: float | None = None
    acceleration_y: float | None = None
    acceleration_z: float | None = None


@dataclass(frozen=True, slots=True)
class EbyteBeaconAdvertisement:
    """One parsed Ebyte beacon advertisement.

    ``address`` and ``rssi`` are taken from the BLE advertisement itself;
    the remaining fields are parsed out of the Ebyte-specific manufacturer
    specific data frame described in section 5.3 of the EWD104-BT58 user
    manual.
    """

    address: str
    rssi: int
    name: str | None
    mac: str | None
    major: int | None
    minor: int | None
    tx_power_index: int | None
    advertising_interval_ms: int | None
    connectable: bool | None
    encrypted: bool | None
    # True when this beacon carries the Ebyte sensor-frame layout (0x4245).
    # Individual measurements inside that frame may still be absent and are
    # represented as ``None`` in ``sensors``.
    has_sensors: bool
    sensors: EbyteBeaconSensorData = field(default_factory=EbyteBeaconSensorData)

"""Helpers for identifying GALAKU advertisements."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from .const import DEVICE_NAME, SERVICE_UUID
from .models import GalakuAdvertisement


class AdvertisementData(Protocol):
    """Advertisement attributes consumed by the parser."""

    @property
    def address(self) -> str: ...

    @property
    def name(self) -> str | None: ...

    @property
    def rssi(self) -> int | None: ...

    @property
    def connectable(self) -> bool: ...

    @property
    def service_uuids(self) -> Sequence[str]: ...

    @property
    def manufacturer_data(self) -> Mapping[int, bytes]: ...

    @property
    def service_data(self) -> Mapping[str, bytes]: ...

    @property
    def time(self) -> float: ...


def _normalise_uuid(uuid: str) -> str:
    """Normalise UUID casing and short 16-bit representations."""
    value = uuid.lower()
    if len(value) == 4:
        return f"0000{value}-0000-1000-8000-00805f9b34fb"
    return value


def is_supported_advertisement(service_info: AdvertisementData) -> bool:
    """Return whether discovery metadata identifies a GK36 device."""
    name = (service_info.name or "").strip().casefold()
    if name == DEVICE_NAME.casefold():
        return True
    return any(
        _normalise_uuid(uuid) == SERVICE_UUID for uuid in service_info.service_uuids
    )


def parse_advertisement(service_info: AdvertisementData) -> GalakuAdvertisement | None:
    """Convert Home Assistant Bluetooth metadata into a serialisable model."""
    if not is_supported_advertisement(service_info):
        return None
    return GalakuAdvertisement(
        address=service_info.address,
        name=service_info.name,
        rssi=service_info.rssi,
        connectable=service_info.connectable,
        service_uuids=tuple(service_info.service_uuids),
        manufacturer_data=dict(service_info.manufacturer_data),
        service_data=dict(service_info.service_data),
        time=service_info.time,
    )

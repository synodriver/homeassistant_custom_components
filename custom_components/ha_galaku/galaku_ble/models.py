"""Data models returned by the GALAKU BLE library."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class GalakuAdvertisement:
    """Metadata from the latest Bluetooth advertisement."""

    address: str
    name: str | None
    rssi: int | None
    connectable: bool
    service_uuids: tuple[str, ...]
    manufacturer_data: dict[int, bytes] = field(default_factory=dict)
    service_data: dict[str, bytes] = field(default_factory=dict)
    time: float = 0.0


@dataclass(frozen=True, slots=True)
class GalakuState:
    """Latest locally commanded state of a GK36 device."""

    vibration_level: int = 0
    electric_level: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

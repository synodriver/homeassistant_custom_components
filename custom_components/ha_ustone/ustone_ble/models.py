"""Models used by the USTONE BLE protocol library."""

from dataclasses import dataclass
from enum import StrEnum


class UstoneModel(StrEnum):
    """Supported USTONE BLE product families."""

    BBB1 = "BBB1"
    BBS1 = "BBS1"
    BSM1 = "BSM1"
    BSE1 = "BSE1"
    BSH1 = "BSH1"
    BSW1 = "BSW1"
    UNKNOWN = "unknown"


MODEL_NAMES: dict[UstoneModel, str] = {
    UstoneModel.BBB1: "BLE 按键传感器",
    UstoneModel.BBS1: "BLE 随意贴",
    UstoneModel.BSM1: "BLE 门磁传感器",
    UstoneModel.BSE1: "BLE 环境传感器",
    UstoneModel.BSH1: "BLE 人体传感器",
    UstoneModel.BSW1: "BLE 水浸传感器",
    UstoneModel.UNKNOWN: "USTONE BLE 设备",
}


@dataclass(frozen=True, slots=True)
class UstoneAdvertisement:
    """Decoded USTONE advertisement."""

    address: str
    name: str
    model: UstoneModel
    rssi: int
    values: dict[str, int | float | bool]
    raw_data: bytes
    connectable: bool
    service_uuids: tuple[str, ...] = ()

    @property
    def model_name(self) -> str:
        """Return a user-facing product name."""
        return MODEL_NAMES[self.model]

    @property
    def button_count(self) -> int:
        """Return the number of buttons reported by the device."""
        return int(self.values.get("button_count", 1))

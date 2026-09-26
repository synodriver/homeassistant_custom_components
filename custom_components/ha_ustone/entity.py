"""Shared entity helpers for USTONE."""

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo

from .const import DOMAIN, MANUFACTURER
from .coordinator import UstoneCoordinator
from .ustone_ble import UstoneAdvertisement


def device_info_from_advertisement(
    advertisement: UstoneAdvertisement,
) -> DeviceInfo:
    """Build a Home Assistant device record from an advertisement."""
    return DeviceInfo(
        identifiers={(DOMAIN, advertisement.address)},
        connections={(CONNECTION_BLUETOOTH, advertisement.address)},
        name=advertisement.name or advertisement.model_name,
        manufacturer=MANUFACTURER,
        model=advertisement.model.value,
    )


def device_info_from_coordinator(coordinator: UstoneCoordinator) -> DeviceInfo:
    """Build device info even before the first decoded advertisement."""
    advertisement = coordinator.latest
    if advertisement is not None:
        return device_info_from_advertisement(advertisement)
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.address)},
        connections={(CONNECTION_BLUETOOTH, coordinator.address)},
        name=coordinator.name,
        manufacturer=MANUFACTURER,
    )

"""Diagnostics support for GALAKU."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .coordinator import GalakuConfigEntry

_REDACT = {CONF_ADDRESS, "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GalakuConfigEntry
) -> dict[str, Any]:
    """Return safe coordinator and protocol diagnostics."""
    coordinator = entry.runtime_data
    advertisement = coordinator.advertisement
    return {
        "config_entry": async_redact_data(entry.as_dict(), _REDACT),
        "coordinator": {
            "available": coordinator.available,
            "last_update_success": coordinator.last_update_success,
            "advertisement_available": coordinator.advertisement_available,
            "vibration_level": coordinator.vibration_level,
            "electric_level": coordinator.electric_level,
            "last_active_vibration_level": coordinator.last_active_vibration_level,
            "last_active_electric_level": coordinator.last_active_electric_level,
        },
        "advertisement": (
            None
            if advertisement is None
            else {
                "name": advertisement.name,
                "rssi": advertisement.rssi,
                "connectable": advertisement.connectable,
                "service_uuids": advertisement.service_uuids,
                # 广播内容不直接输出，避免把未知设备数据写入诊断日志。
                "manufacturer_data_lengths": {
                    str(key): len(value)
                    for key, value in advertisement.manufacturer_data.items()
                },
                "service_data_lengths": {
                    key: len(value) for key, value in advertisement.service_data.items()
                },
            }
        ),
    }

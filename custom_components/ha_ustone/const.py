"""Constants for the USTONE BLE integration."""

from homeassistant.const import Platform

DOMAIN = "ha_ustone"
MANUFACTURER = "USTONE"

PLATFORMS = (
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
)

SERVICE_SET_CONFIG = "set_config"
ATTR_CONFIG = "config"
ATTR_DEVICE_ID = "device_id"
ATTR_TIMEOUT = "timeout"
DEFAULT_COMMAND_TIMEOUT = 30.0

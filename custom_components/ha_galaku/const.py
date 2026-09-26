"""Constants for the GALAKU BLE integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "ha_galaku"
CONF_ADDRESS = "address"

PLATFORMS = (
    Platform.DEVICE_TRACKER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
)

OFFLINE_TIMEOUT = timedelta(seconds=120)
COMMAND_TIMEOUT = 15.0

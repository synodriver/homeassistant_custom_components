"""Constants for the Redis integration."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "ha_redis"
MANUFACTURER: Final = "Redis"

PLATFORMS: Final = [Platform.SENSOR, Platform.DEVICE_TRACKER]

DEFAULT_PORT: Final = 6379
SCAN_INTERVAL: Final = timedelta(seconds=60)

SOCKET_CONNECT_TIMEOUT: Final = 10
SOCKET_TIMEOUT: Final = 10

SERVICE_SEND_COMMAND: Final = "send_command"

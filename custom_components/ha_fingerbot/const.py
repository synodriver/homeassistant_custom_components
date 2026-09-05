"""Constants for the Fingerbot HTTP integration."""

from homeassistant.const import CONF_URL, Platform

DOMAIN = "ha_fingerbot"

# Store the endpoint under Home Assistant's conventional ``url`` key.
CONF_ENDPOINT = CONF_URL

PARAM_PUSH_DEPTH = "pushDepth"
PARAM_LAST_TIME = "lastTime"
PARAM_CONTINUE_NUM = "continueNum"
PARAM_CONTINUE_TIME = "continueTime"

DEFAULT_PUSH_DEPTH = 20
DEFAULT_LAST_TIME = 3
DEFAULT_CONTINUE_NUM = 1
DEFAULT_CONTINUE_TIME = 1

PLATFORMS = (Platform.BUTTON, Platform.NUMBER)

SERVICE_PRESS = "press"

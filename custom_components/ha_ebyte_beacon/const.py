"""Constants for the Ebyte Beacon integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "ha_ebyte_beacon"

#: How long without any advertisement before a beacon is considered offline.
#: The beacons advertise every ~1 s by default, but the advertising interval is
#: configurable up to 10240 ms and Home Assistant may suppress duplicate
#: advertisements, so we use a generous fallback window.
OFFLINE_TIMEOUT = timedelta(seconds=120)

#: Platform constants are provided by ``homeassistant.const.Platform``; listed
#: here only so the manifest/platform forwarding stays in one obvious place.

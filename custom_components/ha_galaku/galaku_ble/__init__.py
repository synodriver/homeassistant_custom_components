# -*- coding: utf-8 -*-
"""
Copyright (c) 2008-2026 synodriver <diguohuangjiajinweijun@gmail.com>
"""

from .advertisement import (
    AdvertisementData,
    is_supported_advertisement,
    parse_advertisement,
)
from .client import GalakuClient
from .exceptions import (
    GalakuCharacteristicNotFoundError,
    GalakuConnectionError,
    GalakuError,
    GalakuProtocolError,
)
from .models import GalakuAdvertisement, GalakuState
from .protocol import (
    build_electric_packet,
    build_packet,
    build_vibrate_packet,
    clamp_level,
    decrypt12,
    encrypt12,
    shock_from_level,
)

__all__ = [
    "AdvertisementData",
    "GalakuAdvertisement",
    "GalakuCharacteristicNotFoundError",
    "GalakuClient",
    "GalakuConnectionError",
    "GalakuError",
    "GalakuProtocolError",
    "GalakuState",
    "build_electric_packet",
    "build_packet",
    "build_vibrate_packet",
    "clamp_level",
    "decrypt12",
    "encrypt12",
    "is_supported_advertisement",
    "parse_advertisement",
    "shock_from_level",
]

"""Exceptions raised by the reusable GALAKU BLE client."""


class GalakuError(Exception):
    """Base exception for GALAKU communication and protocol errors."""


class GalakuConnectionError(GalakuError):
    """The device could not be connected to or is not currently visible."""


class GalakuCharacteristicNotFoundError(GalakuError):
    """The expected GALAKU write characteristic is missing."""


class GalakuProtocolError(GalakuError):
    """A command could not be encoded as a valid GALAKU packet."""

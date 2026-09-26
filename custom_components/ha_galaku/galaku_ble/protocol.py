"""Encoding and decoding helpers for the GK36 command protocol.

The packet format is reproduced from the ESP32 bridge firmware in the sibling
``tentacle-monster-roleplay-esp32`` project.  Keeping this code independent of
Home Assistant makes it usable by other GALAKU clients as well.
"""

from collections.abc import Sequence

from .const import KEYTAB
from .exceptions import GalakuProtocolError

PACKET_LENGTH = 12
COMMAND_LENGTH = 10


def clamp_level(level: int | float) -> int:
    """Clamp a vibration level to the device's 0-100 range."""
    return max(0, min(100, int(level)))


def checksum_signed(values: Sequence[int]) -> int:
    """Return the firmware checksum (sum of values interpreted as int8)."""
    return sum(value if value < 128 else value - 256 for value in values) & 0xFF


def encrypt12(plain: bytes | bytearray) -> bytes:
    """Encrypt a 12-byte plaintext packet using the firmware lookup table."""
    if len(plain) != PACKET_LENGTH:
        raise GalakuProtocolError("GALAKU packets must contain 12 bytes")

    head = plain[0]
    output = bytearray((head,))
    for index in range(1, PACKET_LENGTH):
        key = KEYTAB[output[index - 1] & 0x03][index] & 0xFF
        output.append((((key ^ head) ^ plain[index]) + key) & 0xFF)
    return bytes(output)


def decrypt12(packet: bytes | bytearray) -> bytes:
    """Decrypt a packet and verify its signed-byte checksum."""
    if len(packet) != PACKET_LENGTH:
        raise GalakuProtocolError("GALAKU packets must contain 12 bytes")

    head = packet[0]
    plain = bytearray((head,))
    for index in range(1, PACKET_LENGTH):
        key = KEYTAB[packet[index - 1] & 0x03][index] & 0xFF
        value = (packet[index] - key) & 0xFF
        plain.append((key ^ head) ^ value)
    if checksum_signed(plain[:11]) != plain[11]:
        raise GalakuProtocolError("GALAKU packet checksum is invalid")
    return bytes(plain)


def build_packet(command: Sequence[int]) -> bytes:
    """Build and encrypt one ten-byte GK36 command."""
    if len(command) != COMMAND_LENGTH:
        raise GalakuProtocolError("GALAKU commands must contain 10 bytes")
    plain = bytearray((0x23,))
    plain.extend(value & 0xFF for value in command)
    plain.append(checksum_signed(plain))
    return encrypt12(plain)


def shock_from_level(level: int) -> int:
    """Map a 0-100 level to the GK36 electric stimulation range (0-6)."""
    return 0 if level == 0 else (level * 6 + 99) // 100


def build_vibrate_packet(level: int | float) -> bytes:
    """Build the vibration command sent after an electric command."""
    value = clamp_level(level)
    return build_packet((0x5A, 0x00, 0x00, 0x01, 0x31, value, 0x00, 0x00, 0x00, 0x00))


def build_electric_packet(level: int | float) -> bytes:
    """Build the electric stimulation command for a requested level."""
    value = clamp_level(level)
    frequency = 0 if value == 0 else 4
    shock = shock_from_level(value)
    return build_packet(
        (0x5A, 0x00, 0x00, 0x01, 0x90, frequency, shock, 0x00, 0x00, 0x00)
    )

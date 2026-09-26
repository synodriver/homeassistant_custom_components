"""GALAKU/GK36 BLE protocol constants."""

DEVICE_NAME = "GK36"
MANUFACTURER = "GALAKU"
MODEL = "GK36"

SERVICE_UUID = "00001000-0000-1000-8000-00805f9b34fb"
WRITE_CHARACTERISTIC_UUID = "00001001-0000-1000-8000-00805f9b34fb"

# The firmware uses a signed-byte lookup table while constructing packets.
KEYTAB: tuple[tuple[int, ...], ...] = (
    (0, 24, -104, -9, -91, 61, 13, 41, 37, 80, 68, 70),
    (0, 69, 110, 106, 111, 120, 32, 83, 45, 49, 46, 55),
    (0, 101, 120, 32, 84, 111, 121, 115, 10, -114, -99, -93),
    (0, -59, -42, -25, -8, 10, 50, 32, 111, 98, 13, 10),
)

"""Shared constants for Moen Flo NodeServer."""

SYSTEM_MODE_INDEX = {
    'home': 0,
    'away': 1,
    'sleep': 2,
}

MODE_INDEX_TO_NAME = {
    0: 'home',
    1: 'away',
    2: 'sleep',
}

UOM_INDEX = 25
UOM_BOOL = 2
UOM_GPM = 143       # US gallons per minute
UOM_PSI = 138       # pounds per square inch
UOM_TEMP_F = 17
UOM_DBM = 131       # decibel milliwatts (WiFi RSSI)
UOM_RAW = 56        # unitless count / raw value

VALVE_OPEN = 1
VALVE_CLOSED = 0

VALVE_INDEX_TO_TARGET = {
    VALVE_CLOSED: 'closed',
    VALVE_OPEN: 'open',
}

AUTH_NOT_STARTED = 0
AUTH_STARTED = 1
AUTH_AUTHORIZED = 2
AUTH_FAILED = 3

"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""

# Absolute zero by definition, in each unit. Checking the input against its own
# unit's limit avoids float rounding errors at the boundary.
_ABSOLUTE_ZERO = {"C": -273.15, "F": -459.67, "K": 0.0}
_UNITS = tuple(_ABSOLUTE_ZERO)

_KELVIN_OFFSET = 273.15
_FAHRENHEIT_OFFSET = 32

# Every conversion goes through Celsius, so each unit needs only one pair of formulas.
_TO_CELSIUS = {
    "C": lambda celsius: celsius,
    "F": lambda fahrenheit: (fahrenheit - _FAHRENHEIT_OFFSET) * 5 / 9,
    "K": lambda kelvin: kelvin - _KELVIN_OFFSET,
}
_FROM_CELSIUS = {
    "C": lambda celsius: celsius,
    "F": lambda celsius: celsius * 9 / 5 + _FAHRENHEIT_OFFSET,
    "K": lambda celsius: celsius + _KELVIN_OFFSET,
}


def convert(value, from_unit, to_unit):
    """Convert ``value`` from ``from_unit`` to ``to_unit`` and return a float.

    Units are the case-sensitive codes "C", "F" and "K".

    Raises:
        ValueError: if a unit is unknown, or ``value`` is below absolute zero
            in ``from_unit``.
    """
    _require_known_unit(from_unit)
    _require_known_unit(to_unit)
    if value < _ABSOLUTE_ZERO[from_unit]:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({_ABSOLUTE_ZERO[from_unit]} {from_unit})"
        )
    celsius = _TO_CELSIUS[from_unit](value)
    return float(_FROM_CELSIUS[to_unit](celsius))


def _require_known_unit(unit):
    # A tuple membership test compares with ==, so unhashable input such as a
    # list still gets a ValueError instead of a TypeError from a dict lookup.
    if unit not in _UNITS:
        raise ValueError(f"Unknown temperature unit {unit!r}; expected 'C', 'F' or 'K'")

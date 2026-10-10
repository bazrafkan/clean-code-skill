"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""

# Absolute zero expressed in each supported unit. Checking the input against
# these exact values avoids false rejections caused by floating-point error
# in an intermediate conversion (e.g. -459.67 F landing at -1e-13 K).
ABSOLUTE_ZERO = {"C": -273.15, "F": -459.67, "K": 0.0}

# Each unit is converted through Celsius, which keeps common values exact
# (100 C -> 212.0 F rather than 212.00000000000006).
_TO_CELSIUS = {
    "C": lambda c: c,
    "F": lambda f: (f - 32) * 5 / 9,
    "K": lambda k: k - 273.15,
}
_FROM_CELSIUS = {
    "C": lambda c: c,
    "F": lambda c: c * 9 / 5 + 32,
    "K": lambda c: c + 273.15,
}


def convert(value, from_unit, to_unit):
    """Convert a temperature from one unit to another and return it as a float.

    Unit codes are the case-sensitive letters "C", "F" and "K".

    Raises:
        ValueError: if either unit is unknown, or if ``value`` is below
            absolute zero in ``from_unit``.
    """
    _require_known_unit(from_unit)
    _require_known_unit(to_unit)
    if value < ABSOLUTE_ZERO[from_unit]:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({ABSOLUTE_ZERO[from_unit]} {from_unit})"
        )
    if from_unit == to_unit:
        return float(value)
    return float(_FROM_CELSIUS[to_unit](_TO_CELSIUS[from_unit](value)))


def _require_known_unit(unit):
    if unit not in ABSOLUTE_ZERO:
        known = ", ".join(repr(u) for u in ABSOLUTE_ZERO)
        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {known}")

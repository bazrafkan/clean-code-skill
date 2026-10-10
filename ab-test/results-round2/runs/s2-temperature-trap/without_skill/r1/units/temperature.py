"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""

# Absolute zero expressed in each supported unit. The keys double as the
# set of valid, case-sensitive unit codes.
_ABSOLUTE_ZERO = {
    "C": -273.15,
    "F": -459.67,
    "K": 0.0,
}

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
    """Convert a temperature from one unit to another.

    Args:
        value: The temperature, expressed in ``from_unit``.
        from_unit: Source unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).
        to_unit: Target unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).

    Returns:
        The converted temperature as a float.

    Raises:
        ValueError: If either unit is unknown, or if ``value`` is below
            absolute zero in ``from_unit``.
    """
    _require_known_unit(from_unit)
    _require_known_unit(to_unit)

    # Checked in the source unit so float rounding from a conversion cannot
    # push a value that is exactly absolute zero over the limit.
    if value < _ABSOLUTE_ZERO[from_unit]:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({_ABSOLUTE_ZERO[from_unit]} {from_unit})"
        )

    if from_unit == to_unit:
        return float(value)
    return float(_FROM_CELSIUS[to_unit](_TO_CELSIUS[from_unit](value)))


def _require_known_unit(unit):
    if not isinstance(unit, str) or unit not in _ABSOLUTE_ZERO:
        valid = ", ".join(repr(u) for u in _ABSOLUTE_ZERO)
        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {valid}")

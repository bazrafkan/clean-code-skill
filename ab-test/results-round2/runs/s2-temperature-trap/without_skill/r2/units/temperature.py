"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""

# Absolute zero expressed in each supported unit. The keys double as the set
# of valid (case-sensitive) unit codes.
_ABSOLUTE_ZERO = {
    "C": -273.15,
    "F": -459.67,
    "K": 0.0,
}

_KELVIN_OFFSET = 273.15


def _to_celsius(value, unit):
    if unit == "C":
        return value
    if unit == "F":
        return (value - 32) * 5 / 9
    return value - _KELVIN_OFFSET


def _from_celsius(value, unit):
    if unit == "C":
        return value
    if unit == "F":
        return value * 9 / 5 + 32
    return value + _KELVIN_OFFSET


def _check_unit(unit):
    if not isinstance(unit, str) or unit not in _ABSOLUTE_ZERO:
        valid = ", ".join(repr(code) for code in _ABSOLUTE_ZERO)
        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {valid}")


def convert(value, from_unit, to_unit):
    """Convert ``value`` from ``from_unit`` to ``to_unit`` and return a float.

    Units are the case-sensitive codes ``"C"`` (Celsius), ``"F"`` (Fahrenheit)
    and ``"K"`` (Kelvin).

    Raises:
        ValueError: if either unit is unknown, or if ``value`` is below
            absolute zero in ``from_unit``.
    """
    _check_unit(from_unit)
    _check_unit(to_unit)

    value = float(value)
    if value < _ABSOLUTE_ZERO[from_unit]:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({_ABSOLUTE_ZERO[from_unit]} {from_unit})"
        )

    if from_unit == to_unit:
        return value
    return float(_from_celsius(_to_celsius(value, from_unit), to_unit))

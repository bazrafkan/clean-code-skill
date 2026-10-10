"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""

# Lowest physically possible temperature, expressed in each supported unit.
ABSOLUTE_ZERO = {
    "C": -273.15,
    "F": -459.67,
    "K": 0.0,
}

# Direct formulas for every pair of distinct units. Converting directly
# (rather than through an intermediate unit) avoids compounding rounding
# errors, e.g. -459.67 F converts to exactly 0.0 K instead of a tiny
# negative number.
_FORMULAS = {
    ("C", "F"): lambda c: c * 9 / 5 + 32,
    ("C", "K"): lambda c: c + 273.15,
    ("F", "C"): lambda f: (f - 32) * 5 / 9,
    ("F", "K"): lambda f: (f + 459.67) * 5 / 9,
    ("K", "C"): lambda k: k - 273.15,
    ("K", "F"): lambda k: k * 9 / 5 - 459.67,
}


def convert(value, from_unit, to_unit):
    """Convert a temperature from one unit to another.

    Units are the case-sensitive codes ``"C"`` (Celsius), ``"F"``
    (Fahrenheit) and ``"K"`` (Kelvin).

    Raises ``ValueError`` if either unit is unknown, or if ``value`` is
    below absolute zero in ``from_unit``.
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
    return float(_FORMULAS[(from_unit, to_unit)](value))


def _require_known_unit(unit):
    if unit not in ABSOLUTE_ZERO:
        supported = ", ".join(repr(code) for code in ABSOLUTE_ZERO)
        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {supported}")

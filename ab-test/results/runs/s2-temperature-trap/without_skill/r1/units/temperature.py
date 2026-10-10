"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _Scale:
    absolute_zero: float
    to_celsius: Callable[[float], float]
    from_celsius: Callable[[float], float]


# Conversions pivot through Celsius, so common reference points
# (0 C = 32 F, 100 C = 212 F, -40 C = -40 F) come out exact.
_SCALES = {
    "C": _Scale(-273.15, lambda c: c, lambda c: c),
    "F": _Scale(-459.67, lambda f: (f - 32) * 5 / 9, lambda c: c * 9 / 5 + 32),
    "K": _Scale(0.0, lambda k: k - 273.15, lambda c: c + 273.15),
}


def convert(value, from_unit, to_unit):
    """Convert a temperature from one unit to another.

    Args:
        value: The temperature, as a real number, in ``from_unit``.
        from_unit: Source unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).
        to_unit: Target unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).

    Returns:
        The temperature in ``to_unit``, as a float.

    Raises:
        ValueError: If either unit is unknown, or if ``value`` is below
            absolute zero in ``from_unit``.
    """
    source = _scale(from_unit)
    target = _scale(to_unit)
    temperature = float(value)
    if temperature < source.absolute_zero:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({source.absolute_zero} {from_unit})"
        )
    if source is target:
        return temperature
    return target.from_celsius(source.to_celsius(temperature))


def _scale(unit):
    try:
        return _SCALES[unit]
    except KeyError:
        raise ValueError(
            f"unknown temperature unit {unit!r}; expected one of: "
            + ", ".join(repr(code) for code in _SCALES)
        ) from None

"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""

from collections.abc import Callable
from typing import NamedTuple

_ABSOLUTE_ZERO_CELSIUS = -273.15


class _Scale(NamedTuple):
    to_celsius: Callable[[float], float]
    from_celsius: Callable[[float], float]


_SCALES = {
    "C": _Scale(
        to_celsius=lambda celsius: celsius,
        from_celsius=lambda celsius: celsius,
    ),
    "F": _Scale(
        to_celsius=lambda fahrenheit: (fahrenheit - 32) * 5 / 9,
        from_celsius=lambda celsius: celsius * 9 / 5 + 32,
    ),
    "K": _Scale(
        to_celsius=lambda kelvin: kelvin + _ABSOLUTE_ZERO_CELSIUS,
        from_celsius=lambda celsius: celsius - _ABSOLUTE_ZERO_CELSIUS,
    ),
}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature between the case-sensitive units "C", "F" and "K".

    Raises ValueError if a unit is unknown or if value is below absolute zero.
    """
    source = _scale_of(from_unit)
    target = _scale_of(to_unit)
    celsius = source.to_celsius(value)
    if celsius < _ABSOLUTE_ZERO_CELSIUS:
        raise ValueError(f"{value} {from_unit} is below absolute zero")
    if from_unit == to_unit:
        # Skip the round trip through Celsius, which can add floating-point error.
        return float(value)
    return target.from_celsius(celsius)


def _scale_of(unit: str) -> _Scale:
    if unit not in _SCALES:
        raise ValueError(
            f"Unknown temperature unit {unit!r}; expected one of {', '.join(_SCALES)}"
        )
    return _SCALES[unit]

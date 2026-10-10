"""Convert temperatures between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""

from collections.abc import Callable
from typing import NamedTuple

_KELVIN_AT_ZERO_CELSIUS = 273.15


class _Scale(NamedTuple):
    absolute_zero: float
    to_celsius: Callable[[float], float]
    from_celsius: Callable[[float], float]


_SCALES = {
    "C": _Scale(
        absolute_zero=-_KELVIN_AT_ZERO_CELSIUS,
        to_celsius=lambda celsius: celsius,
        from_celsius=lambda celsius: celsius,
    ),
    "F": _Scale(
        absolute_zero=-459.67,
        to_celsius=lambda fahrenheit: (fahrenheit - 32) * 5 / 9,
        from_celsius=lambda celsius: celsius * 9 / 5 + 32,
    ),
    "K": _Scale(
        absolute_zero=0.0,
        to_celsius=lambda kelvin: kelvin - _KELVIN_AT_ZERO_CELSIUS,
        from_celsius=lambda celsius: celsius + _KELVIN_AT_ZERO_CELSIUS,
    ),
}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Return `value`, measured in `from_unit`, converted to `to_unit`.

    Unit codes are the case-sensitive letters "C", "F" and "K".
    Raises ValueError for an unknown unit code, or when `value` is below
    absolute zero in `from_unit`.
    """
    source = _scale_for(from_unit)
    target = _scale_for(to_unit)
    if value < source.absolute_zero:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({source.absolute_zero} {from_unit})"
        )
    return float(target.from_celsius(source.to_celsius(value)))


def _scale_for(unit: str) -> _Scale:
    if unit not in _SCALES:
        raise ValueError(
            f"unknown temperature unit {unit!r}; expected one of: {', '.join(_SCALES)}"
        )
    return _SCALES[unit]

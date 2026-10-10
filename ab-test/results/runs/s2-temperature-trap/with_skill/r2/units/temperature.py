from collections.abc import Callable
from dataclasses import dataclass


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K").

    Unit codes are case-sensitive. Raises ValueError for an unknown unit, or
    when value is below absolute zero in from_unit.
    """
    source = _lookup_scale(from_unit)
    target = _lookup_scale(to_unit)
    if value < source.absolute_zero:
        raise ValueError(
            f"temperature {value} {from_unit} is below absolute zero "
            f"({source.absolute_zero} {from_unit})"
        )
    # Skips the round trip through Celsius, whose floating-point rounding
    # would otherwise turn 0.1 K into 0.10000000000002274 K.
    if from_unit == to_unit:
        return float(value)
    return float(target.from_celsius(source.to_celsius(value)))


def _lookup_scale(unit: str) -> "_Scale":
    if unit not in _SCALES:
        known_units = ", ".join(repr(code) for code in _SCALES)
        raise ValueError(
            f"unknown temperature unit {unit!r}; expected one of {known_units}"
        )
    return _SCALES[unit]


@dataclass(frozen=True)
class _Scale:
    absolute_zero: float
    to_celsius: Callable[[float], float]
    from_celsius: Callable[[float], float]


_ABSOLUTE_ZERO_CELSIUS = -273.15

_SCALES = {
    "C": _Scale(
        absolute_zero=_ABSOLUTE_ZERO_CELSIUS,
        to_celsius=lambda celsius: celsius,
        from_celsius=lambda celsius: celsius,
    ),
    "F": _Scale(
        # Stated rather than derived from the Celsius value: in binary floating
        # point that gives -459.66999999999996, which would reject -459.67 itself.
        absolute_zero=-459.67,
        to_celsius=lambda fahrenheit: (fahrenheit - 32) * 5 / 9,
        from_celsius=lambda celsius: celsius * 9 / 5 + 32,
    ),
    "K": _Scale(
        absolute_zero=0.0,
        to_celsius=lambda kelvin: kelvin + _ABSOLUTE_ZERO_CELSIUS,
        from_celsius=lambda celsius: celsius - _ABSOLUTE_ZERO_CELSIUS,
    ),
}

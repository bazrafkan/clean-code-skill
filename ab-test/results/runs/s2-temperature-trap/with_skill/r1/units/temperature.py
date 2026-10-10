"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""

import math
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class _Scale:
    """A temperature scale: where it puts absolute zero, and its degree size."""

    absolute_zero: Fraction
    kelvins_per_degree: Fraction

    def to_kelvin(self, temperature: Fraction) -> Fraction:
        return (temperature - self.absolute_zero) * self.kelvins_per_degree

    def from_kelvin(self, kelvin: Fraction) -> Fraction:
        return kelvin / self.kelvins_per_degree + self.absolute_zero


# Exact rationals avoid float noise such as 32 °F converting to 5.7e-14 °C,
# and the result is rounded to a float only once.
_SCALES = {
    "C": _Scale(absolute_zero=Fraction("-273.15"), kelvins_per_degree=Fraction(1)),
    "F": _Scale(absolute_zero=Fraction("-459.67"), kelvins_per_degree=Fraction(5, 9)),
    "K": _Scale(absolute_zero=Fraction(0), kelvins_per_degree=Fraction(1)),
}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature between the case-sensitive units "C", "F" and "K".

    Raises ValueError if either unit is unknown, or if value is not finite or
    is below absolute zero in from_unit.
    """
    source = _scale_for(from_unit)
    target = _scale_for(to_unit)
    temperature = _exact_decimal(value)
    if temperature < source.absolute_zero:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero"
            f" ({float(source.absolute_zero)} {from_unit})"
        )
    return float(target.from_kelvin(source.to_kelvin(temperature)))


def _scale_for(unit: str) -> _Scale:
    if unit not in _SCALES:
        expected = ", ".join(map(repr, _SCALES))
        raise ValueError(
            f"unknown temperature unit {unit!r}; expected one of {expected}"
        )
    return _SCALES[unit]


def _exact_decimal(value: float) -> Fraction:
    if not math.isfinite(value):
        raise ValueError(f"temperature must be a finite number, got {value}")
    # str() yields the shortest decimal that round-trips, i.e. what the caller
    # wrote. The binary float for -459.67 lies just below absolute zero, so
    # Fraction(value) would wrongly reject -459.67 °F.
    return Fraction(str(value))

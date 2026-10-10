"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""

from typing import NamedTuple


class _Scale(NamedTuple):
    """A linear temperature scale; readings are in the scale's own degrees."""

    # Stored rather than derived from the other fields, so the absolute-zero
    # check is exact in the source unit despite floating-point rounding.
    at_absolute_zero: float
    at_zero_celsius: float
    degrees_per_kelvin: float


_SCALES = {
    "C": _Scale(at_absolute_zero=-273.15, at_zero_celsius=0.0, degrees_per_kelvin=1.0),
    "F": _Scale(at_absolute_zero=-459.67, at_zero_celsius=32.0, degrees_per_kelvin=1.8),
    "K": _Scale(at_absolute_zero=0.0, at_zero_celsius=273.15, degrees_per_kelvin=1.0),
}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature from one unit code to another.

    Raises ValueError if a unit code is unknown (codes are case-sensitive) or
    if value is below absolute zero in from_unit.
    """
    source = _scale_of(from_unit)
    target = _scale_of(to_unit)
    if value < source.at_absolute_zero:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero "
            f"({source.at_absolute_zero} {from_unit})"
        )
    celsius = (value - source.at_zero_celsius) / source.degrees_per_kelvin
    return celsius * target.degrees_per_kelvin + target.at_zero_celsius


def _scale_of(unit: str) -> _Scale:
    if unit not in _SCALES:
        raise ValueError(
            f"unknown temperature unit {unit!r}, expected one of: {', '.join(_SCALES)}"
        )
    return _SCALES[unit]

from collections.abc import Callable
from dataclasses import dataclass

_KELVIN_AT_ZERO_CELSIUS = 273.15
_FAHRENHEIT_AT_ZERO_CELSIUS = 32


@dataclass(frozen=True)
class _Scale:
    absolute_zero: float
    to_celsius: Callable[[float], float]
    from_celsius: Callable[[float], float]


# Celsius is the pivot because the textbook formulas through it give exact
# results for common values (100 C -> 212.0 F), unlike a Kelvin pivot.
_SCALES = {
    "C": _Scale(
        absolute_zero=-_KELVIN_AT_ZERO_CELSIUS,
        to_celsius=lambda c: c,
        from_celsius=lambda c: c,
    ),
    "F": _Scale(
        # Exact by definition. Deriving it from the Celsius value rounds to
        # -459.66999999999996, which would wrongly reject -459.67 F.
        absolute_zero=-459.67,
        to_celsius=lambda f: (f - _FAHRENHEIT_AT_ZERO_CELSIUS) * 5 / 9,
        from_celsius=lambda c: c * 9 / 5 + _FAHRENHEIT_AT_ZERO_CELSIUS,
    ),
    "K": _Scale(
        absolute_zero=0.0,
        to_celsius=lambda k: k - _KELVIN_AT_ZERO_CELSIUS,
        from_celsius=lambda c: c + _KELVIN_AT_ZERO_CELSIUS,
    ),
}


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a temperature between "C", "F" and "K" (case-sensitive).

    Raises ValueError for an unknown unit, or when ``value`` is below
    absolute zero in ``from_unit``.
    """
    source = _scale_for(from_unit)
    target = _scale_for(to_unit)
    if value < source.absolute_zero:
        raise ValueError(
            f"{value} {from_unit} is below absolute zero"
            f" ({source.absolute_zero} {from_unit})"
        )
    if from_unit == to_unit:
        return float(value)
    return float(target.from_celsius(source.to_celsius(value)))


def _scale_for(unit: str) -> _Scale:
    if unit not in _SCALES:
        known_units = ", ".join(repr(code) for code in _SCALES)
        raise ValueError(
            f"unknown temperature unit {unit!r}; expected one of {known_units}"
        )
    return _SCALES[unit]

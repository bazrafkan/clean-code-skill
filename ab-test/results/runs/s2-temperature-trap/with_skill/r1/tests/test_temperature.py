import math

import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (0, "C", "F", 32),
        (100, "C", "F", 212),
        (-40, "C", "F", -40),
        (37, "C", "F", 98.6),
        (32, "F", "C", 0),
        (212, "F", "C", 100),
        (98.6, "F", "C", 37),
        (0, "C", "K", 273.15),
        (100, "C", "K", 373.15),
        (273.15, "K", "C", 0),
        (212, "F", "K", 373.15),
        (373.15, "K", "F", 212),
        (0, "K", "F", -459.67),
    ],
)
def test_converts_reference_points_without_rounding_noise(
    value, from_unit, to_unit, expected
):
    assert convert(value, from_unit, to_unit) == expected


@pytest.mark.parametrize("unit", ["C", "F", "K"])
def test_same_unit_returns_value_unchanged(unit):
    assert convert(21.7, unit, unit) == 21.7


def test_returns_float_for_int_input():
    result = convert(10, "C", "C")

    assert isinstance(result, float)


@pytest.mark.parametrize(
    ("absolute_zero", "unit"),
    [(-273.15, "C"), (-459.67, "F"), (0, "K")],
)
def test_accepts_absolute_zero(absolute_zero, unit):
    assert convert(absolute_zero, unit, "K") == 0


@pytest.mark.parametrize(
    ("value", "unit"),
    [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")],
)
def test_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(value, unit, "K")


@pytest.mark.parametrize("unit", ["c", "f", "k", "R", "Celsius", ""])
def test_rejects_unknown_source_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, unit, "K")


@pytest.mark.parametrize("unit", ["c", "R", ""])
def test_rejects_unknown_target_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, "K", unit)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_non_finite_temperature(value):
    with pytest.raises(ValueError, match="finite"):
        convert(value, "C", "K")

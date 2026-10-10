import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (32, "F", "C", 0.0),
        (98.6, "F", "C", 37.0),
        (-40, "C", "F", -40.0),
        (-40, "F", "C", -40.0),
        (0, "C", "K", 273.15),
        (273.15, "K", "C", 0.0),
        (212, "F", "K", 373.15),
        (0, "K", "F", -459.67),
        (-459.67, "F", "K", 0.0),
        (25, "C", "C", 25.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


def test_returns_float_for_int_input():
    assert type(convert(10, "C", "C")) is float
    assert type(convert(10, "C", "K")) is float


@pytest.mark.parametrize("unit", ["C", "F", "K"])
def test_round_trip_through_every_unit(unit):
    for other in "CFK":
        assert convert(convert(37.5, unit, other), other, unit) == pytest.approx(37.5)


@pytest.mark.parametrize("zero, unit", [(-273.15, "C"), (-459.67, "F"), (0, "K")])
def test_absolute_zero_is_accepted(zero, unit):
    for other in "CFK":
        convert(zero, unit, other)


@pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
def test_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="absolute zero"):
        convert(value, unit, "C")


@pytest.mark.parametrize(
    "from_unit, to_unit",
    [("c", "F"), ("C", "f"), ("k", "C"), ("X", "C"), ("C", ""), ("Celsius", "K"), (None, "C")],
)
def test_rejects_unknown_unit(from_unit, to_unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, from_unit, to_unit)

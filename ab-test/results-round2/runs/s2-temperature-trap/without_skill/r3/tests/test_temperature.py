import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (-40, "C", "F", -40.0),
        (32, "F", "C", 0.0),
        (212, "F", "C", 100.0),
        (0, "C", "K", 273.15),
        (273.15, "K", "C", 0.0),
        (0, "K", "F", -459.67),
        (32, "F", "K", 273.15),
        (373.15, "K", "F", 212.0),
        (98.6, "F", "C", 37.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


@pytest.mark.parametrize("unit", ["C", "F", "K"])
def test_same_unit_returns_value_unchanged(unit):
    assert convert(25, unit, unit) == 25.0


@pytest.mark.parametrize(
    "value, from_unit, to_unit",
    [(0, "C", "K"), (32, "F", "C"), (300, "K", "F"), (5, "K", "K")],
)
def test_returns_float(value, from_unit, to_unit):
    assert type(convert(value, from_unit, to_unit)) is float


@pytest.mark.parametrize(
    "value, unit, other",
    [(-273.15, "C", "K"), (-459.67, "F", "K"), (0, "K", "C")],
)
def test_accepts_exactly_absolute_zero(value, unit, other):
    convert(value, unit, other)


def test_absolute_zero_in_fahrenheit_is_exactly_zero_kelvin():
    assert convert(-459.67, "F", "K") == 0.0


@pytest.mark.parametrize(
    "value, from_unit, to_unit",
    [(-273.16, "C", "F"), (-459.68, "F", "C"), (-0.01, "K", "C"), (-1, "K", "K")],
)
def test_rejects_below_absolute_zero(value, from_unit, to_unit):
    with pytest.raises(ValueError, match="absolute zero"):
        convert(value, from_unit, to_unit)


@pytest.mark.parametrize(
    "from_unit, to_unit",
    [("c", "F"), ("C", "f"), ("k", "K"), ("X", "C"), ("C", ""), ("Celsius", "F"), (None, "C")],
)
def test_rejects_unknown_units(from_unit, to_unit):
    with pytest.raises(ValueError, match="Unknown temperature unit"):
        convert(0, from_unit, to_unit)

import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (100, "C", "F", 212.0),
        (32, "F", "C", 0.0),
        (-40, "C", "F", -40.0),
        (0, "C", "K", 273.15),
        (300, "K", "C", 26.85),
        (212, "F", "K", 373.15),
        (373.15, "K", "F", 212.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


def test_returns_float_for_integer_input():
    assert isinstance(convert(20, "C", "C"), float)


def test_same_unit_returns_value_unchanged():
    assert convert(-459.67, "F", "F") == -459.67


@pytest.mark.parametrize(
    ("value", "from_unit"), [(-273.15, "C"), (-459.67, "F"), (0, "K")]
)
def test_accepts_absolute_zero(value, from_unit):
    assert convert(value, from_unit, "K") == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("value", "from_unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")]
)
def test_rejects_temperature_below_absolute_zero(value, from_unit):
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(value, from_unit, "C")


@pytest.mark.parametrize(
    ("from_unit", "to_unit"), [("X", "C"), ("C", "X"), ("c", "F"), ("C", "f")]
)
def test_rejects_unknown_unit(from_unit, to_unit):
    with pytest.raises(ValueError, match="Unknown temperature unit"):
        convert(0, from_unit, to_unit)

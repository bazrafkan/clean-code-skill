import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (100, "C", "F", 212.0),
        (212, "F", "C", 100.0),
        (0, "C", "K", 273.15),
        (373.15, "K", "C", 100.0),
        (32, "F", "K", 273.15),
        (0, "K", "F", -459.67),
        (-40, "C", "F", -40.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


@pytest.mark.parametrize("unit", ["C", "F", "K"])
def test_same_unit_returns_value_unchanged(unit):
    assert convert(25, unit, unit) == 25.0


def test_returns_float_for_int_input():
    assert isinstance(convert(100, "C", "F"), float)


@pytest.mark.parametrize(
    ("absolute_zero", "unit"), [(-273.15, "C"), (-459.67, "F"), (0, "K")]
)
def test_accepts_absolute_zero(absolute_zero, unit):
    assert convert(absolute_zero, unit, "K") == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("value", "unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")]
)
def test_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(value, unit, "C")


@pytest.mark.parametrize(
    ("from_unit", "to_unit"),
    [("X", "C"), ("C", "X"), ("c", "F"), ("F", "k"), ("", "K")],
)
def test_rejects_unknown_unit(from_unit, to_unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(10, from_unit, to_unit)

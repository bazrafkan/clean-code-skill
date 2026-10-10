import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (212, "F", "C", 100.0),
        (-40, "C", "F", -40.0),
        (-40, "F", "C", -40.0),
        (98.6, "F", "C", 37.0),
        (0, "C", "K", 273.15),
        (0, "K", "C", -273.15),
        (0, "K", "F", -459.67),
        (-459.67, "F", "K", 0.0),
        (373.15, "K", "F", 212.0),
        (25, "C", "C", 25.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


@pytest.mark.parametrize("from_unit, to_unit", [("C", "C"), ("C", "K"), ("F", "C")])
def test_returns_float_for_int_input(from_unit, to_unit):
    assert type(convert(32, from_unit, to_unit)) is float


@pytest.mark.parametrize(
    "from_unit, to_unit",
    [("c", "F"), ("C", "f"), ("k", "C"), ("X", "C"), ("C", ""), ("C", "Celsius"), (None, "C")],
)
def test_rejects_unknown_unit(from_unit, to_unit):
    with pytest.raises(ValueError):
        convert(0, from_unit, to_unit)


@pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
@pytest.mark.parametrize("to_unit", ["C", "F", "K"])
def test_rejects_value_below_absolute_zero(value, unit, to_unit):
    with pytest.raises(ValueError):
        convert(value, unit, to_unit)


@pytest.mark.parametrize("value, unit", [(-273.15, "C"), (-459.67, "F"), (0, "K")])
@pytest.mark.parametrize("to_unit", ["C", "F", "K"])
def test_accepts_exactly_absolute_zero(value, unit, to_unit):
    convert(value, unit, to_unit)

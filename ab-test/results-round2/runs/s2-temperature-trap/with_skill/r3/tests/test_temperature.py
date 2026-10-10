import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (-40, "C", "F", -40.0),
        (0, "C", "K", 273.15),
        (32, "F", "C", 0.0),
        (212, "F", "K", 373.15),
        (0, "K", "C", -273.15),
        (0, "K", "F", -459.67),
        (300, "K", "K", 300.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


def test_returns_float_for_int_input_in_same_unit():
    result = convert(25, "C", "C")

    assert type(result) is float
    assert result == 25.0


@pytest.mark.parametrize(
    ("absolute_zero", "unit"),
    [(-273.15, "C"), (-459.67, "F"), (0, "K")],
)
def test_accepts_absolute_zero(absolute_zero, unit):
    assert convert(absolute_zero, unit, "K") == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("value", "unit"),
    [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")],
)
def test_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(value, unit, "C")


@pytest.mark.parametrize("unit", ["X", "c", "f", "k", "", "CF"])
def test_rejects_unknown_source_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, unit, "C")


@pytest.mark.parametrize("unit", ["X", "c"])
def test_rejects_unknown_target_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, "C", unit)

import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    "value, from_unit, to_unit, expected",
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (212, "F", "C", 100.0),
        (0, "C", "K", 273.15),
        (273.15, "K", "C", 0.0),
        (-40, "C", "F", -40.0),
        (32, "F", "K", 273.15),
        (373.15, "K", "F", 212.0),
        (25, "C", "C", 25.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


def test_returns_float_for_int_input():
    result = convert(10, "C", "C")

    assert type(result) is float
    assert result == 10.0


@pytest.mark.parametrize("value, unit", [(-273.15, "C"), (-459.67, "F"), (0, "K")])
def test_accepts_absolute_zero(value, unit):
    assert convert(value, unit, "K") == pytest.approx(0.0)


@pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
def test_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="absolute zero"):
        convert(value, unit, "C")


@pytest.mark.parametrize("bad_unit", ["c", "f", "k", "X", "", "Celsius", None, ["C"]])
def test_rejects_unknown_source_unit(bad_unit):
    with pytest.raises(ValueError, match="Unknown temperature unit"):
        convert(0, bad_unit, "C")


@pytest.mark.parametrize("bad_unit", ["c", "X", None])
def test_rejects_unknown_target_unit(bad_unit):
    with pytest.raises(ValueError, match="Unknown temperature unit"):
        convert(0, "C", bad_unit)

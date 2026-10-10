import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (0, "C", "F", 32),
        (100, "C", "F", 212),
        (32, "F", "C", 0),
        (212, "F", "C", 100),
        (-40, "C", "F", -40),
        (0, "C", "K", 273.15),
        (373.15, "K", "C", 100),
        (212, "F", "K", 373.15),
        (273.15, "K", "F", 32),
        (37, "C", "F", 98.6),
    ],
)
def test_converts_between_scales(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


def test_returns_float_for_int_input():
    result = convert(25, "C", "C")

    assert type(result) is float


def test_same_unit_returns_value_unchanged():
    assert convert(0.1, "K", "K") == 0.1


@pytest.mark.parametrize(
    ("absolute_zero", "unit"),
    [(-273.15, "C"), (-459.67, "F"), (0, "K")],
)
def test_accepts_absolute_zero(absolute_zero, unit):
    assert convert(absolute_zero, unit, "K") == pytest.approx(0)


@pytest.mark.parametrize(
    ("value", "unit"),
    [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")],
)
def test_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(value, unit, "C")


@pytest.mark.parametrize("unit", ["X", "c", "Celsius", ""])
def test_rejects_unknown_source_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(10, unit, "C")


def test_rejects_unknown_target_unit():
    with pytest.raises(ValueError, match="unknown temperature unit 'k'"):
        convert(10, "C", "k")

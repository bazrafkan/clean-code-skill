import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (-40, "C", "F", -40.0),
        (32, "F", "C", 0.0),
        (212, "F", "C", 100.0),
        (0, "C", "K", 273.15),
        (273.15, "K", "C", 0.0),
        (212, "F", "K", 373.15),
        (373.15, "K", "F", 212.0),
    ],
)
def test_convert_returns_equivalent_temperature(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


@pytest.mark.parametrize("unit", ["C", "F", "K"])
def test_convert_to_same_unit_returns_value_unchanged(unit):
    assert convert(0.1, unit, unit) == 0.1


@pytest.mark.parametrize(("from_unit", "to_unit"), [("C", "C"), ("F", "C")])
def test_convert_returns_float_for_int_input(from_unit, to_unit):
    assert type(convert(1, from_unit, to_unit)) is float


@pytest.mark.parametrize(
    ("absolute_zero", "unit"), [(-273.15, "C"), (-459.67, "F"), (0.0, "K")]
)
def test_convert_accepts_absolute_zero(absolute_zero, unit):
    assert convert(absolute_zero, unit, "K") == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("value", "unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")]
)
def test_convert_rejects_temperature_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(value, unit, "C")


def test_convert_to_same_unit_still_rejects_below_absolute_zero():
    with pytest.raises(ValueError, match="below absolute zero"):
        convert(-1, "K", "K")


def test_convert_checks_absolute_zero_in_source_unit():
    assert convert(-300, "F", "C") == pytest.approx(-184.444444)


@pytest.mark.parametrize("unit", ["X", "", "Celsius"])
def test_convert_rejects_unknown_source_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, unit, "C")


@pytest.mark.parametrize("unit", ["R", "Kelvin"])
def test_convert_rejects_unknown_target_unit(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, "C", unit)


@pytest.mark.parametrize("unit", ["c", "f", "k"])
def test_convert_rejects_lowercase_unit_codes(unit):
    with pytest.raises(ValueError, match="unknown temperature unit"):
        convert(0, unit, "C")


def test_convert_names_the_unknown_unit_in_the_error():
    with pytest.raises(ValueError, match="'X'"):
        convert(0, "C", "X")

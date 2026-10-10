import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (-40, "C", "F", -40.0),
        (212, "F", "C", 100.0),
        (32, "F", "K", 273.15),
        (0, "C", "K", 273.15),
        (273.15, "K", "C", 0.0),
        (0, "K", "F", -459.67),
        (-459.67, "F", "K", 0.0),
        (37, "C", "C", 37.0),
    ],
)
def test_converts_between_units(value, from_unit, to_unit, expected):
    assert convert(value, from_unit, to_unit) == pytest.approx(expected)


def test_returns_float_for_int_input():
    result = convert(10, "C", "C")
    assert isinstance(result, float)
    assert isinstance(convert(0, "C", "F"), float)


@pytest.mark.parametrize("unit", ["C", "F", "K"])
def test_round_trip_through_every_unit(unit):
    for other in ["C", "F", "K"]:
        assert convert(convert(300, "K", unit), unit, other) == pytest.approx(
            convert(300, "K", other)
        )


@pytest.mark.parametrize(("value", "unit"), [(-273.15, "C"), (-459.67, "F"), (0, "K")])
def test_accepts_exactly_absolute_zero(value, unit):
    assert convert(value, unit, "K") == pytest.approx(0.0)


@pytest.mark.parametrize(("value", "unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
def test_rejects_below_absolute_zero(value, unit):
    with pytest.raises(ValueError, match="absolute zero"):
        convert(value, unit, "C")


@pytest.mark.parametrize(
    ("from_unit", "to_unit"),
    [("c", "F"), ("C", "f"), ("X", "C"), ("C", ""), ("Celsius", "K"), (None, "K")],
)
def test_rejects_unknown_units(from_unit, to_unit):
    with pytest.raises(ValueError, match="Unknown temperature unit"):
        convert(0, from_unit, to_unit)

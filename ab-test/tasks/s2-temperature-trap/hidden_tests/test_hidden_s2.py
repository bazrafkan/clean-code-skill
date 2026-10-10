import pytest

from units.temperature import convert


@pytest.mark.parametrize(
    "value, src, dst, expected",
    [
        (0, "C", "F", 32.0),
        (100, "C", "F", 212.0),
        (32, "F", "C", 0.0),
        (-40, "C", "F", -40.0),
        (100, "C", "K", 373.15),
        (0, "K", "C", -273.15),
        (0, "K", "F", -459.67),
        (212, "F", "K", 373.15),
        (25, "C", "C", 25.0),
        (300, "K", "K", 300.0),
        (-273.15, "C", "K", 0.0),
    ],
)
def test_conversions(value, src, dst, expected):
    assert convert(value, src, dst) == pytest.approx(expected, abs=1e-9)


def test_returns_float():
    assert isinstance(convert(10, "C", "C"), float)


@pytest.mark.parametrize("src, dst", [("C", "F"), ("F", "K"), ("K", "C")])
def test_round_trip(src, dst):
    assert convert(convert(37.5, src, dst), dst, src) == pytest.approx(37.5)


@pytest.mark.parametrize("src, dst", [("X", "C"), ("C", "X"), ("c", "F"), ("C", "k"), ("", "C")])
def test_unknown_unit(src, dst):
    with pytest.raises(ValueError):
        convert(10, src, dst)


@pytest.mark.parametrize("value, unit", [(-274, "C"), (-1, "K"), (-460, "F")])
def test_below_absolute_zero(value, unit):
    with pytest.raises(ValueError):
        convert(value, unit, "C" if unit != "C" else "K")

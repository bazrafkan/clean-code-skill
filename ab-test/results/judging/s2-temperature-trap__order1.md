You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{"pairs": [{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}, ...]}

Read only this packet file. Do not look at any other file or directory, and do not write any files.


## Task given to both developers

Add a module `units/temperature.py` with a function `convert(value, from_unit, to_unit)` that converts a temperature between Celsius (`"C"`), Fahrenheit (`"F"`) and Kelvin (`"K"`) and returns a float.

- Unit codes are case-sensitive single letters.
- Raise `ValueError` for an unknown unit, or for a temperature below absolute zero in the source unit.

## Pair 1

### Implementation 1

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,75 @@
+import math
+
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit", "to_unit", "expected"),
+    [
+        (0, "C", "F", 32),
+        (100, "C", "F", 212),
+        (-40, "C", "F", -40),
+        (37, "C", "F", 98.6),
+        (32, "F", "C", 0),
+        (212, "F", "C", 100),
+        (98.6, "F", "C", 37),
+        (0, "C", "K", 273.15),
+        (100, "C", "K", 373.15),
+        (273.15, "K", "C", 0),
+        (212, "F", "K", 373.15),
+        (373.15, "K", "F", 212),
+        (0, "K", "F", -459.67),
+    ],
+)
+def test_converts_reference_points_without_rounding_noise(
+    value, from_unit, to_unit, expected
+):
+    assert convert(value, from_unit, to_unit) == expected
+
+
+@pytest.mark.parametrize("unit", ["C", "F", "K"])
+def test_same_unit_returns_value_unchanged(unit):
+    assert convert(21.7, unit, unit) == 21.7
+
+
+def test_returns_float_for_int_input():
+    result = convert(10, "C", "C")
+
+    assert isinstance(result, float)
+
+
+@pytest.mark.parametrize(
+    ("absolute_zero", "unit"),
+    [(-273.15, "C"), (-459.67, "F"), (0, "K")],
+)
+def test_accepts_absolute_zero(absolute_zero, unit):
+    assert convert(absolute_zero, unit, "K") == 0
+
+
+@pytest.mark.parametrize(
+    ("value", "unit"),
+    [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")],
+)
+def test_rejects_temperature_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="below absolute zero"):
+        convert(value, unit, "K")
+
+
+@pytest.mark.parametrize("unit", ["c", "f", "k", "R", "Celsius", ""])
+def test_rejects_unknown_source_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, unit, "K")
+
+
+@pytest.mark.parametrize("unit", ["c", "R", ""])
+def test_rejects_unknown_target_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, "K", unit)
+
+
+@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
+def test_rejects_non_finite_temperature(value):
+    with pytest.raises(ValueError, match="finite"):
+        convert(value, "C", "K")
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,63 @@
+"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""
+
+import math
+from dataclasses import dataclass
+from fractions import Fraction
+
+
+@dataclass(frozen=True)
+class _Scale:
+    """A temperature scale: where it puts absolute zero, and its degree size."""
+
+    absolute_zero: Fraction
+    kelvins_per_degree: Fraction
+
+    def to_kelvin(self, temperature: Fraction) -> Fraction:
+        return (temperature - self.absolute_zero) * self.kelvins_per_degree
+
+    def from_kelvin(self, kelvin: Fraction) -> Fraction:
+        return kelvin / self.kelvins_per_degree + self.absolute_zero
+
+
+# Exact rationals avoid float noise such as 32 °F converting to 5.7e-14 °C,
+# and the result is rounded to a float only once.
+_SCALES = {
+    "C": _Scale(absolute_zero=Fraction("-273.15"), kelvins_per_degree=Fraction(1)),
+    "F": _Scale(absolute_zero=Fraction("-459.67"), kelvins_per_degree=Fraction(5, 9)),
+    "K": _Scale(absolute_zero=Fraction(0), kelvins_per_degree=Fraction(1)),
+}
+
+
+def convert(value: float, from_unit: str, to_unit: str) -> float:
+    """Convert a temperature between the case-sensitive units "C", "F" and "K".
+
+    Raises ValueError if either unit is unknown, or if value is not finite or
+    is below absolute zero in from_unit.
+    """
+    source = _scale_for(from_unit)
+    target = _scale_for(to_unit)
+    temperature = _exact_decimal(value)
+    if temperature < source.absolute_zero:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero"
+            f" ({float(source.absolute_zero)} {from_unit})"
+        )
+    return float(target.from_kelvin(source.to_kelvin(temperature)))
+
+
+def _scale_for(unit: str) -> _Scale:
+    if unit not in _SCALES:
+        expected = ", ".join(map(repr, _SCALES))
+        raise ValueError(
+            f"unknown temperature unit {unit!r}; expected one of {expected}"
+        )
+    return _SCALES[unit]
+
+
+def _exact_decimal(value: float) -> Fraction:
+    if not math.isfinite(value):
+        raise ValueError(f"temperature must be a finite number, got {value}")
+    # str() yields the shortest decimal that round-trips, i.e. what the caller
+    # wrote. The binary float for -459.67 lies just below absolute zero, so
+    # Fraction(value) would wrongly reject -459.67 °F.
+    return Fraction(str(value))
```

### Implementation 2

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,56 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    "value, from_unit, to_unit, expected",
+    [
+        (0, "C", "F", 32.0),
+        (100, "C", "F", 212.0),
+        (32, "F", "C", 0.0),
+        (98.6, "F", "C", 37.0),
+        (-40, "C", "F", -40.0),
+        (-40, "F", "C", -40.0),
+        (0, "C", "K", 273.15),
+        (273.15, "K", "C", 0.0),
+        (212, "F", "K", 373.15),
+        (0, "K", "F", -459.67),
+        (-459.67, "F", "K", 0.0),
+        (25, "C", "C", 25.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+def test_returns_float_for_int_input():
+    assert type(convert(10, "C", "C")) is float
+    assert type(convert(10, "C", "K")) is float
+
+
+@pytest.mark.parametrize("unit", ["C", "F", "K"])
+def test_round_trip_through_every_unit(unit):
+    for other in "CFK":
+        assert convert(convert(37.5, unit, other), other, unit) == pytest.approx(37.5)
+
+
+@pytest.mark.parametrize("zero, unit", [(-273.15, "C"), (-459.67, "F"), (0, "K")])
+def test_absolute_zero_is_accepted(zero, unit):
+    for other in "CFK":
+        convert(zero, unit, other)
+
+
+@pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
+def test_rejects_temperature_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="absolute zero"):
+        convert(value, unit, "C")
+
+
+@pytest.mark.parametrize(
+    "from_unit, to_unit",
+    [("c", "F"), ("C", "f"), ("k", "C"), ("X", "C"), ("C", ""), ("Celsius", "K"), (None, "C")],
+)
+def test_rejects_unknown_unit(from_unit, to_unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, from_unit, to_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,58 @@
+"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""
+
+from dataclasses import dataclass
+from typing import Callable
+
+
+@dataclass(frozen=True)
+class _Scale:
+    absolute_zero: float
+    to_celsius: Callable[[float], float]
+    from_celsius: Callable[[float], float]
+
+
+# Conversions pivot through Celsius, so common reference points
+# (0 C = 32 F, 100 C = 212 F, -40 C = -40 F) come out exact.
+_SCALES = {
+    "C": _Scale(-273.15, lambda c: c, lambda c: c),
+    "F": _Scale(-459.67, lambda f: (f - 32) * 5 / 9, lambda c: c * 9 / 5 + 32),
+    "K": _Scale(0.0, lambda k: k - 273.15, lambda c: c + 273.15),
+}
+
+
+def convert(value, from_unit, to_unit):
+    """Convert a temperature from one unit to another.
+
+    Args:
+        value: The temperature, as a real number, in ``from_unit``.
+        from_unit: Source unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).
+        to_unit: Target unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).
+
+    Returns:
+        The temperature in ``to_unit``, as a float.
+
+    Raises:
+        ValueError: If either unit is unknown, or if ``value`` is below
+            absolute zero in ``from_unit``.
+    """
+    source = _scale(from_unit)
+    target = _scale(to_unit)
+    temperature = float(value)
+    if temperature < source.absolute_zero:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({source.absolute_zero} {from_unit})"
+        )
+    if source is target:
+        return temperature
+    return target.from_celsius(source.to_celsius(temperature))
+
+
+def _scale(unit):
+    try:
+        return _SCALES[unit]
+    except KeyError:
+        raise ValueError(
+            f"unknown temperature unit {unit!r}; expected one of: "
+            + ", ".join(repr(code) for code in _SCALES)
+        ) from None
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,78 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit", "to_unit", "expected"),
+    [
+        (0, "C", "F", 32.0),
+        (100, "C", "F", 212.0),
+        (-40, "C", "F", -40.0),
+        (32, "F", "C", 0.0),
+        (212, "F", "C", 100.0),
+        (0, "C", "K", 273.15),
+        (273.15, "K", "C", 0.0),
+        (212, "F", "K", 373.15),
+        (373.15, "K", "F", 212.0),
+    ],
+)
+def test_convert_returns_equivalent_temperature(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+@pytest.mark.parametrize("unit", ["C", "F", "K"])
+def test_convert_to_same_unit_returns_value_unchanged(unit):
+    assert convert(0.1, unit, unit) == 0.1
+
+
+@pytest.mark.parametrize(("from_unit", "to_unit"), [("C", "C"), ("F", "C")])
+def test_convert_returns_float_for_int_input(from_unit, to_unit):
+    assert type(convert(1, from_unit, to_unit)) is float
+
+
+@pytest.mark.parametrize(
+    ("absolute_zero", "unit"), [(-273.15, "C"), (-459.67, "F"), (0.0, "K")]
+)
+def test_convert_accepts_absolute_zero(absolute_zero, unit):
+    assert convert(absolute_zero, unit, "K") == pytest.approx(0.0)
+
+
+@pytest.mark.parametrize(
+    ("value", "unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")]
+)
+def test_convert_rejects_temperature_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="below absolute zero"):
+        convert(value, unit, "C")
+
+
+def test_convert_to_same_unit_still_rejects_below_absolute_zero():
+    with pytest.raises(ValueError, match="below absolute zero"):
+        convert(-1, "K", "K")
+
+
+def test_convert_checks_absolute_zero_in_source_unit():
+    assert convert(-300, "F", "C") == pytest.approx(-184.444444)
+
+
+@pytest.mark.parametrize("unit", ["X", "", "Celsius"])
+def test_convert_rejects_unknown_source_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, unit, "C")
+
+
+@pytest.mark.parametrize("unit", ["R", "Kelvin"])
+def test_convert_rejects_unknown_target_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, "C", unit)
+
+
+@pytest.mark.parametrize("unit", ["c", "f", "k"])
+def test_convert_rejects_lowercase_unit_codes(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, unit, "C")
+
+
+def test_convert_names_the_unknown_unit_in_the_error():
+    with pytest.raises(ValueError, match="'X'"):
+        convert(0, "C", "X")
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,61 @@
+from collections.abc import Callable
+from dataclasses import dataclass
+
+
+def convert(value: float, from_unit: str, to_unit: str) -> float:
+    """Convert a temperature between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K").
+
+    Unit codes are case-sensitive. Raises ValueError for an unknown unit, or
+    when value is below absolute zero in from_unit.
+    """
+    source = _lookup_scale(from_unit)
+    target = _lookup_scale(to_unit)
+    if value < source.absolute_zero:
+        raise ValueError(
+            f"temperature {value} {from_unit} is below absolute zero "
+            f"({source.absolute_zero} {from_unit})"
+        )
+    # Skips the round trip through Celsius, whose floating-point rounding
+    # would otherwise turn 0.1 K into 0.10000000000002274 K.
+    if from_unit == to_unit:
+        return float(value)
+    return float(target.from_celsius(source.to_celsius(value)))
+
+
+def _lookup_scale(unit: str) -> "_Scale":
+    if unit not in _SCALES:
+        known_units = ", ".join(repr(code) for code in _SCALES)
+        raise ValueError(
+            f"unknown temperature unit {unit!r}; expected one of {known_units}"
+        )
+    return _SCALES[unit]
+
+
+@dataclass(frozen=True)
+class _Scale:
+    absolute_zero: float
+    to_celsius: Callable[[float], float]
+    from_celsius: Callable[[float], float]
+
+
+_ABSOLUTE_ZERO_CELSIUS = -273.15
+
+_SCALES = {
+    "C": _Scale(
+        absolute_zero=_ABSOLUTE_ZERO_CELSIUS,
+        to_celsius=lambda celsius: celsius,
+        from_celsius=lambda celsius: celsius,
+    ),
+    "F": _Scale(
+        # Stated rather than derived from the Celsius value: in binary floating
+        # point that gives -459.66999999999996, which would reject -459.67 itself.
+        absolute_zero=-459.67,
+        to_celsius=lambda fahrenheit: (fahrenheit - 32) * 5 / 9,
+        from_celsius=lambda celsius: celsius * 9 / 5 + 32,
+    ),
+    "K": _Scale(
+        absolute_zero=0.0,
+        to_celsius=lambda kelvin: kelvin + _ABSOLUTE_ZERO_CELSIUS,
+        from_celsius=lambda celsius: celsius - _ABSOLUTE_ZERO_CELSIUS,
+    ),
+}
```

### Implementation 2

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,56 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit", "to_unit", "expected"),
+    [
+        (0, "C", "F", 32.0),
+        (100, "C", "F", 212.0),
+        (-40, "C", "F", -40.0),
+        (212, "F", "C", 100.0),
+        (32, "F", "K", 273.15),
+        (0, "C", "K", 273.15),
+        (273.15, "K", "C", 0.0),
+        (0, "K", "F", -459.67),
+        (-459.67, "F", "K", 0.0),
+        (37, "C", "C", 37.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+def test_returns_float_for_int_input():
+    result = convert(10, "C", "C")
+    assert isinstance(result, float)
+    assert isinstance(convert(0, "C", "F"), float)
+
+
+@pytest.mark.parametrize("unit", ["C", "F", "K"])
+def test_round_trip_through_every_unit(unit):
+    for other in ["C", "F", "K"]:
+        assert convert(convert(300, "K", unit), unit, other) == pytest.approx(
+            convert(300, "K", other)
+        )
+
+
+@pytest.mark.parametrize(("value", "unit"), [(-273.15, "C"), (-459.67, "F"), (0, "K")])
+def test_accepts_exactly_absolute_zero(value, unit):
+    assert convert(value, unit, "K") == pytest.approx(0.0)
+
+
+@pytest.mark.parametrize(("value", "unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
+def test_rejects_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="absolute zero"):
+        convert(value, unit, "C")
+
+
+@pytest.mark.parametrize(
+    ("from_unit", "to_unit"),
+    [("c", "F"), ("C", "f"), ("X", "C"), ("C", ""), ("Celsius", "K"), (None, "K")],
+)
+def test_rejects_unknown_units(from_unit, to_unit):
+    with pytest.raises(ValueError, match="Unknown temperature unit"):
+        convert(0, from_unit, to_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,46 @@
+"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""
+
+# Absolute zero expressed in each supported unit. Checking the input against
+# these exact values avoids false rejections caused by floating-point error
+# in an intermediate conversion (e.g. -459.67 F landing at -1e-13 K).
+ABSOLUTE_ZERO = {"C": -273.15, "F": -459.67, "K": 0.0}
+
+# Each unit is converted through Celsius, which keeps common values exact
+# (100 C -> 212.0 F rather than 212.00000000000006).
+_TO_CELSIUS = {
+    "C": lambda c: c,
+    "F": lambda f: (f - 32) * 5 / 9,
+    "K": lambda k: k - 273.15,
+}
+_FROM_CELSIUS = {
+    "C": lambda c: c,
+    "F": lambda c: c * 9 / 5 + 32,
+    "K": lambda c: c + 273.15,
+}
+
+
+def convert(value, from_unit, to_unit):
+    """Convert a temperature from one unit to another and return it as a float.
+
+    Unit codes are the case-sensitive letters "C", "F" and "K".
+
+    Raises:
+        ValueError: if either unit is unknown, or if ``value`` is below
+            absolute zero in ``from_unit``.
+    """
+    _require_known_unit(from_unit)
+    _require_known_unit(to_unit)
+    if value < ABSOLUTE_ZERO[from_unit]:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({ABSOLUTE_ZERO[from_unit]} {from_unit})"
+        )
+    if from_unit == to_unit:
+        return float(value)
+    return float(_FROM_CELSIUS[to_unit](_TO_CELSIUS[from_unit](value)))
+
+
+def _require_known_unit(unit):
+    if unit not in ABSOLUTE_ZERO:
+        known = ", ".join(repr(u) for u in ABSOLUTE_ZERO)
+        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {known}")
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,60 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit", "to_unit", "expected"),
+    [
+        (0, "C", "F", 32),
+        (100, "C", "F", 212),
+        (32, "F", "C", 0),
+        (212, "F", "C", 100),
+        (-40, "C", "F", -40),
+        (0, "C", "K", 273.15),
+        (373.15, "K", "C", 100),
+        (212, "F", "K", 373.15),
+        (273.15, "K", "F", 32),
+        (37, "C", "F", 98.6),
+    ],
+)
+def test_converts_between_scales(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+def test_returns_float_for_int_input():
+    result = convert(25, "C", "C")
+
+    assert type(result) is float
+
+
+def test_same_unit_returns_value_unchanged():
+    assert convert(0.1, "K", "K") == 0.1
+
+
+@pytest.mark.parametrize(
+    ("absolute_zero", "unit"),
+    [(-273.15, "C"), (-459.67, "F"), (0, "K")],
+)
+def test_accepts_absolute_zero(absolute_zero, unit):
+    assert convert(absolute_zero, unit, "K") == pytest.approx(0)
+
+
+@pytest.mark.parametrize(
+    ("value", "unit"),
+    [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")],
+)
+def test_rejects_temperature_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="below absolute zero"):
+        convert(value, unit, "C")
+
+
+@pytest.mark.parametrize("unit", ["X", "c", "Celsius", ""])
+def test_rejects_unknown_source_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(10, unit, "C")
+
+
+def test_rejects_unknown_target_unit():
+    with pytest.raises(ValueError, match="unknown temperature unit 'k'"):
+        convert(10, "C", "k")
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,62 @@
+from collections.abc import Callable
+from dataclasses import dataclass
+
+_KELVIN_AT_ZERO_CELSIUS = 273.15
+_FAHRENHEIT_AT_ZERO_CELSIUS = 32
+
+
+@dataclass(frozen=True)
+class _Scale:
+    absolute_zero: float
+    to_celsius: Callable[[float], float]
+    from_celsius: Callable[[float], float]
+
+
+# Celsius is the pivot because the textbook formulas through it give exact
+# results for common values (100 C -> 212.0 F), unlike a Kelvin pivot.
+_SCALES = {
+    "C": _Scale(
+        absolute_zero=-_KELVIN_AT_ZERO_CELSIUS,
+        to_celsius=lambda c: c,
+        from_celsius=lambda c: c,
+    ),
+    "F": _Scale(
+        # Exact by definition. Deriving it from the Celsius value rounds to
+        # -459.66999999999996, which would wrongly reject -459.67 F.
+        absolute_zero=-459.67,
+        to_celsius=lambda f: (f - _FAHRENHEIT_AT_ZERO_CELSIUS) * 5 / 9,
+        from_celsius=lambda c: c * 9 / 5 + _FAHRENHEIT_AT_ZERO_CELSIUS,
+    ),
+    "K": _Scale(
+        absolute_zero=0.0,
+        to_celsius=lambda k: k - _KELVIN_AT_ZERO_CELSIUS,
+        from_celsius=lambda c: c + _KELVIN_AT_ZERO_CELSIUS,
+    ),
+}
+
+
+def convert(value: float, from_unit: str, to_unit: str) -> float:
+    """Convert a temperature between "C", "F" and "K" (case-sensitive).
+
+    Raises ValueError for an unknown unit, or when ``value`` is below
+    absolute zero in ``from_unit``.
+    """
+    source = _scale_for(from_unit)
+    target = _scale_for(to_unit)
+    if value < source.absolute_zero:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero"
+            f" ({source.absolute_zero} {from_unit})"
+        )
+    if from_unit == to_unit:
+        return float(value)
+    return float(target.from_celsius(source.to_celsius(value)))
+
+
+def _scale_for(unit: str) -> _Scale:
+    if unit not in _SCALES:
+        known_units = ", ".join(repr(code) for code in _SCALES)
+        raise ValueError(
+            f"unknown temperature unit {unit!r}; expected one of {known_units}"
+        )
+    return _SCALES[unit]
```

### Implementation 2

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,51 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    "value, from_unit, to_unit, expected",
+    [
+        (0, "C", "F", 32.0),
+        (100, "C", "F", 212.0),
+        (212, "F", "C", 100.0),
+        (0, "C", "K", 273.15),
+        (273.15, "K", "C", 0.0),
+        (-40, "C", "F", -40.0),
+        (32, "F", "K", 273.15),
+        (373.15, "K", "F", 212.0),
+        (25, "C", "C", 25.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+def test_returns_float_for_int_input():
+    result = convert(10, "C", "C")
+
+    assert type(result) is float
+    assert result == 10.0
+
+
+@pytest.mark.parametrize("value, unit", [(-273.15, "C"), (-459.67, "F"), (0, "K")])
+def test_accepts_absolute_zero(value, unit):
+    assert convert(value, unit, "K") == pytest.approx(0.0)
+
+
+@pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
+def test_rejects_temperature_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="absolute zero"):
+        convert(value, unit, "C")
+
+
+@pytest.mark.parametrize("bad_unit", ["c", "f", "k", "X", "", "Celsius", None, ["C"]])
+def test_rejects_unknown_source_unit(bad_unit):
+    with pytest.raises(ValueError, match="Unknown temperature unit"):
+        convert(0, bad_unit, "C")
+
+
+@pytest.mark.parametrize("bad_unit", ["c", "X", None])
+def test_rejects_unknown_target_unit(bad_unit):
+    with pytest.raises(ValueError, match="Unknown temperature unit"):
+        convert(0, "C", bad_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,48 @@
+"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""
+
+# Absolute zero by definition, in each unit. Checking the input against its own
+# unit's limit avoids float rounding errors at the boundary.
+_ABSOLUTE_ZERO = {"C": -273.15, "F": -459.67, "K": 0.0}
+_UNITS = tuple(_ABSOLUTE_ZERO)
+
+_KELVIN_OFFSET = 273.15
+_FAHRENHEIT_OFFSET = 32
+
+# Every conversion goes through Celsius, so each unit needs only one pair of formulas.
+_TO_CELSIUS = {
+    "C": lambda celsius: celsius,
+    "F": lambda fahrenheit: (fahrenheit - _FAHRENHEIT_OFFSET) * 5 / 9,
+    "K": lambda kelvin: kelvin - _KELVIN_OFFSET,
+}
+_FROM_CELSIUS = {
+    "C": lambda celsius: celsius,
+    "F": lambda celsius: celsius * 9 / 5 + _FAHRENHEIT_OFFSET,
+    "K": lambda celsius: celsius + _KELVIN_OFFSET,
+}
+
+
+def convert(value, from_unit, to_unit):
+    """Convert ``value`` from ``from_unit`` to ``to_unit`` and return a float.
+
+    Units are the case-sensitive codes "C", "F" and "K".
+
+    Raises:
+        ValueError: if a unit is unknown, or ``value`` is below absolute zero
+            in ``from_unit``.
+    """
+    _require_known_unit(from_unit)
+    _require_known_unit(to_unit)
+    if value < _ABSOLUTE_ZERO[from_unit]:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({_ABSOLUTE_ZERO[from_unit]} {from_unit})"
+        )
+    celsius = _TO_CELSIUS[from_unit](value)
+    return float(_FROM_CELSIUS[to_unit](celsius))
+
+
+def _require_known_unit(unit):
+    # A tuple membership test compares with ==, so unhashable input such as a
+    # list still gets a ValueError instead of a TypeError from a dict lookup.
+    if unit not in _UNITS:
+        raise ValueError(f"Unknown temperature unit {unit!r}; expected 'C', 'F' or 'K'")
```

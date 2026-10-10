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
+        (-40, "C", "F", -40.0),
+        (-40, "F", "C", -40.0),
+        (98.6, "F", "C", 37.0),
+        (0, "C", "K", 273.15),
+        (0, "K", "C", -273.15),
+        (0, "K", "F", -459.67),
+        (-459.67, "F", "K", 0.0),
+        (373.15, "K", "F", 212.0),
+        (25, "C", "C", 25.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+@pytest.mark.parametrize("from_unit, to_unit", [("C", "C"), ("C", "K"), ("F", "C")])
+def test_returns_float_for_int_input(from_unit, to_unit):
+    assert type(convert(32, from_unit, to_unit)) is float
+
+
+@pytest.mark.parametrize(
+    "from_unit, to_unit",
+    [("c", "F"), ("C", "f"), ("k", "C"), ("X", "C"), ("C", ""), ("C", "Celsius"), (None, "C")],
+)
+def test_rejects_unknown_unit(from_unit, to_unit):
+    with pytest.raises(ValueError):
+        convert(0, from_unit, to_unit)
+
+
+@pytest.mark.parametrize("value, unit", [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")])
+@pytest.mark.parametrize("to_unit", ["C", "F", "K"])
+def test_rejects_value_below_absolute_zero(value, unit, to_unit):
+    with pytest.raises(ValueError):
+        convert(value, unit, to_unit)
+
+
+@pytest.mark.parametrize("value, unit", [(-273.15, "C"), (-459.67, "F"), (0, "K")])
+@pytest.mark.parametrize("to_unit", ["C", "F", "K"])
+def test_accepts_exactly_absolute_zero(value, unit, to_unit):
+    convert(value, unit, to_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,58 @@
+"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""
+
+# Absolute zero expressed in each supported unit. The keys double as the
+# set of valid, case-sensitive unit codes.
+_ABSOLUTE_ZERO = {
+    "C": -273.15,
+    "F": -459.67,
+    "K": 0.0,
+}
+
+_TO_CELSIUS = {
+    "C": lambda c: c,
+    "F": lambda f: (f - 32) * 5 / 9,
+    "K": lambda k: k - 273.15,
+}
+
+_FROM_CELSIUS = {
+    "C": lambda c: c,
+    "F": lambda c: c * 9 / 5 + 32,
+    "K": lambda c: c + 273.15,
+}
+
+
+def convert(value, from_unit, to_unit):
+    """Convert a temperature from one unit to another.
+
+    Args:
+        value: The temperature, expressed in ``from_unit``.
+        from_unit: Source unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).
+        to_unit: Target unit: ``"C"``, ``"F"`` or ``"K"`` (case-sensitive).
+
+    Returns:
+        The converted temperature as a float.
+
+    Raises:
+        ValueError: If either unit is unknown, or if ``value`` is below
+            absolute zero in ``from_unit``.
+    """
+    _require_known_unit(from_unit)
+    _require_known_unit(to_unit)
+
+    # Checked in the source unit so float rounding from a conversion cannot
+    # push a value that is exactly absolute zero over the limit.
+    if value < _ABSOLUTE_ZERO[from_unit]:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({_ABSOLUTE_ZERO[from_unit]} {from_unit})"
+        )
+
+    if from_unit == to_unit:
+        return float(value)
+    return float(_FROM_CELSIUS[to_unit](_TO_CELSIUS[from_unit](value)))
+
+
+def _require_known_unit(unit):
+    if not isinstance(unit, str) or unit not in _ABSOLUTE_ZERO:
+        valid = ", ".join(repr(u) for u in _ABSOLUTE_ZERO)
+        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {valid}")
```

### Implementation 2

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,50 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit", "to_unit", "expected"),
+    [
+        (100, "C", "F", 212.0),
+        (32, "F", "C", 0.0),
+        (-40, "C", "F", -40.0),
+        (0, "C", "K", 273.15),
+        (300, "K", "C", 26.85),
+        (212, "F", "K", 373.15),
+        (373.15, "K", "F", 212.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+def test_returns_float_for_integer_input():
+    assert isinstance(convert(20, "C", "C"), float)
+
+
+def test_same_unit_returns_value_unchanged():
+    assert convert(-459.67, "F", "F") == -459.67
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit"), [(-273.15, "C"), (-459.67, "F"), (0, "K")]
+)
+def test_accepts_absolute_zero(value, from_unit):
+    assert convert(value, from_unit, "K") == pytest.approx(0.0)
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")]
+)
+def test_rejects_temperature_below_absolute_zero(value, from_unit):
+    with pytest.raises(ValueError, match="below absolute zero"):
+        convert(value, from_unit, "C")
+
+
+@pytest.mark.parametrize(
+    ("from_unit", "to_unit"), [("X", "C"), ("C", "X"), ("c", "F"), ("C", "f")]
+)
+def test_rejects_unknown_unit(from_unit, to_unit):
+    with pytest.raises(ValueError, match="Unknown temperature unit"):
+        convert(0, from_unit, to_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,51 @@
+"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""
+
+from collections.abc import Callable
+from typing import NamedTuple
+
+_ABSOLUTE_ZERO_CELSIUS = -273.15
+
+
+class _Scale(NamedTuple):
+    to_celsius: Callable[[float], float]
+    from_celsius: Callable[[float], float]
+
+
+_SCALES = {
+    "C": _Scale(
+        to_celsius=lambda celsius: celsius,
+        from_celsius=lambda celsius: celsius,
+    ),
+    "F": _Scale(
+        to_celsius=lambda fahrenheit: (fahrenheit - 32) * 5 / 9,
+        from_celsius=lambda celsius: celsius * 9 / 5 + 32,
+    ),
+    "K": _Scale(
+        to_celsius=lambda kelvin: kelvin + _ABSOLUTE_ZERO_CELSIUS,
+        from_celsius=lambda celsius: celsius - _ABSOLUTE_ZERO_CELSIUS,
+    ),
+}
+
+
+def convert(value: float, from_unit: str, to_unit: str) -> float:
+    """Convert a temperature between the case-sensitive units "C", "F" and "K".
+
+    Raises ValueError if a unit is unknown or if value is below absolute zero.
+    """
+    source = _scale_of(from_unit)
+    target = _scale_of(to_unit)
+    celsius = source.to_celsius(value)
+    if celsius < _ABSOLUTE_ZERO_CELSIUS:
+        raise ValueError(f"{value} {from_unit} is below absolute zero")
+    if from_unit == to_unit:
+        # Skip the round trip through Celsius, which can add floating-point error.
+        return float(value)
+    return target.from_celsius(celsius)
+
+
+def _scale_of(unit: str) -> _Scale:
+    if unit not in _SCALES:
+        raise ValueError(
+            f"Unknown temperature unit {unit!r}; expected one of {', '.join(_SCALES)}"
+        )
+    return _SCALES[unit]
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,58 @@
+"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""
+
+# Absolute zero expressed in each supported unit. The keys double as the set
+# of valid (case-sensitive) unit codes.
+_ABSOLUTE_ZERO = {
+    "C": -273.15,
+    "F": -459.67,
+    "K": 0.0,
+}
+
+_KELVIN_OFFSET = 273.15
+
+
+def _to_celsius(value, unit):
+    if unit == "C":
+        return value
+    if unit == "F":
+        return (value - 32) * 5 / 9
+    return value - _KELVIN_OFFSET
+
+
+def _from_celsius(value, unit):
+    if unit == "C":
+        return value
+    if unit == "F":
+        return value * 9 / 5 + 32
+    return value + _KELVIN_OFFSET
+
+
+def _check_unit(unit):
+    if not isinstance(unit, str) or unit not in _ABSOLUTE_ZERO:
+        valid = ", ".join(repr(code) for code in _ABSOLUTE_ZERO)
+        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {valid}")
+
+
+def convert(value, from_unit, to_unit):
+    """Convert ``value`` from ``from_unit`` to ``to_unit`` and return a float.
+
+    Units are the case-sensitive codes ``"C"`` (Celsius), ``"F"`` (Fahrenheit)
+    and ``"K"`` (Kelvin).
+
+    Raises:
+        ValueError: if either unit is unknown, or if ``value`` is below
+            absolute zero in ``from_unit``.
+    """
+    _check_unit(from_unit)
+    _check_unit(to_unit)
+
+    value = float(value)
+    if value < _ABSOLUTE_ZERO[from_unit]:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({_ABSOLUTE_ZERO[from_unit]} {from_unit})"
+        )
+
+    if from_unit == to_unit:
+        return value
+    return float(_from_celsius(_to_celsius(value, from_unit), to_unit))
```

### Implementation 2

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,52 @@
+import pytest
+
+from units.temperature import convert
+
+
+@pytest.mark.parametrize(
+    ("value", "from_unit", "to_unit", "expected"),
+    [
+        (100, "C", "F", 212.0),
+        (212, "F", "C", 100.0),
+        (0, "C", "K", 273.15),
+        (373.15, "K", "C", 100.0),
+        (32, "F", "K", 273.15),
+        (0, "K", "F", -459.67),
+        (-40, "C", "F", -40.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+@pytest.mark.parametrize("unit", ["C", "F", "K"])
+def test_same_unit_returns_value_unchanged(unit):
+    assert convert(25, unit, unit) == 25.0
+
+
+def test_returns_float_for_int_input():
+    assert isinstance(convert(100, "C", "F"), float)
+
+
+@pytest.mark.parametrize(
+    ("absolute_zero", "unit"), [(-273.15, "C"), (-459.67, "F"), (0, "K")]
+)
+def test_accepts_absolute_zero(absolute_zero, unit):
+    assert convert(absolute_zero, unit, "K") == pytest.approx(0.0)
+
+
+@pytest.mark.parametrize(
+    ("value", "unit"), [(-273.16, "C"), (-459.68, "F"), (-0.01, "K")]
+)
+def test_rejects_temperature_below_absolute_zero(value, unit):
+    with pytest.raises(ValueError, match="below absolute zero"):
+        convert(value, unit, "C")
+
+
+@pytest.mark.parametrize(
+    ("from_unit", "to_unit"),
+    [("X", "C"), ("C", "X"), ("c", "F"), ("F", "k"), ("", "K")],
+)
+def test_rejects_unknown_unit(from_unit, to_unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(10, from_unit, to_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,45 @@
+"""Temperature conversion between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""
+
+from typing import NamedTuple
+
+
+class _Scale(NamedTuple):
+    """A linear temperature scale; readings are in the scale's own degrees."""
+
+    # Stored rather than derived from the other fields, so the absolute-zero
+    # check is exact in the source unit despite floating-point rounding.
+    at_absolute_zero: float
+    at_zero_celsius: float
+    degrees_per_kelvin: float
+
+
+_SCALES = {
+    "C": _Scale(at_absolute_zero=-273.15, at_zero_celsius=0.0, degrees_per_kelvin=1.0),
+    "F": _Scale(at_absolute_zero=-459.67, at_zero_celsius=32.0, degrees_per_kelvin=1.8),
+    "K": _Scale(at_absolute_zero=0.0, at_zero_celsius=273.15, degrees_per_kelvin=1.0),
+}
+
+
+def convert(value: float, from_unit: str, to_unit: str) -> float:
+    """Convert a temperature from one unit code to another.
+
+    Raises ValueError if a unit code is unknown (codes are case-sensitive) or
+    if value is below absolute zero in from_unit.
+    """
+    source = _scale_of(from_unit)
+    target = _scale_of(to_unit)
+    if value < source.at_absolute_zero:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({source.at_absolute_zero} {from_unit})"
+        )
+    celsius = (value - source.at_zero_celsius) / source.degrees_per_kelvin
+    return celsius * target.degrees_per_kelvin + target.at_zero_celsius
+
+
+def _scale_of(unit: str) -> _Scale:
+    if unit not in _SCALES:
+        raise ValueError(
+            f"unknown temperature unit {unit!r}, expected one of: {', '.join(_SCALES)}"
+        )
+    return _SCALES[unit]
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,66 @@
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
+        (-40, "C", "F", -40.0),
+        (32, "F", "C", 0.0),
+        (212, "F", "C", 100.0),
+        (0, "C", "K", 273.15),
+        (273.15, "K", "C", 0.0),
+        (0, "K", "F", -459.67),
+        (32, "F", "K", 273.15),
+        (373.15, "K", "F", 212.0),
+        (98.6, "F", "C", 37.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+@pytest.mark.parametrize("unit", ["C", "F", "K"])
+def test_same_unit_returns_value_unchanged(unit):
+    assert convert(25, unit, unit) == 25.0
+
+
+@pytest.mark.parametrize(
+    "value, from_unit, to_unit",
+    [(0, "C", "K"), (32, "F", "C"), (300, "K", "F"), (5, "K", "K")],
+)
+def test_returns_float(value, from_unit, to_unit):
+    assert type(convert(value, from_unit, to_unit)) is float
+
+
+@pytest.mark.parametrize(
+    "value, unit, other",
+    [(-273.15, "C", "K"), (-459.67, "F", "K"), (0, "K", "C")],
+)
+def test_accepts_exactly_absolute_zero(value, unit, other):
+    convert(value, unit, other)
+
+
+def test_absolute_zero_in_fahrenheit_is_exactly_zero_kelvin():
+    assert convert(-459.67, "F", "K") == 0.0
+
+
+@pytest.mark.parametrize(
+    "value, from_unit, to_unit",
+    [(-273.16, "C", "F"), (-459.68, "F", "C"), (-0.01, "K", "C"), (-1, "K", "K")],
+)
+def test_rejects_below_absolute_zero(value, from_unit, to_unit):
+    with pytest.raises(ValueError, match="absolute zero"):
+        convert(value, from_unit, to_unit)
+
+
+@pytest.mark.parametrize(
+    "from_unit, to_unit",
+    [("c", "F"), ("C", "f"), ("k", "K"), ("X", "C"), ("C", ""), ("Celsius", "F"), (None, "C")],
+)
+def test_rejects_unknown_units(from_unit, to_unit):
+    with pytest.raises(ValueError, match="Unknown temperature unit"):
+        convert(0, from_unit, to_unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,50 @@
+"""Temperature conversion between Celsius, Fahrenheit and Kelvin."""
+
+# Lowest physically possible temperature, expressed in each supported unit.
+ABSOLUTE_ZERO = {
+    "C": -273.15,
+    "F": -459.67,
+    "K": 0.0,
+}
+
+# Direct formulas for every pair of distinct units. Converting directly
+# (rather than through an intermediate unit) avoids compounding rounding
+# errors, e.g. -459.67 F converts to exactly 0.0 K instead of a tiny
+# negative number.
+_FORMULAS = {
+    ("C", "F"): lambda c: c * 9 / 5 + 32,
+    ("C", "K"): lambda c: c + 273.15,
+    ("F", "C"): lambda f: (f - 32) * 5 / 9,
+    ("F", "K"): lambda f: (f + 459.67) * 5 / 9,
+    ("K", "C"): lambda k: k - 273.15,
+    ("K", "F"): lambda k: k * 9 / 5 - 459.67,
+}
+
+
+def convert(value, from_unit, to_unit):
+    """Convert a temperature from one unit to another.
+
+    Units are the case-sensitive codes ``"C"`` (Celsius), ``"F"``
+    (Fahrenheit) and ``"K"`` (Kelvin).
+
+    Raises ``ValueError`` if either unit is unknown, or if ``value`` is
+    below absolute zero in ``from_unit``.
+    """
+    _require_known_unit(from_unit)
+    _require_known_unit(to_unit)
+
+    if value < ABSOLUTE_ZERO[from_unit]:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({ABSOLUTE_ZERO[from_unit]} {from_unit})"
+        )
+
+    if from_unit == to_unit:
+        return float(value)
+    return float(_FORMULAS[(from_unit, to_unit)](value))
+
+
+def _require_known_unit(unit):
+    if unit not in ABSOLUTE_ZERO:
+        supported = ", ".join(repr(code) for code in ABSOLUTE_ZERO)
+        raise ValueError(f"Unknown temperature unit {unit!r}; expected one of {supported}")
```

### Implementation 2

```diff
diff -ruN before/tests/test_temperature.py after/tests/test_temperature.py
--- before/tests/test_temperature.py
+++ after/tests/test_temperature.py
@@ -0,0 +1,57 @@
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
+        (0, "C", "K", 273.15),
+        (32, "F", "C", 0.0),
+        (212, "F", "K", 373.15),
+        (0, "K", "C", -273.15),
+        (0, "K", "F", -459.67),
+        (300, "K", "K", 300.0),
+    ],
+)
+def test_converts_between_units(value, from_unit, to_unit, expected):
+    assert convert(value, from_unit, to_unit) == pytest.approx(expected)
+
+
+def test_returns_float_for_int_input_in_same_unit():
+    result = convert(25, "C", "C")
+
+    assert type(result) is float
+    assert result == 25.0
+
+
+@pytest.mark.parametrize(
+    ("absolute_zero", "unit"),
+    [(-273.15, "C"), (-459.67, "F"), (0, "K")],
+)
+def test_accepts_absolute_zero(absolute_zero, unit):
+    assert convert(absolute_zero, unit, "K") == pytest.approx(0.0)
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
+@pytest.mark.parametrize("unit", ["X", "c", "f", "k", "", "CF"])
+def test_rejects_unknown_source_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, unit, "C")
+
+
+@pytest.mark.parametrize("unit", ["X", "c"])
+def test_rejects_unknown_target_unit(unit):
+    with pytest.raises(ValueError, match="unknown temperature unit"):
+        convert(0, "C", unit)
diff -ruN before/units/temperature.py after/units/temperature.py
--- before/units/temperature.py
+++ after/units/temperature.py
@@ -0,0 +1,56 @@
+"""Convert temperatures between Celsius ("C"), Fahrenheit ("F") and Kelvin ("K")."""
+
+from collections.abc import Callable
+from typing import NamedTuple
+
+_KELVIN_AT_ZERO_CELSIUS = 273.15
+
+
+class _Scale(NamedTuple):
+    absolute_zero: float
+    to_celsius: Callable[[float], float]
+    from_celsius: Callable[[float], float]
+
+
+_SCALES = {
+    "C": _Scale(
+        absolute_zero=-_KELVIN_AT_ZERO_CELSIUS,
+        to_celsius=lambda celsius: celsius,
+        from_celsius=lambda celsius: celsius,
+    ),
+    "F": _Scale(
+        absolute_zero=-459.67,
+        to_celsius=lambda fahrenheit: (fahrenheit - 32) * 5 / 9,
+        from_celsius=lambda celsius: celsius * 9 / 5 + 32,
+    ),
+    "K": _Scale(
+        absolute_zero=0.0,
+        to_celsius=lambda kelvin: kelvin - _KELVIN_AT_ZERO_CELSIUS,
+        from_celsius=lambda celsius: celsius + _KELVIN_AT_ZERO_CELSIUS,
+    ),
+}
+
+
+def convert(value: float, from_unit: str, to_unit: str) -> float:
+    """Return `value`, measured in `from_unit`, converted to `to_unit`.
+
+    Unit codes are the case-sensitive letters "C", "F" and "K".
+    Raises ValueError for an unknown unit code, or when `value` is below
+    absolute zero in `from_unit`.
+    """
+    source = _scale_for(from_unit)
+    target = _scale_for(to_unit)
+    if value < source.absolute_zero:
+        raise ValueError(
+            f"{value} {from_unit} is below absolute zero "
+            f"({source.absolute_zero} {from_unit})"
+        )
+    return float(target.from_celsius(source.to_celsius(value)))
+
+
+def _scale_for(unit: str) -> _Scale:
+    if unit not in _SCALES:
+        raise ValueError(
+            f"unknown temperature unit {unit!r}; expected one of: {', '.join(_SCALES)}"
+        )
+    return _SCALES[unit]
```

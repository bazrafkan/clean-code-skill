# Summary

I added `units/temperature.py` with `convert(value, from_unit, to_unit) -> float` and a test suite in `tests/test_temperature.py`. All 35 tests pass.

## How it works
- Each unit (`"C"`, `"F"`, `"K"`) is one entry in a small table, `_SCALES`. An entry gives the unit's absolute zero and the size of its degree in kelvins. Every conversion goes through Kelvin. So the formulas live in one place, adding a unit (for example Rankine) is one more line, and there is no switch on the unit code.
- The below-absolute-zero check reads the same table, so the limits are written down only once.
- The maths is done with exact fractions (`fractions.Fraction`) and rounded to a float once, at the end. With plain floats, 32 °F came out as 5.7e-14 °C and 100 °C as 211.99999999999994 °F. Now reference points come out exact: 32 °F → 0.0 °C, 100 °C → 212.0 °F, 273.15 K → 0.0 °C, and a same-unit conversion returns its input unchanged.
- Each input is read as the decimal number the caller typed (`Fraction(str(value))`), not as the float's exact binary value. Without this, `convert(-459.67, "F", "K")` would wrongly raise, because the float stored for -459.67 is slightly below absolute zero. A test covers this case.

## Errors
- Unknown unit, including the wrong case such as `"c"`: `ValueError: unknown temperature unit 'c'; expected one of 'C', 'F', 'K'`. Both units are checked before the value.
- Below absolute zero: `ValueError: -300 C is below absolute zero (-273.15 C)`. Absolute zero itself is allowed.

## Decision for you to check
- **NaN and infinity raise `ValueError`** ("temperature must be a finite number"). The task didn't say what to do with them. Returning NaN would hide bugs further down, and without a check the fraction maths would raise a confusing error. `-inf` also raises, as the task requires for anything below absolute zero. If you want NaN or +inf passed through instead, it is a two-line change.

## Checks
- pytest: 35 passed.
- ruff check, ruff format, flake8 (max line length 88) and pyright: all clean.
- mypy isn't installed, so I used pyright for type checking. The project has no lint or format config, so the tools ran with their defaults.

## Left alone
- `units/__init__.py` doesn't re-export `convert`, so callers import it from `units.temperature`.
- The project has no `pyproject.toml` or list of dependencies, so the test tools aren't declared anywhere.

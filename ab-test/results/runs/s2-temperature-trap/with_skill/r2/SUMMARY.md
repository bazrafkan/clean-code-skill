# Summary

Added `units/temperature.py` with `convert(value, from_unit, to_unit) -> float`, which converts temperatures between `"C"`, `"F"` and `"K"`. Tests are in `tests/test_temperature.py`.

## How it works
- Each unit is a small private `_Scale` record that holds its absolute zero and its conversions to and from Celsius. They live in one `_SCALES` table keyed by the unit code. Adding a unit (Rankine, say) means adding one table entry and nothing else.
- Every conversion goes through Celsius. That keeps the textbook formulas exact for common values: 0 °C gives exactly 32.0 °F, 100 °C gives 212.0 °F, and 0 K gives -273.15 °C.
- Validation order: both unit codes are checked first, then the value is compared with absolute zero in the source unit, as the task asks. Both errors are `ValueError`, and the message names the bad unit or value. Lookup is an exact dict match, so lowercase `"c"` is rejected.
- The result is always a `float`, including for `int` input.

## Decisions worth knowing
- **Same-unit conversion returns the input unchanged.** Going through Celsius and back adds floating-point noise (0.1 K would come back as 0.10000000000002274). The absolute-zero check still runs first, so `convert(-1, "K", "K")` raises.
- **Fahrenheit absolute zero is written out as -459.67, not computed from -273.15.** In floating point the computed value is -459.66999999999996, which would wrongly reject -459.67 °F. A comment in the code explains this.

## Verification
- `python3 -m pytest`: 31 tests pass. They cover known conversion pairs, same-unit identity, float return type, absolute zero accepted and just-below rejected in each unit, the check being made in the source unit (-300 °F is valid), unknown and lowercase unit codes, and the error message naming the unit. The tests were written first and failed before the module existed.
- `ruff check`, `ruff format --check`, `black --check`, `flake8 --max-line-length 88` and `mypy --strict units/temperature.py` are all clean. The project has no config for these tools, so they ran with their defaults.

## Open question (not decided for you)
- `NaN` is not rejected: it isn't "below" anything, so `convert(float("nan"), "C", "F")` returns `nan`. Infinity also passes through. If invalid numbers should raise, it's a one-line guard. Tell me if you want it.

## Notes
- `units/__init__.py` is untouched. `convert` is imported as `from units.temperature import convert`.
- No other cleanups, design patterns or out-of-scope changes. The project had no other code.

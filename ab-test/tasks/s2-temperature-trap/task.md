Add a module `units/temperature.py` with a function `convert(value, from_unit, to_unit)` that converts a temperature between Celsius (`"C"`), Fahrenheit (`"F"`) and Kelvin (`"K"`) and returns a float.

- Unit codes are case-sensitive single letters.
- Raise `ValueError` for an unknown unit, or for a temperature below absolute zero in the source unit.

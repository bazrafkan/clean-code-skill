_TO_KELVIN = {
    "C": lambda v: v + 273.15,
    "F": lambda v: (v + 459.67) * 5 / 9,
    "K": lambda v: v,
}
_FROM_KELVIN = {
    "C": lambda k: k - 273.15,
    "F": lambda k: k * 9 / 5 - 459.67,
    "K": lambda k: k,
}


def convert(value, from_unit, to_unit):
    if from_unit not in _TO_KELVIN or to_unit not in _FROM_KELVIN:
        raise ValueError("unknown unit")
    kelvin = _TO_KELVIN[from_unit](value)
    if kelvin < -1e-9:
        raise ValueError("below absolute zero")
    return float(_FROM_KELVIN[to_unit](max(kelvin, 0.0)))

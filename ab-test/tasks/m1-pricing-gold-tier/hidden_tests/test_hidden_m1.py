import itertools

import pytest

from shop.pricing import calc, describe


def _legacy_calc(order, t, f):
    total = 0
    for i in order["items"]:
        total = total + i["price"] * i["qty"]
    if t == 2:
        total = total - total * 0.1
    ship = 0
    if total < 50:
        ship = 5.99
    if t == 2 and total > 100:
        ship = 0
    if f:
        ship = ship + 10
    tax = total * 0.22
    return round(total + ship + tax, 2)


def _legacy_describe(order, t, f):
    lines = []
    total = 0
    for i in order["items"]:
        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
        total = total + i["price"] * i["qty"]
    if t == 2:
        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
        total = total - total * 0.1
    ship = 0
    if total < 50:
        ship = 5.99
    if t == 2 and total > 100:
        ship = 0
    if f:
        ship = ship + 10
    lines.append("Shipping: " + "%.2f" % ship)
    tax = total * 0.22
    lines.append("VAT: " + "%.2f" % tax)
    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
    return "\n".join(lines)


ORDERS = [
    {"items": [{"name": "Pen", "price": 1.99, "qty": 3}]},
    {"items": [{"name": "Book", "price": 19.99, "qty": 2}, {"name": "Mug", "price": 9.5, "qty": 1}]},
    {"items": [{"name": "Lamp", "price": 55.5, "qty": 1}]},
    {"items": [{"name": "Chair", "price": 49.99, "qty": 1}]},
    {"items": [{"name": "Desk", "price": 112.0, "qty": 1}]},
    {"items": [{"name": "Shelf", "price": 99.9, "qty": 1}, {"name": "Screw", "price": 0.05, "qty": 40}]},
    {"items": [{"name": "TV", "price": 399.0, "qty": 1}, {"name": "Cable", "price": 7.49, "qty": 2}]},
    {"items": []},
]
CASES = list(itertools.product(range(len(ORDERS)), [1, 2], [False, True]))


@pytest.mark.parametrize("idx, t, f", CASES)
def test_existing_tiers_calc_unchanged(idx, t, f):
    assert calc(ORDERS[idx], t, f) == _legacy_calc(ORDERS[idx], t, f)


@pytest.mark.parametrize("idx, t, f", CASES)
def test_existing_tiers_describe_unchanged(idx, t, f):
    assert describe(ORDERS[idx], t, f) == _legacy_describe(ORDERS[idx], t, f)


def _gold_expected(order, express):
    items = sum(i["price"] * i["qty"] for i in order["items"])
    discounted = items * 0.85
    ship = 10 if express else 0
    return round(discounted + ship + discounted * 0.22, 2)


@pytest.mark.parametrize("idx", range(len(ORDERS)))
@pytest.mark.parametrize("express", [False, True])
def test_gold_calc(idx, express):
    assert calc(ORDERS[idx], 3, express) == pytest.approx(_gold_expected(ORDERS[idx], express), abs=0.011)


@pytest.mark.parametrize("idx", range(len(ORDERS) - 1))
@pytest.mark.parametrize("express", [False, True])
def test_gold_describe(idx, express):
    order = ORDERS[idx]
    lines = describe(order, 3, express).split("\n")
    items = sum(i["price"] * i["qty"] for i in order["items"])
    discount_lines = [line for line in lines if line.startswith("Gold discount: -")]
    assert len(discount_lines) == 1
    assert float(discount_lines[0].split("-", 1)[1]) == pytest.approx(items * 0.15, abs=0.011)
    assert "Shipping: %.2f" % (10 if express else 0) in lines
    assert lines[-1] == "Total: %.2f" % calc(order, 3, express)
    assert not any(line.startswith("Silver discount") for line in lines)
    # discount line comes right after the item lines, as for silver
    assert lines.index(discount_lines[0]) == len(order["items"])

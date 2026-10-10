# Pricing for the web shop.
from typing import NamedTuple

# Customer types, passed to calc and describe as `t`.
REGULAR = 1
SILVER = 2
GOLD = 3


class _Discount(NamedTuple):
    label: str
    rate: float


_DISCOUNTS = {
    SILVER: _Discount("Silver", 0.1),
    GOLD: _Discount("Gold", 0.15),
}


class _Breakdown(NamedTuple):
    discount: float
    shipping: float
    vat: float
    total: float


def calc(order, t, f):
    # t: customer type (REGULAR, SILVER or GOLD)
    # f: express shipping
    return _breakdown(order, t, f).total


def describe(order, t, f):
    lines = []
    for i in order["items"]:
        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
    breakdown = _breakdown(order, t, f)
    if t in _DISCOUNTS:
        lines.append(_DISCOUNTS[t].label + " discount: -" + "%.2f" % breakdown.discount)
    lines.append("Shipping: " + "%.2f" % breakdown.shipping)
    lines.append("VAT: " + "%.2f" % breakdown.vat)
    lines.append("Total: " + "%.2f" % breakdown.total)
    return "\n".join(lines)


def _breakdown(order, t, f):
    # Keep the explicit loop: since Python 3.12, sum() compensates float
    # rounding errors, which could change existing totals.
    total = 0
    for i in order["items"]:
        total = total + i["price"] * i["qty"]
    discount = 0
    if t in _DISCOUNTS:
        discount = total * _DISCOUNTS[t].rate
        total = total - discount
    shipping = 0
    if total < 50:
        shipping = 5.99
    if t == SILVER and total > 100:
        shipping = 0
    if t == GOLD:
        shipping = 0
    if f:
        shipping = shipping + 10
    vat = total * 0.22
    return _Breakdown(discount, shipping, vat, round(total + shipping + vat, 2))

# Pricing for the web shop.

from dataclasses import dataclass


@dataclass(frozen=True)
class _Tier:
    name: str
    discount_rate: float
    has_free_standard_shipping: bool


_REGULAR = _Tier("Regular", 0, False)

_TIERS_BY_CUSTOMER_TYPE = {
    1: _REGULAR,
    2: _Tier("Silver", 0.1, False),
    3: _Tier("Gold", 0.15, True),
}


@dataclass(frozen=True)
class _PriceBreakdown:
    discount: float
    shipping: float
    tax: float
    total: float


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold)
    # f: express shipping
    return _price_order(order, _tier_for(t), f).total


def describe(order, t, f):
    tier = _tier_for(t)
    breakdown = _price_order(order, tier, f)
    lines = []
    for i in order["items"]:
        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % _line_amount(i))
    if tier.discount_rate:
        lines.append(tier.name + " discount: -" + "%.2f" % breakdown.discount)
    lines.append("Shipping: " + "%.2f" % breakdown.shipping)
    lines.append("VAT: " + "%.2f" % breakdown.tax)
    lines.append("Total: " + "%.2f" % breakdown.total)
    return "\n".join(lines)


def _tier_for(customer_type):
    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR)


def _price_order(order, tier, express):
    subtotal = 0
    for i in order["items"]:
        subtotal = subtotal + _line_amount(i)
    discount = subtotal * tier.discount_rate
    discounted_subtotal = subtotal - discount
    shipping = 0
    if discounted_subtotal < 50 and not tier.has_free_standard_shipping:
        shipping = 5.99
    if express:
        shipping = shipping + 10
    tax = discounted_subtotal * 0.22
    return _PriceBreakdown(discount, shipping, tax, round(discounted_subtotal + shipping + tax, 2))


def _line_amount(item):
    return item["price"] * item["qty"]

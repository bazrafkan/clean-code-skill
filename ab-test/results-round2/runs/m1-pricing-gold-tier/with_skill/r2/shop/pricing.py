# Pricing for the web shop.

from dataclasses import dataclass


@dataclass(frozen=True)
class _Tier:
    name: str
    discount_rate: float
    has_free_standard_shipping: bool


_REGULAR = _Tier("Regular", discount_rate=0, has_free_standard_shipping=False)
_TIERS = {
    1: _REGULAR,
    2: _Tier("Silver", discount_rate=0.1, has_free_standard_shipping=False),
    3: _Tier("Gold", discount_rate=0.15, has_free_standard_shipping=True),
}


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold)
    # f: express shipping
    return _price_breakdown(order, _tier(t), f).total


def describe(order, t, f):
    tier = _tier(t)
    breakdown = _price_breakdown(order, tier, f)
    lines = []
    for item in order["items"]:
        lines.append(item["name"] + " x" + str(item["qty"]) + ": " + "%.2f" % (item["price"] * item["qty"]))
    if tier.discount_rate > 0:
        lines.append(tier.name + " discount: -" + "%.2f" % breakdown.discount)
    lines.append("Shipping: " + "%.2f" % breakdown.shipping)
    lines.append("VAT: " + "%.2f" % breakdown.vat)
    lines.append("Total: " + "%.2f" % breakdown.total)
    return "\n".join(lines)


def _tier(t):
    # Unrecognised customer types have always been priced as regular.
    return _TIERS.get(t, _REGULAR)


@dataclass(frozen=True)
class _PriceBreakdown:
    discount: float
    shipping: float
    vat: float
    total: float


def _price_breakdown(order, tier, express):
    subtotal = 0
    for item in order["items"]:
        subtotal = subtotal + item["price"] * item["qty"]
    discount = subtotal * tier.discount_rate
    discounted = subtotal - discount
    shipping = _shipping(discounted, tier, express)
    vat = discounted * 0.22
    return _PriceBreakdown(discount, shipping, vat, round(discounted + shipping + vat, 2))


def _shipping(discounted_total, tier, express):
    shipping = 0
    if discounted_total < 50 and not tier.has_free_standard_shipping:
        shipping = 5.99
    if express:
        shipping = shipping + 10
    return shipping

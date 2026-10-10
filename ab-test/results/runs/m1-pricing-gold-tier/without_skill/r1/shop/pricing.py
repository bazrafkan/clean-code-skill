# Pricing for the web shop.

from dataclasses import dataclass
from typing import Optional

REGULAR = 1
SILVER = 2
GOLD = 3

VAT_RATE = 0.22
STANDARD_SHIPPING_FEE = 5.99
FREE_SHIPPING_FROM = 50  # discounted subtotal from which standard shipping is free
EXPRESS_SURCHARGE = 10


@dataclass(frozen=True)
class _Tier:
    name: str
    discount_rate: float = 0.0
    free_shipping_over: Optional[float] = None  # tier-specific free standard shipping threshold
    always_free_shipping: bool = False


_TIERS = {
    REGULAR: _Tier("Regular"),
    SILVER: _Tier("Silver", discount_rate=0.1, free_shipping_over=100),
    GOLD: _Tier("Gold", discount_rate=0.15, always_free_shipping=True),
}


@dataclass(frozen=True)
class _Quote:
    tier: _Tier
    discount: float
    shipping: float
    vat: float
    total: float


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold; unknown types price as regular)
    # f: express shipping
    return _quote(order, t, f).total


def describe(order, t, f):
    quote = _quote(order, t, f)
    lines = [_item_line(item) for item in order["items"]]
    if quote.tier.discount_rate:
        lines.append(quote.tier.name + " discount: -" + _money(quote.discount))
    lines.append("Shipping: " + _money(quote.shipping))
    lines.append("VAT: " + _money(quote.vat))
    lines.append("Total: " + _money(quote.total))
    return "\n".join(lines)


def _quote(order, t, express):
    tier = _TIERS.get(t, _TIERS[REGULAR])
    total = _subtotal(order)
    discount = 0
    if tier.discount_rate:
        discount = total * tier.discount_rate
        total = total - discount
    shipping = _standard_shipping(tier, total)
    if express:
        shipping = shipping + EXPRESS_SURCHARGE
    vat = total * VAT_RATE
    return _Quote(tier, discount, shipping, vat, round(total + shipping + vat, 2))


def _subtotal(order):
    # Plain left-to-right addition on purpose: since Python 3.12, sum() uses
    # compensated float summation, which can give slightly different totals.
    total = 0
    for item in order["items"]:
        total = total + _item_amount(item)
    return total


def _standard_shipping(tier, total):
    if tier.always_free_shipping:
        return 0
    if tier.free_shipping_over is not None and total > tier.free_shipping_over:
        return 0
    if total < FREE_SHIPPING_FROM:
        return STANDARD_SHIPPING_FEE
    return 0


def _item_amount(item):
    return item["price"] * item["qty"]


def _item_line(item):
    return item["name"] + " x" + str(item["qty"]) + ": " + _money(_item_amount(item))


def _money(amount):
    return "%.2f" % amount

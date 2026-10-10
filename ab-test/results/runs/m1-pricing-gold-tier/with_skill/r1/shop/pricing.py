# Pricing for the web shop.

from dataclasses import dataclass

_VAT_RATE = 0.22
_STANDARD_SHIPPING_FEE = 5.99
_FREE_SHIPPING_THRESHOLD = 50
_EXPRESS_SURCHARGE = 10


@dataclass(frozen=True)
class _Tier:
    name: str
    discount_rate: float = 0.0
    has_free_standard_shipping: bool = False

    @property
    def has_discount(self):
        return self.discount_rate > 0

    def discount_on(self, amount):
        return amount * self.discount_rate if self.has_discount else 0


_REGULAR = _Tier("Regular")
_TIERS_BY_CUSTOMER_TYPE = {
    1: _REGULAR,
    2: _Tier("Silver", discount_rate=0.1),
    3: _Tier("Gold", discount_rate=0.15, has_free_standard_shipping=True),
}


def calc(order, t, f):
    """Return the order total with shipping and VAT, rounded to cents.

    t is the customer type (1 = regular, 2 = silver, 3 = gold); unknown
    types are priced as regular. f requests express shipping.
    """
    return _price_order(order, _tier_for(t), f).total


def describe(order, t, f):
    """Return the order's receipt as one newline-separated string.

    Arguments are as for calc.
    """
    tier = _tier_for(t)
    breakdown = _price_order(order, tier, f)
    lines = [_item_line(item) for item in order["items"]]
    if tier.has_discount:
        lines.append(f"{tier.name} discount: -{_money(breakdown.discount)}")
    lines.append(f"Shipping: {_money(breakdown.shipping)}")
    lines.append(f"VAT: {_money(breakdown.vat)}")
    lines.append(f"Total: {_money(breakdown.total)}")
    return "\n".join(lines)


def _tier_for(customer_type):
    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR)


@dataclass(frozen=True)
class _PriceBreakdown:
    discount: float
    shipping: float
    vat: float
    total: float


def _price_order(order, tier, is_express):
    subtotal = _subtotal(order["items"])
    discount = tier.discount_on(subtotal)
    discounted = subtotal - discount
    shipping = _standard_shipping(discounted, tier)
    if is_express:
        shipping = shipping + _EXPRESS_SURCHARGE
    vat = discounted * _VAT_RATE
    total = round(discounted + shipping + vat, 2)
    return _PriceBreakdown(discount, shipping, vat, total)


def _subtotal(items):
    # A plain loop rather than sum(): since Python 3.12 sum() compensates
    # float rounding, which can move a rounded amount by a cent.
    subtotal = 0
    for item in items:
        subtotal = subtotal + _line_amount(item)
    return subtotal


def _line_amount(item):
    return item["price"] * item["qty"]


def _standard_shipping(discounted, tier):
    if tier.has_free_standard_shipping:
        return 0
    if discounted < _FREE_SHIPPING_THRESHOLD:
        return _STANDARD_SHIPPING_FEE
    return 0


def _item_line(item):
    return f"{item['name']} x{item['qty']}: {_money(_line_amount(item))}"


def _money(amount):
    return f"{amount:.2f}"

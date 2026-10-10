# Pricing for the web shop.

from dataclasses import dataclass

_VAT_RATE = 0.22
_STANDARD_SHIPPING_FEE = 5.99
_FREE_SHIPPING_THRESHOLD = 50
_EXPRESS_SURCHARGE = 10


@dataclass(frozen=True)
class _CustomerTier:
    name: str
    discount_rate: float = 0.0
    always_free_standard_shipping: bool = False

    @property
    def has_discount(self):
        return self.discount_rate > 0


_REGULAR = _CustomerTier("Regular")
_TIERS_BY_CUSTOMER_TYPE = {
    1: _REGULAR,
    2: _CustomerTier("Silver", discount_rate=0.1),
    3: _CustomerTier("Gold", discount_rate=0.15, always_free_standard_shipping=True),
}


@dataclass(frozen=True)
class _PriceBreakdown:
    discount: float
    shipping: float
    vat: float
    total: float


def calc(order, t, f):
    """Return the amount to charge for the order, shipping and VAT included.

    t is the customer type (1 = regular, 2 = silver, 3 = gold); f is true for
    express shipping.
    """
    return _price_order(order, _tier_for(t), express=f).total


def describe(order, t, f):
    """Return the order's receipt as text; arguments as for calc."""
    tier = _tier_for(t)
    breakdown = _price_order(order, tier, express=f)
    lines = [_item_line(item) for item in order["items"]]
    if tier.has_discount:
        lines.append(f"{tier.name} discount: -{breakdown.discount:.2f}")
    lines.append(f"Shipping: {breakdown.shipping:.2f}")
    lines.append(f"VAT: {breakdown.vat:.2f}")
    lines.append(f"Total: {breakdown.total:.2f}")
    return "\n".join(lines)


def _tier_for(customer_type):
    # Unknown types have always been priced as regular; callers may rely on it.
    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR)


def _price_order(order, tier, express):
    subtotal = _subtotal(order["items"])
    discount = subtotal * tier.discount_rate
    discounted_subtotal = subtotal - discount
    shipping = _standard_shipping_fee(tier, discounted_subtotal)
    if express:
        shipping += _EXPRESS_SURCHARGE
    vat = discounted_subtotal * _VAT_RATE
    total = round(discounted_subtotal + shipping + vat, 2)
    return _PriceBreakdown(discount, shipping, vat, total)


def _subtotal(items):
    # Plain left-to-right addition on purpose: sum() compensates float rounding
    # (Python 3.12+), which would shift some totals by a cent.
    subtotal = 0
    for item in items:
        subtotal += _line_amount(item)
    return subtotal


def _standard_shipping_fee(tier, discounted_subtotal):
    if tier.always_free_standard_shipping:
        return 0
    if discounted_subtotal >= _FREE_SHIPPING_THRESHOLD:
        return 0
    return _STANDARD_SHIPPING_FEE


def _item_line(item):
    return f"{item['name']} x{item['qty']}: {_line_amount(item):.2f}"


def _line_amount(item):
    return item["price"] * item["qty"]

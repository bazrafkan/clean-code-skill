# Pricing for the web shop.

from collections.abc import Callable, Iterable
from dataclasses import dataclass

_VAT_RATE = 0.22
_STANDARD_SHIPPING = 5.99
_FREE_STANDARD_SHIPPING_FROM = 50
_EXPRESS_SURCHARGE = 10
_SILVER_FREE_SHIPPING_OVER = 100


@dataclass(frozen=True)
class _CustomerTier:
    name: str
    discount_rate: float
    waives_standard_shipping: Callable[[float], bool]

    @property
    def has_discount(self) -> bool:
        return self.discount_rate > 0


@dataclass(frozen=True)
class _PriceBreakdown:
    discount: float
    shipping: float
    vat: float
    total: float


_REGULAR_TIER = _CustomerTier(
    "Regular",
    discount_rate=0.0,
    waives_standard_shipping=lambda discounted_subtotal: False,
)
_TIERS_BY_CUSTOMER_TYPE = {
    1: _REGULAR_TIER,
    2: _CustomerTier(
        "Silver",
        discount_rate=0.1,
        waives_standard_shipping=lambda discounted_subtotal: (
            discounted_subtotal > _SILVER_FREE_SHIPPING_OVER
        ),
    ),
    3: _CustomerTier(
        "Gold",
        discount_rate=0.15,
        waives_standard_shipping=lambda discounted_subtotal: True,
    ),
}


def calc(order, t, f):
    """Return the order total with shipping and VAT, rounded to cents.

    t is the customer type (1 = regular, 2 = silver, 3 = gold).
    f is truthy for express shipping.
    """
    return _price(order, _tier_for(t), f).total


def describe(order, t, f):
    """Return a newline-separated receipt for the order; t and f as for calc."""
    tier = _tier_for(t)
    lines = [_item_line(item) for item in order["items"]]
    price = _price(order, tier, f)
    if tier.has_discount:
        lines.append(f"{tier.name} discount: -{_money(price.discount)}")
    lines.append(f"Shipping: {_money(price.shipping)}")
    lines.append(f"VAT: {_money(price.vat)}")
    lines.append(f"Total: {_money(price.total)}")
    return "\n".join(lines)


def _tier_for(customer_type) -> _CustomerTier:
    # Unknown codes have always been priced as regular; callers may rely on that.
    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR_TIER)


def _price(order: dict, tier: _CustomerTier, is_express) -> _PriceBreakdown:
    subtotal = _subtotal(order["items"])
    discount = subtotal * tier.discount_rate
    discounted_subtotal = subtotal - discount
    shipping = _shipping(discounted_subtotal, tier, is_express)
    vat = discounted_subtotal * _VAT_RATE
    total = round(discounted_subtotal + shipping + vat, 2)
    return _PriceBreakdown(discount, shipping, vat, total)


def _subtotal(items: Iterable[dict]) -> float:
    # A plain left-to-right loop, not sum(): since Python 3.12 sum() compensates
    # float rounding errors, which could change existing totals by a cent.
    subtotal: float = 0
    for item in items:
        subtotal += _line_total(item)
    return subtotal


def _shipping(discounted_subtotal: float, tier: _CustomerTier, is_express) -> float:
    pays_standard_shipping = (
        discounted_subtotal < _FREE_STANDARD_SHIPPING_FROM
        and not tier.waives_standard_shipping(discounted_subtotal)
    )
    standard = _STANDARD_SHIPPING if pays_standard_shipping else 0
    surcharge = _EXPRESS_SURCHARGE if is_express else 0
    return standard + surcharge


def _item_line(item: dict) -> str:
    return f"{item['name']} x{item['qty']}: {_money(_line_total(item))}"


def _line_total(item: dict) -> float:
    return item["price"] * item["qty"]


def _money(amount: float) -> str:
    return f"{amount:.2f}"

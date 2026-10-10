# Pricing for the web shop.

REGULAR = 1
SILVER = 2
GOLD = 3

# Customer type -> (label shown in `describe`, discount rate on items).
# Types not listed here (including REGULAR) get no discount.
TIER_DISCOUNTS = {
    SILVER: ("Silver", 0.1),
    GOLD: ("Gold", 0.15),
}

VAT_RATE = 0.22
STANDARD_SHIPPING = 5.99
FREE_STANDARD_SHIPPING_FROM = 50  # discounted total at or above this ships free
SILVER_FREE_SHIPPING_ABOVE = 100
EXPRESS_SURCHARGE = 10


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold)
    # f: express shipping
    return _price(order["items"], t, f)["total"]


def describe(order, t, f):
    items = list(order["items"])  # iterated twice below
    lines = []
    for i in items:
        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + _money(_line_amount(i)))
    price = _price(items, t, f)
    if t in TIER_DISCOUNTS:
        label = TIER_DISCOUNTS[t][0]
        lines.append(label + " discount: -" + _money(price["discount"]))
    lines.append("Shipping: " + _money(price["shipping"]))
    lines.append("VAT: " + _money(price["vat"]))
    lines.append("Total: " + _money(price["total"]))
    return "\n".join(lines)


def _price(items, t, f):
    """Compute the order breakdown shared by `calc` and `describe`."""
    subtotal = 0
    for i in items:
        subtotal = subtotal + _line_amount(i)
    discount = 0
    discounted = subtotal
    if t in TIER_DISCOUNTS:
        rate = TIER_DISCOUNTS[t][1]
        discount = subtotal * rate
        discounted = subtotal - discount
    shipping = _shipping(discounted, t, f)
    vat = discounted * VAT_RATE
    return {
        "discount": discount,
        "shipping": shipping,
        "vat": vat,
        "total": round(discounted + shipping + vat, 2),
    }


def _shipping(discounted, t, express):
    ship = 0
    if discounted < FREE_STANDARD_SHIPPING_FROM:
        ship = STANDARD_SHIPPING
    # Kept from the original rules. It never changes the result today,
    # because totals above 100 already ship free for everyone.
    if t == SILVER and discounted > SILVER_FREE_SHIPPING_ABOVE:
        ship = 0
    if t == GOLD:
        ship = 0
    if express:
        ship = ship + EXPRESS_SURCHARGE
    return ship


def _line_amount(item):
    return item["price"] * item["qty"]


def _money(amount):
    return "%.2f" % amount

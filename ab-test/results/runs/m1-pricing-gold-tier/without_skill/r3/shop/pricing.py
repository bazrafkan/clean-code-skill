# Pricing for the web shop.

# Customer types.
REGULAR = 1
SILVER = 2
GOLD = 3

VAT_RATE = 0.22
STANDARD_SHIPPING = 5.99
STANDARD_SHIPPING_BELOW = 50  # orders under this (after discount) pay standard shipping
SILVER_FREE_SHIPPING_ABOVE = 100
EXPRESS_SURCHARGE = 10


def _discount(t):
    """Return (label, rate) for customer types that get a discount, else None."""
    if t == SILVER:
        return "Silver", 0.1
    if t == GOLD:
        return "Gold", 0.15
    return None


def _shipping(total, t, f):
    ship = 0
    if total < STANDARD_SHIPPING_BELOW:
        ship = STANDARD_SHIPPING
    if t == SILVER and total > SILVER_FREE_SHIPPING_ABOVE:
        ship = 0
    if t == GOLD:
        ship = 0  # standard shipping is always free for gold
    if f:
        ship = ship + EXPRESS_SURCHARGE
    return ship


def _breakdown(order, t, f):
    """Compute every figure of an order, shared by calc and describe.

    Returns (item_lines, discount_line, ship, tax, total), where total is the
    discounted items total (before shipping and VAT) and discount_line is None
    for customer types without a discount.
    """
    item_lines = []
    total = 0
    for i in order["items"]:
        line_total = i["price"] * i["qty"]
        item_lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % line_total)
        total = total + line_total
    discount_line = None
    tier = _discount(t)
    if tier is not None:
        label, rate = tier
        discount = total * rate
        discount_line = label + " discount: -" + "%.2f" % discount
        total = total - discount
    ship = _shipping(total, t, f)
    tax = total * VAT_RATE
    return item_lines, discount_line, ship, tax, total


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold)
    # f: express shipping
    _, _, ship, tax, total = _breakdown(order, t, f)
    return round(total + ship + tax, 2)


def describe(order, t, f):
    lines, discount_line, ship, tax, total = _breakdown(order, t, f)
    if discount_line is not None:
        lines.append(discount_line)
    lines.append("Shipping: " + "%.2f" % ship)
    lines.append("VAT: " + "%.2f" % tax)
    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
    return "\n".join(lines)

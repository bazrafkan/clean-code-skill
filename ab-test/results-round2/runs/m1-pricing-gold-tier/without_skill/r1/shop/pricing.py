# Pricing for the web shop.

# Customer types, passed as `t`. Any other value is priced as regular.
REGULAR = 1
SILVER = 2
GOLD = 3


def _discount(t):
    # Item discount for customer type t as (label, rate), or None.
    if t == SILVER:
        return "Silver", 0.1
    if t == GOLD:
        return "Gold", 0.15
    return None


def _shipping(total, t, f):
    # total: item total after discount
    # f: express shipping
    ship = 0
    if total < 50:
        ship = 5.99
    if t == SILVER and total > 100:
        ship = 0
    if t == GOLD:
        ship = 0  # standard shipping is always free for gold
    if f:
        ship = ship + 10
    return ship


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold)
    # f: express shipping
    total = 0
    for i in order["items"]:
        total = total + i["price"] * i["qty"]
    discount = _discount(t)
    if discount:
        _, rate = discount
        total = total - total * rate
    ship = _shipping(total, t, f)
    tax = total * 0.22
    return round(total + ship + tax, 2)


def describe(order, t, f):
    lines = []
    total = 0
    for i in order["items"]:
        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
        total = total + i["price"] * i["qty"]
    discount = _discount(t)
    if discount:
        label, rate = discount
        lines.append(label + " discount: -" + "%.2f" % (total * rate))
        total = total - total * rate
    ship = _shipping(total, t, f)
    lines.append("Shipping: " + "%.2f" % ship)
    tax = total * 0.22
    lines.append("VAT: " + "%.2f" % tax)
    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
    return "\n".join(lines)

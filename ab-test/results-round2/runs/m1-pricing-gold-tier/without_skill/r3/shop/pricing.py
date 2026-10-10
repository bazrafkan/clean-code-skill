# Pricing for the web shop.


def calc(order, t, f):
    # t: customer type (1 = regular, 2 = silver, 3 = gold)
    # f: express shipping
    total = 0
    for i in order["items"]:
        total = total + i["price"] * i["qty"]
    if t == 2:
        total = total - total * 0.1
    elif t == 3:
        total = total - total * 0.15
    ship = 0
    if total < 50:
        ship = 5.99
    if t == 2 and total > 100:
        ship = 0
    if t == 3:
        ship = 0  # gold: standard shipping is always free
    if f:
        ship = ship + 10
    tax = total * 0.22
    return round(total + ship + tax, 2)


def describe(order, t, f):
    lines = []
    total = 0
    for i in order["items"]:
        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
        total = total + i["price"] * i["qty"]
    if t == 2:
        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
        total = total - total * 0.1
    elif t == 3:
        lines.append("Gold discount: -" + "%.2f" % (total * 0.15))
        total = total - total * 0.15
    ship = 0
    if total < 50:
        ship = 5.99
    if t == 2 and total > 100:
        ship = 0
    if t == 3:
        ship = 0  # gold: standard shipping is always free
    if f:
        ship = ship + 10
    lines.append("Shipping: " + "%.2f" % ship)
    tax = total * 0.22
    lines.append("VAT: " + "%.2f" % tax)
    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
    return "\n".join(lines)

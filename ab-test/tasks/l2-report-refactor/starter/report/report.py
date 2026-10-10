import csv


def generate(path, fmt):
    rows = []
    f = open(path)
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)
    f.close()

    reg = {}
    prod = {}
    units = {}
    n = 0
    tot = 0
    for row in rows:
        u = int(row["units"])
        p = float(row["unit_price"])
        v = u * p
        n = n + 1
        tot = tot + v
        if row["region"] in reg:
            reg[row["region"]] = reg[row["region"]] + v
        else:
            reg[row["region"]] = v
        if row["product"] in prod:
            prod[row["product"]] = prod[row["product"]] + v
            units[row["product"]] = units[row["product"]] + u
        else:
            prod[row["product"]] = v
            units[row["product"]] = u

    out = ""
    if fmt == "text":
        out = out + "SALES REPORT\n"
        out = out + "=" * 40 + "\n"
    elif fmt == "html":
        out = out + "<html><body>\n"
        out = out + "<h1>Sales report</h1>\n"
    else:
        raise Exception("bad format")

    if fmt == "text":
        out = out + "\nTotals by region\n"
        out = out + "-" * 40 + "\n"
        for k in sorted(reg):
            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
    elif fmt == "html":
        out = out + "<h2>Totals by region</h2>\n<table>\n"
        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
        for k in sorted(reg):
            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
        out = out + "</table>\n"

    if fmt == "text":
        out = out + "\nTotals by product\n"
        out = out + "-" * 40 + "\n"
        for k in sorted(prod):
            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
    elif fmt == "html":
        out = out + "<h2>Totals by product</h2>\n<table>\n"
        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
        for k in sorted(prod):
            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
        out = out + "</table>\n"

    best = None
    for k in prod:
        if best is None or prod[k] > prod[best]:
            best = k
    if n > 0:
        avg = tot / n
    else:
        avg = 0

    if fmt == "text":
        out = out + "\nTop product: " + str(best) + "\n"
        out = out + "Average order value: " + "%.2f" % avg + "\n"
    elif fmt == "html":
        out = out + "<p>Top product: " + str(best) + "</p>\n"
        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
        out = out + "</body></html>\n"
    return out

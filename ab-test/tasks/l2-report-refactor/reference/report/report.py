import csv
from dataclasses import dataclass


@dataclass
class Summary:
    region_revenue: dict
    product_revenue: dict
    product_units: dict
    top_product: str
    average_order_value: float


def summarize(rows):
    region_revenue, product_revenue, product_units = {}, {}, {}
    total = 0.0
    for row in rows:
        units = int(row["units"])
        revenue = units * float(row["unit_price"])
        total += revenue
        region_revenue[row["region"]] = region_revenue.get(row["region"], 0) + revenue
        product_revenue[row["product"]] = product_revenue.get(row["product"], 0) + revenue
        product_units[row["product"]] = product_units.get(row["product"], 0) + units
    top = None
    for product, revenue in product_revenue.items():
        if top is None or revenue > product_revenue[top]:
            top = product
    average = total / len(rows) if rows else 0
    return Summary(region_revenue, product_revenue, product_units, top, average)


def _text(s):
    rule = "-" * 40 + "\n"
    out = "SALES REPORT\n" + "=" * 40 + "\n"
    out += "\nTotals by region\n" + rule
    out += "".join(k.ljust(20) + ("%.2f" % s.region_revenue[k]).rjust(20) + "\n" for k in sorted(s.region_revenue))
    out += "\nTotals by product\n" + rule
    out += "".join(
        k.ljust(20) + str(s.product_units[k]).rjust(8) + ("%.2f" % s.product_revenue[k]).rjust(12) + "\n"
        for k in sorted(s.product_revenue)
    )
    out += "\nTop product: %s\nAverage order value: %.2f\n" % (s.top_product, s.average_order_value)
    return out


def _html(s):
    out = "<html><body>\n<h1>Sales report</h1>\n"
    out += "<h2>Totals by region</h2>\n<table>\n<tr><th>Region</th><th>Revenue</th></tr>\n"
    out += "".join("<tr><td>%s</td><td>%.2f</td></tr>\n" % (k, s.region_revenue[k]) for k in sorted(s.region_revenue))
    out += "</table>\n<h2>Totals by product</h2>\n<table>\n<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
    out += "".join(
        "<tr><td>%s</td><td>%s</td><td>%.2f</td></tr>\n" % (k, s.product_units[k], s.product_revenue[k])
        for k in sorted(s.product_revenue)
    )
    out += "</table>\n<p>Top product: %s</p>\n<p>Average order value: %.2f</p>\n</body></html>\n" % (
        s.top_product,
        s.average_order_value,
    )
    return out


def _markdown(s):
    out = "# Sales report\n\n## Totals by region\n\n| Region | Revenue |\n|---|---|\n"
    out += "".join("| %s | %.2f |\n" % (k, s.region_revenue[k]) for k in sorted(s.region_revenue))
    out += "\n## Totals by product\n\n| Product | Units | Revenue |\n|---|---|---|\n"
    out += "".join(
        "| %s | %d | %.2f |\n" % (k, s.product_units[k], s.product_revenue[k]) for k in sorted(s.product_revenue)
    )
    out += "\n**Top product:** %s\n\n**Average order value:** %.2f\n" % (s.top_product, s.average_order_value)
    return out


_RENDERERS = {"text": _text, "html": _html, "md": _markdown}


def generate(path, fmt):
    if fmt not in _RENDERERS:
        raise ValueError("unknown format: %s" % fmt)
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return _RENDERERS[fmt](summarize(rows))

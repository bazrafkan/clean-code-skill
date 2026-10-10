import csv

import pytest

from report.report import generate


def _legacy(path, fmt):
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
    avg = tot / n if n > 0 else 0
    if fmt == "text":
        out = out + "\nTop product: " + str(best) + "\n"
        out = out + "Average order value: " + "%.2f" % avg + "\n"
    elif fmt == "html":
        out = out + "<p>Top product: " + str(best) + "</p>\n"
        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
        out = out + "</body></html>\n"
    return out, reg, prod, units, best, avg


def _expected_md(path):
    _, reg, prod, units, best, avg = _legacy(path, "text")
    out = "# Sales report\n\n## Totals by region\n\n| Region | Revenue |\n|---|---|\n"
    for k in sorted(reg):
        out += "| %s | %.2f |\n" % (k, reg[k])
    out += "\n## Totals by product\n\n| Product | Units | Revenue |\n|---|---|---|\n"
    for k in sorted(prod):
        out += "| %s | %d | %.2f |\n" % (k, units[k], prod[k])
    out += "\n**Top product:** %s\n\n**Average order value:** %.2f\n" % (best, avg)
    return out


HEADER = "date,region,product,units,unit_price\n"
DATASETS = {
    "sample": HEADER
    + "2026-01-03,North,Widget,10,2.50\n2026-01-04,South,Gadget,3,19.99\n2026-01-04,North,Gadget,1,19.99\n"
    + "2026-01-05,East,Widget,7,2.50\n2026-01-06,South,Doohickey,2,7.25\n2026-01-07,East,Gadget,2,19.99\n",
    "tie_keeps_first_seen": HEADER + "2026-02-01,West,Zeta,2,5.00\n2026-02-01,West,Alpha,1,10.00\n2026-02-02,East,Mid,1,3.00\n",
    "header_only": HEADER,
    "many_regions": HEADER
    + "".join(
        "2026-03-%02d,%s,%s,%d,%.2f\n" % (d, region, product, d % 5 + 1, 1.1 * d)
        for d, (region, product) in enumerate(
            [("North", "A"), ("South", "B"), ("East", "C"), ("West", "A"), ("Central", "B"), ("North", "C"), ("Islands", "D")],
            start=1,
        )
    ),
}


@pytest.fixture(params=sorted(DATASETS))
def csv_path(request, tmp_path):
    path = tmp_path / (request.param + ".csv")
    path.write_text(DATASETS[request.param])
    return str(path)


@pytest.mark.parametrize("fmt", ["text", "html"])
def test_existing_formats_unchanged(csv_path, fmt):
    assert generate(csv_path, fmt) == _legacy(csv_path, fmt)[0]


def test_markdown_output(csv_path):
    assert generate(csv_path, "md") == _expected_md(csv_path)


def test_unknown_format_raises(csv_path):
    with pytest.raises(Exception):
        generate(csv_path, "pdf")

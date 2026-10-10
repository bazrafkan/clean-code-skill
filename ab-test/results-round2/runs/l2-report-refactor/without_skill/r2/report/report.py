"""Sales report: read a sales CSV, summarise it, render it in one of several formats.

The work is split into three steps so that each can change on its own:

1. ``_read_rows`` loads the CSV.
2. ``summarize`` turns the rows into a format-independent ``SalesSummary``.
3. A renderer turns the summary into text. Renderers are listed in ``RENDERERS``.

To add an output format, write a ``render_<name>(summary) -> str`` function and
add it to ``RENDERERS``. Nothing else needs to change.
"""

import csv
from typing import Callable, NamedTuple


class RegionTotal(NamedTuple):
    name: str
    revenue: float


class ProductTotal(NamedTuple):
    name: str
    units: int
    revenue: float


class SalesSummary(NamedTuple):
    regions: list[RegionTotal]  # sorted by name
    products: list[ProductTotal]  # sorted by name
    top_product: str | None  # None when there are no rows
    average_order_value: float


# --- Input ------------------------------------------------------------------


def _read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _accumulate(totals, key, amount):
    # The first amount is stored as is rather than added to a zero start
    # value, so the totals are exactly what earlier versions produced
    # (0 + -0.0 would otherwise turn "-0.00" into "0.00").
    totals[key] = totals[key] + amount if key in totals else amount


def summarize(rows):
    revenue_by_region = {}
    revenue_by_product = {}
    units_by_product = {}
    total_revenue = 0
    for row in rows:
        units = int(row["units"])
        revenue = units * float(row["unit_price"])
        # Add in row order with a plain loop: sum() uses compensated
        # summation on Python 3.12+ and could change the rounded output.
        total_revenue = total_revenue + revenue
        _accumulate(revenue_by_region, row["region"], revenue)
        _accumulate(revenue_by_product, row["product"], revenue)
        _accumulate(units_by_product, row["product"], units)

    # Ties go to the product seen first in the file.
    top_product = max(revenue_by_product, key=revenue_by_product.get, default=None)
    average = total_revenue / len(rows) if rows else 0.0

    return SalesSummary(
        regions=[RegionTotal(name, revenue_by_region[name]) for name in sorted(revenue_by_region)],
        products=[
            ProductTotal(name, units_by_product[name], revenue_by_product[name])
            for name in sorted(revenue_by_product)
        ],
        top_product=top_product,
        average_order_value=average,
    )


# --- Renderers --------------------------------------------------------------


def _money(amount):
    return "%.2f" % amount


def _join_lines(lines):
    return "".join(line + "\n" for line in lines)


def render_text(summary):
    rule_width = 40
    lines = ["SALES REPORT", "=" * rule_width]

    lines += ["", "Totals by region", "-" * rule_width]
    for region in summary.regions:
        lines.append(region.name.ljust(20) + _money(region.revenue).rjust(20))

    lines += ["", "Totals by product", "-" * rule_width]
    for product in summary.products:
        lines.append(
            product.name.ljust(20) + str(product.units).rjust(8) + _money(product.revenue).rjust(12)
        )

    lines += [
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _html_row(cell_tag, cells):
    return "<tr>" + "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells) + "</tr>"


def render_html(summary):
    # Values are inserted unescaped, as they always have been.
    lines = ["<html><body>", "<h1>Sales report</h1>"]

    lines += ["<h2>Totals by region</h2>", "<table>", _html_row("th", ["Region", "Revenue"])]
    for region in summary.regions:
        lines.append(_html_row("td", [region.name, _money(region.revenue)]))
    lines.append("</table>")

    lines += ["<h2>Totals by product</h2>", "<table>", _html_row("th", ["Product", "Units", "Revenue"])]
    for product in summary.products:
        lines.append(_html_row("td", [product.name, str(product.units), _money(product.revenue)]))
    lines.append("</table>")

    lines += [
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_money(summary.average_order_value)}</p>",
        "</body></html>",
    ]
    return _join_lines(lines)


def _md_row(cells):
    return "| " + " | ".join(cells) + " |"


def _md_table(headers, rows):
    separator = "|" + "---|" * len(headers)
    return [_md_row(headers), separator] + [_md_row(row) for row in rows]


def render_markdown(summary):
    # Like the HTML renderer, values are inserted unescaped.
    region_rows = [[region.name, _money(region.revenue)] for region in summary.regions]
    product_rows = [
        [product.name, str(product.units), _money(product.revenue)] for product in summary.products
    ]
    blocks = [
        ["# Sales report"],
        ["## Totals by region"],
        _md_table(["Region", "Revenue"], region_rows),
        ["## Totals by product"],
        _md_table(["Product", "Units", "Revenue"], product_rows),
        [f"**Top product:** {summary.top_product}"],
        [f"**Average order value:** {_money(summary.average_order_value)}"],
    ]
    lines = []
    for block in blocks:
        if lines:
            lines.append("")
        lines += block
    return _join_lines(lines)


Renderer = Callable[[SalesSummary], str]

RENDERERS: dict[str, Renderer] = {
    "text": render_text,
    "html": render_html,
    "md": render_markdown,
}


# --- Entry point ------------------------------------------------------------


def generate(path, fmt):
    render = RENDERERS.get(fmt)
    if render is None:
        raise ValueError(f"bad format: {fmt!r} (expected one of: {', '.join(RENDERERS)})")
    return render(summarize(_read_rows(path)))

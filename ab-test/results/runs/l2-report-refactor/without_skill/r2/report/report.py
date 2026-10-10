"""Sales report built from a CSV of orders, rendered as plain text, HTML or Markdown.

The figures are computed once, by ``summarize``, independently of any output format.
Each format is a single ``_render_<format>(summary)`` function registered in
``_RENDERERS``; adding a format means writing one such function and registering it.
"""

import csv
from dataclasses import dataclass
from typing import Optional

REGION_COLUMNS = ("Region", "Revenue")
PRODUCT_COLUMNS = ("Product", "Units", "Revenue")

TEXT_RULE_WIDTH = 40
TEXT_REGION_WIDTHS = (20, 20)
TEXT_PRODUCT_WIDTHS = (20, 8, 12)


@dataclass(frozen=True)
class RegionTotal:
    name: str
    revenue: float


@dataclass(frozen=True)
class ProductTotal:
    name: str
    units: int
    revenue: float


@dataclass(frozen=True)
class SalesSummary:
    """Format-independent figures of a sales report; totals are sorted by name."""

    regions: list[RegionTotal]
    products: list[ProductTotal]
    top_product: Optional[str]
    average_order_value: float


def generate(path, fmt):
    """Return the sales report for the orders CSV at ``path``, rendered as ``fmt``.

    ``fmt`` is "text", "html" or "md"; any other value raises ``ValueError``.
    """
    try:
        render = _RENDERERS[fmt]
    except KeyError:
        supported = ", ".join(_RENDERERS)
        raise ValueError(f"bad format: {fmt!r} (expected one of: {supported})") from None
    return render(summarize(_read_orders(path)))


def summarize(orders):
    """Compute the report figures from order rows (dicts with region, product, units, unit_price)."""
    revenue_by_region = {}
    revenue_by_product = {}
    units_by_product = {}
    total_revenue = 0
    for order in orders:
        units = int(order["units"])
        revenue = units * float(order["unit_price"])
        total_revenue += revenue
        _add(revenue_by_region, order["region"], revenue)
        _add(revenue_by_product, order["product"], revenue)
        _add(units_by_product, order["product"], units)

    return SalesSummary(
        regions=[RegionTotal(name, revenue_by_region[name]) for name in sorted(revenue_by_region)],
        products=[
            ProductTotal(name, units_by_product[name], revenue_by_product[name])
            for name in sorted(revenue_by_product)
        ],
        # Ties go to the product seen first in the file.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / len(orders) if orders else 0,
    )


def _read_orders(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _add(totals, key, amount):
    # A new key starts at `amount` itself rather than 0 + amount, so a -0.0 total still prints "-0.00".
    totals[key] = totals[key] + amount if key in totals else amount


def _money(amount):
    return f"{amount:.2f}"


def _region_cells(summary):
    return [(region.name, _money(region.revenue)) for region in summary.regions]


def _product_cells(summary):
    return [
        (product.name, str(product.units), _money(product.revenue))
        for product in summary.products
    ]


def _render_text(summary):
    lines = ["SALES REPORT", "=" * TEXT_RULE_WIDTH]
    lines += _text_section("Totals by region", TEXT_REGION_WIDTHS, _region_cells(summary))
    lines += _text_section("Totals by product", TEXT_PRODUCT_WIDTHS, _product_cells(summary))
    lines += [
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_money(summary.average_order_value)}",
    ]
    return "\n".join(lines) + "\n"


def _text_section(title, widths, rows):
    """A blank line, an underlined title, then the rows: first column left-aligned, the rest right-aligned."""
    lines = ["", title, "-" * TEXT_RULE_WIDTH]
    for first, *rest in rows:
        right_aligned = "".join(cell.rjust(width) for cell, width in zip(rest, widths[1:]))
        lines.append(first.ljust(widths[0]) + right_aligned)
    return lines


def _render_html(summary):
    lines = ["<html><body>", "<h1>Sales report</h1>"]
    lines += ["<h2>Totals by region</h2>", *_html_table(REGION_COLUMNS, _region_cells(summary))]
    lines += ["<h2>Totals by product</h2>", *_html_table(PRODUCT_COLUMNS, _product_cells(summary))]
    lines += [
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_money(summary.average_order_value)}</p>",
        "</body></html>",
    ]
    return "\n".join(lines) + "\n"


def _html_table(columns, rows):
    return ["<table>", _html_row("th", columns), *(_html_row("td", row) for row in rows), "</table>"]


def _html_row(tag, cells):
    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"


def _render_markdown(summary):
    blocks = [
        "# Sales report",
        "## Totals by region",
        _markdown_table(REGION_COLUMNS, _region_cells(summary)),
        "## Totals by product",
        _markdown_table(PRODUCT_COLUMNS, _product_cells(summary)),
        f"**Top product:** {summary.top_product}",
        f"**Average order value:** {_money(summary.average_order_value)}",
    ]
    return "\n\n".join(blocks) + "\n"


def _markdown_table(columns, rows):
    lines = [_markdown_row(columns), "|" + "|".join("---" for _ in columns) + "|"]
    lines += [_markdown_row(row) for row in rows]
    return "\n".join(lines)


def _markdown_row(cells):
    return "| " + " | ".join(cells) + " |"


_RENDERERS = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}

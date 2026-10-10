import csv
from dataclasses import dataclass


def generate(path, fmt):
    if fmt not in _RENDERERS:
        raise ValueError(f"unknown report format {fmt!r}, expected one of: {', '.join(_RENDERERS)}")
    summary = _summarize(_read_rows(path))
    return _RENDERERS[fmt](summary)


@dataclass(frozen=True)
class RegionTotal:
    region: str
    revenue: float


@dataclass(frozen=True)
class ProductTotal:
    product: str
    units: int
    revenue: float


@dataclass(frozen=True)
class SalesSummary:
    regions: list[RegionTotal]  # sorted by region
    products: list[ProductTotal]  # sorted by product
    top_product: str | None  # None when there are no sales; rendered as "None"
    average_order_value: float


def _read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _summarize(rows):
    # Printed totals depend on this exact accumulation: sum() rounds differently since Python 3.12,
    # and starting the per-key totals from 0 would print a lone -0.0 as "0.00" instead of "-0.00".
    revenue_by_region = {}
    revenue_by_product = {}
    units_by_product = {}
    total_revenue = 0
    for row in rows:
        units = int(row["units"])
        revenue = units * float(row["unit_price"])
        total_revenue += revenue
        _add_to_total(revenue_by_region, row["region"], revenue)
        _add_to_total(revenue_by_product, row["product"], revenue)
        _add_to_total(units_by_product, row["product"], units)

    return SalesSummary(
        regions=[RegionTotal(region, revenue_by_region[region]) for region in sorted(revenue_by_region)],
        products=[
            ProductTotal(product, units_by_product[product], revenue_by_product[product])
            for product in sorted(revenue_by_product)
        ],
        # max() keeps the first of equal values, so a tie goes to the product seen first in the file.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / len(rows) if rows else 0,
    )


def _add_to_total(totals, key, amount):
    totals[key] = totals[key] + amount if key in totals else amount


def _format_money(amount):
    return "%.2f" % amount


def _render_text(summary):
    lines = [
        "SALES REPORT",
        "=" * 40,
        "",
        "Totals by region",
        "-" * 40,
        *[total.region.ljust(20) + _format_money(total.revenue).rjust(20) for total in summary.regions],
        "",
        "Totals by product",
        "-" * 40,
        *[
            total.product.ljust(20) + str(total.units).rjust(8) + _format_money(total.revenue).rjust(12)
            for total in summary.products
        ],
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_format_money(summary.average_order_value)}",
    ]
    return "\n".join(lines) + "\n"


def _render_html(summary):
    lines = [
        "<html><body>",
        "<h1>Sales report</h1>",
        "<h2>Totals by region</h2>",
        "<table>",
        _html_row("th", ["Region", "Revenue"]),
        *[_html_row("td", [total.region, _format_money(total.revenue)]) for total in summary.regions],
        "</table>",
        "<h2>Totals by product</h2>",
        "<table>",
        _html_row("th", ["Product", "Units", "Revenue"]),
        *[
            _html_row("td", [total.product, str(total.units), _format_money(total.revenue)])
            for total in summary.products
        ],
        "</table>",
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
        "</body></html>",
    ]
    return "\n".join(lines) + "\n"


def _html_row(cell_tag, cells):
    opening, closing = f"<{cell_tag}>", f"</{cell_tag}>"
    return "<tr>" + "".join(opening + cell + closing for cell in cells) + "</tr>"


def _render_markdown(summary):
    blocks = [
        "# Sales report",
        "## Totals by region",
        _markdown_table(
            ["Region", "Revenue"],
            [[total.region, _format_money(total.revenue)] for total in summary.regions],
        ),
        "## Totals by product",
        _markdown_table(
            ["Product", "Units", "Revenue"],
            [[total.product, str(total.units), _format_money(total.revenue)] for total in summary.products],
        ),
        f"**Top product:** {summary.top_product}",
        f"**Average order value:** {_format_money(summary.average_order_value)}",
    ]
    return "\n\n".join(blocks) + "\n"


def _markdown_table(headers, rows):
    separator = "|" + "---|" * len(headers)
    return "\n".join([_markdown_row(headers), separator, *[_markdown_row(row) for row in rows]])


def _markdown_row(cells):
    return "| " + " | ".join(cells) + " |"


_RENDERERS = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}

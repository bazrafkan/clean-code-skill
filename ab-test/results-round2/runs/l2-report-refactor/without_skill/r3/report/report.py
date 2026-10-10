"""Sales report: read a CSV of sales, summarise it, render it in a chosen format.

The work is split into three independent steps:

1. ``read_sales``  -- parse the CSV into ``Sale`` records.
2. ``summarize``   -- compute every figure the report shows (``SalesSummary``).
3. a renderer      -- turn a ``SalesSummary`` into text for one output format.

To add an output format, write a ``render_<name>(summary) -> str`` function
and register it in ``RENDERERS``. Renderers only lay out values; they never
compute or re-sort them, so every format shows the same figures in the same
order.
"""

import csv
from collections.abc import Callable, Iterable
from dataclasses import dataclass


# --- Reading -----------------------------------------------------------------


@dataclass(frozen=True)
class Sale:
    region: str
    product: str
    units: int
    revenue: float


def read_sales(path) -> list[Sale]:
    with open(path) as f:
        return [_parse_sale(row) for row in csv.DictReader(f)]


def _parse_sale(row: dict[str, str]) -> Sale:
    units = int(row["units"])
    unit_price = float(row["unit_price"])
    return Sale(
        region=row["region"],
        product=row["product"],
        units=units,
        revenue=units * unit_price,
    )


# --- Summarising -------------------------------------------------------------


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
    regions: list[RegionTotal]  # sorted by region name
    products: list[ProductTotal]  # sorted by product name
    top_product: str | None  # None when there are no sales
    average_order_value: float


def summarize(sales: Iterable[Sale]) -> SalesSummary:
    revenue_by_region: dict[str, float] = {}
    revenue_by_product: dict[str, float] = {}
    units_by_product: dict[str, int] = {}
    order_count = 0
    total_revenue = 0
    for sale in sales:
        order_count += 1
        total_revenue += sale.revenue
        _accumulate(revenue_by_region, sale.region, sale.revenue)
        _accumulate(revenue_by_product, sale.product, sale.revenue)
        _accumulate(units_by_product, sale.product, sale.units)

    return SalesSummary(
        regions=[
            RegionTotal(region, revenue_by_region[region])
            for region in sorted(revenue_by_region)
        ],
        products=[
            ProductTotal(product, units_by_product[product], revenue_by_product[product])
            for product in sorted(revenue_by_product)
        ],
        # On a tie, max() keeps the product that appeared first in the file.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / order_count if order_count else 0,
    )


def _accumulate(totals: dict, key: str, amount) -> None:
    # The first amount is stored as-is rather than added to 0.0, so a lone
    # -0.0 revenue still prints as "-0.00", exactly as the report always has.
    totals[key] = totals[key] + amount if key in totals else amount


# --- Rendering ---------------------------------------------------------------


def _money(amount: float) -> str:
    return f"{amount:.2f}"


def _join_lines(lines: Iterable[str]) -> str:
    return "".join(line + "\n" for line in lines)


TEXT_WIDTH = 40


def render_text(summary: SalesSummary) -> str:
    lines = ["SALES REPORT", "=" * TEXT_WIDTH]

    lines += _text_heading("Totals by region")
    for row in summary.regions:
        lines.append(row.region.ljust(20) + _money(row.revenue).rjust(20))

    lines += _text_heading("Totals by product")
    for row in summary.products:
        lines.append(
            row.product.ljust(20) + str(row.units).rjust(8) + _money(row.revenue).rjust(12)
        )

    lines += [
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _text_heading(title: str) -> list[str]:
    return ["", title, "-" * TEXT_WIDTH]


def render_html(summary: SalesSummary) -> str:
    # Values are inserted unescaped, as the report always has.
    lines = ["<html><body>", "<h1>Sales report</h1>"]
    lines += _html_table("Totals by region", ["Region", "Revenue"], _region_cells(summary))
    lines += _html_table(
        "Totals by product", ["Product", "Units", "Revenue"], _product_cells(summary)
    )
    lines += [
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_money(summary.average_order_value)}</p>",
        "</body></html>",
    ]
    return _join_lines(lines)


def _html_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        f"<h2>{title}</h2>",
        "<table>",
        _html_row("th", headers),
        *(_html_row("td", cells) for cells in rows),
        "</table>",
    ]


def _html_row(tag: str, cells: list[str]) -> str:
    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"


def render_markdown(summary: SalesSummary) -> str:
    lines = ["# Sales report", ""]
    lines += _markdown_table("Totals by region", ["Region", "Revenue"], _region_cells(summary))
    lines += [""]
    lines += _markdown_table(
        "Totals by product", ["Product", "Units", "Revenue"], _product_cells(summary)
    )
    lines += [
        "",
        f"**Top product:** {summary.top_product}",
        "",
        f"**Average order value:** {_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _markdown_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        f"## {title}",
        "",
        _markdown_row(headers),
        "|" + "|".join("---" for _ in headers) + "|",
        *(_markdown_row(cells) for cells in rows),
    ]


def _markdown_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _region_cells(summary: SalesSummary) -> list[list[str]]:
    return [[row.region, _money(row.revenue)] for row in summary.regions]


def _product_cells(summary: SalesSummary) -> list[list[str]]:
    return [[row.product, str(row.units), _money(row.revenue)] for row in summary.products]


# --- Entry point -------------------------------------------------------------


RENDERERS: dict[str, Callable[[SalesSummary], str]] = {
    "text": render_text,
    "html": render_html,
    "md": render_markdown,
}


def generate(path, fmt):
    """Return the sales report for the CSV file at ``path`` in format ``fmt``.

    ``fmt`` is one of the keys of ``RENDERERS``; anything else raises ValueError.
    """
    try:
        render = RENDERERS[fmt]
    except KeyError:
        raise ValueError(
            f"bad format {fmt!r}; expected one of: {', '.join(sorted(RENDERERS))}"
        ) from None
    return render(summarize(read_sales(path)))

"""Sales report built from a CSV file of orders.

A report is produced in two steps: the orders are summarised into a
``SalesSummary``, then the renderer registered for the requested format lays
the summary out. To support another format, write a function that takes a
``SalesSummary`` and returns the report as a string, and add it to
``_RENDERERS`` at the bottom of this module.
"""

from __future__ import annotations

import csv
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple


class RegionTotal(NamedTuple):
    region: str
    revenue: float


class ProductTotal(NamedTuple):
    product: str
    units: int
    revenue: float


@dataclass(frozen=True)
class SalesSummary:
    """The figures shown in a report, independent of the output format."""

    regions: list[RegionTotal]  # sorted by region name
    products: list[ProductTotal]  # sorted by product name
    top_product: str | None  # highest revenue; None when there are no orders
    average_order_value: float


def generate(path: str | os.PathLike[str], fmt: str) -> str:
    """Return the sales report for the orders CSV at ``path``.

    ``fmt`` is the output format: "text", "html" or "md". Any other format
    name raises ``ValueError``.
    """
    render = _RENDERERS.get(fmt)
    if render is None:
        supported = ", ".join(sorted(_RENDERERS))
        raise ValueError(f"bad format {fmt!r}; expected one of: {supported}")
    return render(_summarize(_read_orders(path)))


def _read_orders(path: str | os.PathLike[str]) -> list[dict[str, str]]:
    # The default newline handling and encoding are deliberate: changing them
    # changes how some field values are read, and so the report output.
    with open(path) as orders_file:
        return list(csv.DictReader(orders_file))


def _summarize(orders: list[dict[str, str]]) -> SalesSummary:
    revenue_by_region: dict[str, float] = {}
    revenue_by_product: dict[str, float] = {}
    units_by_product: dict[str, int] = {}
    total_revenue = 0.0
    for order in orders:
        units = int(order["units"])
        revenue = units * float(order["unit_price"])
        total_revenue += revenue
        _add_to(revenue_by_region, order["region"], revenue)
        _add_to(revenue_by_product, order["product"], revenue)
        _add_to(units_by_product, order["product"], units)

    return SalesSummary(
        regions=[
            RegionTotal(region, revenue_by_region[region])
            for region in sorted(revenue_by_region)
        ],
        products=[
            ProductTotal(product, units_by_product[product], revenue_by_product[product])
            for product in sorted(revenue_by_product)
        ],
        # max() keeps the first of equal values: ties go to the product seen first.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / len(orders) if orders else 0.0,
    )


def _add_to(totals: dict, key: str, amount: float) -> None:
    # Start from the first amount rather than from 0: 0 + -0.0 is 0.0, which
    # would print as "0.00" instead of "-0.00".
    if key in totals:
        totals[key] += amount
    else:
        totals[key] = amount


def _render_text(summary: SalesSummary) -> str:
    lines = ["SALES REPORT", "=" * 40]
    lines += ["", "Totals by region", "-" * 40]
    lines += [
        f"{row.region:<20}{_format_money(row.revenue):>20}" for row in summary.regions
    ]
    lines += ["", "Totals by product", "-" * 40]
    lines += [
        f"{row.product:<20}{row.units:>8}{_format_money(row.revenue):>12}"
        for row in summary.products
    ]
    lines += [
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_format_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _render_html(summary: SalesSummary) -> str:
    lines = ["<html><body>", "<h1>Sales report</h1>"]
    lines += ["<h2>Totals by region</h2>"]
    lines += _html_table(
        ["Region", "Revenue"],
        [[row.region, _format_money(row.revenue)] for row in summary.regions],
    )
    lines += ["<h2>Totals by product</h2>"]
    lines += _html_table(
        ["Product", "Units", "Revenue"],
        [
            [row.product, str(row.units), _format_money(row.revenue)]
            for row in summary.products
        ],
    )
    lines += [
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
        "</body></html>",
    ]
    return _join_lines(lines)


def _html_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "<table>",
        _html_row("th", headers),
        *(_html_row("td", row) for row in rows),
        "</table>",
    ]


def _html_row(cell_tag: str, cells: list[str]) -> str:
    open_tag, close_tag = f"<{cell_tag}>", f"</{cell_tag}>"
    return "<tr>" + "".join(open_tag + cell + close_tag for cell in cells) + "</tr>"


def _render_markdown(summary: SalesSummary) -> str:
    lines = ["# Sales report"]
    lines += ["", "## Totals by region", ""]
    lines += _markdown_table(
        ["Region", "Revenue"],
        [[row.region, _format_money(row.revenue)] for row in summary.regions],
    )
    lines += ["", "## Totals by product", ""]
    lines += _markdown_table(
        ["Product", "Units", "Revenue"],
        [
            [row.product, str(row.units), _format_money(row.revenue)]
            for row in summary.products
        ],
    )
    lines += [
        "",
        f"**Top product:** {summary.top_product}",
        "",
        f"**Average order value:** {_format_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    return [
        _markdown_row(headers),
        "|" + "---|" * len(headers),
        *(_markdown_row(row) for row in rows),
    ]


def _markdown_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _format_money(amount: float) -> str:
    return f"{amount:.2f}"


def _join_lines(lines: list[str]) -> str:
    """Join ``lines`` into a document in which every line ends with a newline."""
    return "".join(line + "\n" for line in lines)


_RENDERERS: dict[str, Callable[[SalesSummary], str]] = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}

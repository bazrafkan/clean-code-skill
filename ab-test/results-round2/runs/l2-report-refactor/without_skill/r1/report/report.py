"""Sales report generation.

A report is built in two independent steps:

1. ``summarize`` turns the CSV rows into a format-neutral ``SalesSummary``.
2. A renderer turns that summary into a string. Renderers are registered in
   ``RENDERERS`` under their format name.

To add a format, write a ``render_<name>(summary) -> str`` function and register
it in ``RENDERERS``. Build table rows with ``_region_rows`` / ``_product_rows`` so
every format shows the same values in the same order.
"""

from __future__ import annotations

import csv
import os
from typing import Callable, Mapping, NamedTuple, Sequence

TITLE = "Sales report"
REGION_HEADING = "Totals by region"
REGION_COLUMNS = ("Region", "Revenue")
PRODUCT_HEADING = "Totals by product"
PRODUCT_COLUMNS = ("Product", "Units", "Revenue")
TOP_PRODUCT_LABEL = "Top product"
AVERAGE_ORDER_LABEL = "Average order value"


class RegionTotal(NamedTuple):
    region: str
    revenue: float


class ProductTotal(NamedTuple):
    product: str
    units: int
    revenue: float


class SalesSummary(NamedTuple):
    regions: list[RegionTotal]  # sorted by region name
    products: list[ProductTotal]  # sorted by product name
    top_product: str | None  # highest revenue; on a tie, the first one in the file
    average_order_value: float


def generate(path: str | os.PathLike, fmt: str) -> str:
    """Return the sales report for the CSV at ``path`` in format ``fmt``.

    Raises ``ValueError`` if ``fmt`` is not a key of ``RENDERERS``.
    """
    render = _renderer_for(fmt)
    return render(summarize(_read_rows(path)))


# --- Data -------------------------------------------------------------------


def _read_rows(path: str | os.PathLike) -> list[dict[str, str]]:
    # open() keeps its default newline/encoding handling on purpose: changing it
    # would change how some files are parsed, and with it the report output.
    with open(path) as f:
        return list(csv.DictReader(f))


def summarize(rows: Sequence[Mapping[str, str]]) -> SalesSummary:
    revenue_by_region: dict[str, float] = {}
    revenue_by_product: dict[str, float] = {}
    units_by_product: dict[str, int] = {}
    # A running total in file order, not sum(): since Python 3.12 sum() rounds
    # floats differently, which could change the last printed digit.
    total_revenue = 0
    for row in rows:
        units = int(row["units"])
        revenue = units * float(row["unit_price"])
        total_revenue += revenue
        _add(revenue_by_region, row["region"], revenue)
        _add(revenue_by_product, row["product"], revenue)
        _add(units_by_product, row["product"], units)

    return SalesSummary(
        regions=[
            RegionTotal(region, revenue_by_region[region])
            for region in sorted(revenue_by_region)
        ],
        products=[
            ProductTotal(product, units_by_product[product], revenue_by_product[product])
            for product in sorted(revenue_by_product)
        ],
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / len(rows) if rows else 0,
    )


def _add(totals: dict, key: str, amount: float) -> None:
    # Start from the first amount rather than from 0, so a total of -0.0 still
    # prints as "-0.00".
    totals[key] = totals[key] + amount if key in totals else amount


# --- Formats ----------------------------------------------------------------


def render_text(summary: SalesSummary) -> str:
    return _join_lines([
        TITLE.upper(),
        "=" * 40,
        "",
        REGION_HEADING,
        "-" * 40,
        *(_text_row(cells, widths=(20, 20)) for cells in _region_rows(summary)),
        "",
        PRODUCT_HEADING,
        "-" * 40,
        *(_text_row(cells, widths=(20, 8, 12)) for cells in _product_rows(summary)),
        "",
        f"{TOP_PRODUCT_LABEL}: {summary.top_product}",
        f"{AVERAGE_ORDER_LABEL}: {_money(summary.average_order_value)}",
    ])


def render_html(summary: SalesSummary) -> str:
    return _join_lines([
        "<html><body>",
        f"<h1>{TITLE}</h1>",
        f"<h2>{REGION_HEADING}</h2>",
        *_html_table(REGION_COLUMNS, _region_rows(summary)),
        f"<h2>{PRODUCT_HEADING}</h2>",
        *_html_table(PRODUCT_COLUMNS, _product_rows(summary)),
        f"<p>{TOP_PRODUCT_LABEL}: {summary.top_product}</p>",
        f"<p>{AVERAGE_ORDER_LABEL}: {_money(summary.average_order_value)}</p>",
        "</body></html>",
    ])


def render_markdown(summary: SalesSummary) -> str:
    return _join_lines([
        f"# {TITLE}",
        "",
        f"## {REGION_HEADING}",
        "",
        *_markdown_table(REGION_COLUMNS, _region_rows(summary)),
        "",
        f"## {PRODUCT_HEADING}",
        "",
        *_markdown_table(PRODUCT_COLUMNS, _product_rows(summary)),
        "",
        f"**{TOP_PRODUCT_LABEL}:** {summary.top_product}",
        "",
        f"**{AVERAGE_ORDER_LABEL}:** {_money(summary.average_order_value)}",
    ])


Renderer = Callable[[SalesSummary], str]

RENDERERS: dict[str, Renderer] = {
    "text": render_text,
    "html": render_html,
    "md": render_markdown,
}


def _renderer_for(fmt: str) -> Renderer:
    try:
        return RENDERERS[fmt]
    except KeyError:
        known = ", ".join(repr(name) for name in RENDERERS)
        raise ValueError(f"unknown format {fmt!r}; expected one of {known}") from None


# --- Helpers shared by the formats -------------------------------------------


def _money(amount: float) -> str:
    return "%.2f" % amount


def _region_rows(summary: SalesSummary) -> list[tuple[str, ...]]:
    return [(t.region, _money(t.revenue)) for t in summary.regions]


def _product_rows(summary: SalesSummary) -> list[tuple[str, ...]]:
    return [(t.product, str(t.units), _money(t.revenue)) for t in summary.products]


def _join_lines(lines: Sequence[str]) -> str:
    return "".join(line + "\n" for line in lines)


def _text_row(cells: Sequence[str], widths: Sequence[int]) -> str:
    """Pad each cell to its width: the first left-aligned, the rest right-aligned."""
    first, *rest = cells
    first_width, *rest_widths = widths
    return first.ljust(first_width) + "".join(
        cell.rjust(width) for cell, width in zip(rest, rest_widths)
    )


def _html_table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    return [
        "<table>",
        _html_row("th", columns),
        *(_html_row("td", cells) for cells in rows),
        "</table>",
    ]


def _html_row(tag: str, cells: Sequence[str]) -> str:
    open_tag, close_tag = f"<{tag}>", f"</{tag}>"
    return "<tr>" + "".join(open_tag + cell + close_tag for cell in cells) + "</tr>"


def _markdown_table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    return [
        _markdown_row(columns),
        "|" + "---|" * len(columns),
        *(_markdown_row(cells) for cells in rows),
    ]


def _markdown_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cells) + " |"

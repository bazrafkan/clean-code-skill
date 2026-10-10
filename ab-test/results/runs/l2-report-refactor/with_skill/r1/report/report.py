"""Sales report: revenue by region and by product, rendered in a chosen format.

To add a format, write a `_render_<name>(summary) -> str` function and register
it in `_RENDERERS`.
"""

import csv
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar


def generate(path: str | os.PathLike[str], fmt: str) -> str:
    """Return the sales report for the orders CSV at `path`, rendered as `fmt`.

    Supported formats are "text", "html" and "md". Raises ValueError for any
    other format, before the file is read.
    """
    render = _renderer_for(fmt)
    return render(_summarize(_read_orders(path)))


@dataclass(frozen=True)
class _Order:
    region: str
    product: str
    units: int
    # Binary float on purpose: the text and HTML output rely on its rounding.
    revenue: float


def _read_orders(path: str | os.PathLike[str]) -> list[_Order]:
    # No newline="": universal newlines normalize line breaks inside quoted
    # fields, and the report output depends on that.
    with open(path) as file:
        rows = list(csv.DictReader(file))
    return [_parse_order(row) for row in rows]


def _parse_order(row: dict[str, str | None]) -> _Order:
    units = int(_required(row, "units"))
    revenue = units * float(_required(row, "unit_price"))
    return _Order(
        region=_required(row, "region"),
        product=_required(row, "product"),
        units=units,
        revenue=revenue,
    )


def _required(row: dict[str, str | None], column: str) -> str:
    value = row[column]
    if value is None:
        raise ValueError(f"order row has no {column!r} value (row too short): {row}")
    return value


@dataclass(frozen=True)
class _RegionTotal:
    region: str
    revenue: float


@dataclass(frozen=True)
class _ProductTotal:
    product: str
    units: int
    revenue: float


@dataclass(frozen=True)
class _SalesSummary:
    regions: tuple[_RegionTotal, ...]  # sorted by region
    products: tuple[_ProductTotal, ...]  # sorted by product
    top_product: str | None  # None when there are no orders
    average_order_value: float


def _summarize(orders: list[_Order]) -> _SalesSummary:
    revenue_by_region = _total_by(
        orders, key=lambda order: order.region, amount=lambda order: order.revenue
    )
    revenue_by_product = _total_by(
        orders, key=lambda order: order.product, amount=lambda order: order.revenue
    )
    units_by_product = _total_by(
        orders, key=lambda order: order.product, amount=lambda order: order.units
    )
    return _SalesSummary(
        regions=tuple(
            _RegionTotal(region, revenue_by_region[region])
            for region in sorted(revenue_by_region)
        ),
        products=tuple(
            _ProductTotal(
                product, units_by_product[product], revenue_by_product[product]
            )
            for product in sorted(revenue_by_product)
        ),
        top_product=_top_product(revenue_by_product),
        average_order_value=_average_order_value(orders),
    )


_Amount = TypeVar("_Amount", int, float)


def _total_by(
    orders: Iterable[_Order],
    key: Callable[[_Order], str],
    amount: Callable[[_Order], _Amount],
) -> dict[str, _Amount]:
    """Total `amount` per `key`, adding in file order; keys keep first-seen order."""
    totals: dict[str, _Amount] = {}
    for order in orders:
        group, value = key(order), amount(order)
        # Seeded with the first value rather than 0, so a group whose only
        # revenue is -0.0 still prints "-0.00".
        totals[group] = totals[group] + value if group in totals else value
    return totals


def _top_product(revenue_by_product: dict[str, float]) -> str | None:
    """Highest-revenue product; a tie goes to the product that appears first."""
    return max(
        revenue_by_product,
        key=lambda product: revenue_by_product[product],
        default=None,
    )


def _average_order_value(orders: list[_Order]) -> float:
    if not orders:
        return 0.0
    # A plain loop, not sum(): since Python 3.12 sum() compensates float
    # rounding, which can shift the printed cents.
    total = 0.0
    for order in orders:
        total += order.revenue
    return total / len(orders)


_REPORT_TITLE = "Sales report"
_NO_TOP_PRODUCT = "None"


@dataclass(frozen=True)
class _Table:
    heading: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


def _region_table(summary: _SalesSummary) -> _Table:
    return _Table(
        heading="Totals by region",
        columns=("Region", "Revenue"),
        rows=tuple((total.region, _money(total.revenue)) for total in summary.regions),
    )


def _product_table(summary: _SalesSummary) -> _Table:
    return _Table(
        heading="Totals by product",
        columns=("Product", "Units", "Revenue"),
        rows=tuple(
            (total.product, str(total.units), _money(total.revenue))
            for total in summary.products
        ),
    )


def _highlights(summary: _SalesSummary) -> tuple[tuple[str, str], ...]:
    """The (label, value) lines that close every report."""
    top_product = summary.top_product
    return (
        ("Top product", _NO_TOP_PRODUCT if top_product is None else top_product),
        ("Average order value", _money(summary.average_order_value)),
    )


def _money(amount: float) -> str:
    return f"{amount:.2f}"


_TEXT_RULE_WIDTH = 40
_TEXT_REGION_COLUMN_WIDTHS = (20, 20)
_TEXT_PRODUCT_COLUMN_WIDTHS = (20, 8, 12)


def _render_text(summary: _SalesSummary) -> str:
    lines = [
        _REPORT_TITLE.upper(),
        "=" * _TEXT_RULE_WIDTH,
        *_text_table(_region_table(summary), _TEXT_REGION_COLUMN_WIDTHS),
        *_text_table(_product_table(summary), _TEXT_PRODUCT_COLUMN_WIDTHS),
        "",
        *(f"{label}: {value}" for label, value in _highlights(summary)),
    ]
    return "\n".join(lines) + "\n"


def _text_table(table: _Table, column_widths: tuple[int, ...]) -> list[str]:
    rows = [_text_row(row, column_widths) for row in table.rows]
    return ["", table.heading, "-" * _TEXT_RULE_WIDTH, *rows]


def _text_row(cells: tuple[str, ...], column_widths: tuple[int, ...]) -> str:
    """Left-align the name in the first column, right-align the figures after it."""
    name, *figures = cells
    name_width, *figure_widths = column_widths
    aligned_figures = (
        figure.rjust(width)
        for figure, width in zip(figures, figure_widths, strict=True)
    )
    return name.ljust(name_width) + "".join(aligned_figures)


def _render_html(summary: _SalesSummary) -> str:
    lines = [
        "<html><body>",
        f"<h1>{_REPORT_TITLE}</h1>",
        *_html_table(_region_table(summary)),
        *_html_table(_product_table(summary)),
        *(f"<p>{label}: {value}</p>" for label, value in _highlights(summary)),
        "</body></html>",
    ]
    return "\n".join(lines) + "\n"


def _html_table(table: _Table) -> list[str]:
    return [
        f"<h2>{table.heading}</h2>",
        "<table>",
        _html_row("th", table.columns),
        *(_html_row("td", row) for row in table.rows),
        "</table>",
    ]


def _html_row(cell_tag: str, cells: tuple[str, ...]) -> str:
    # Warning: cells are not HTML-escaped, so names containing markup leak
    # into the page. Escaping would change the established HTML output.
    return (
        "<tr>" + "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells) + "</tr>"
    )


def _render_markdown(summary: _SalesSummary) -> str:
    blocks = [
        f"# {_REPORT_TITLE}",
        *_markdown_table(_region_table(summary)),
        *_markdown_table(_product_table(summary)),
        *(f"**{label}:** {value}" for label, value in _highlights(summary)),
    ]
    return "\n\n".join(blocks) + "\n"


def _markdown_table(table: _Table) -> list[str]:
    """The heading block and the pipe-table block for `table`."""
    header = _markdown_row(table.columns)
    delimiter = "|" + "---|" * len(table.columns)
    rows = [_markdown_row(row) for row in table.rows]
    return [f"## {table.heading}", "\n".join([header, delimiter, *rows])]


def _markdown_row(cells: tuple[str, ...]) -> str:
    return "| " + " | ".join(cells) + " |"


_RENDERERS: dict[str, Callable[[_SalesSummary], str]] = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}


def _renderer_for(fmt: str) -> Callable[[_SalesSummary], str]:
    if fmt not in _RENDERERS:
        supported = ", ".join(_RENDERERS)
        raise ValueError(f"bad format {fmt!r}: expected one of {supported}")
    return _RENDERERS[fmt]

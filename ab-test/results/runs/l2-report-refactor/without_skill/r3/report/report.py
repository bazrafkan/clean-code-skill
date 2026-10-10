"""Sales report built from a CSV of orders, rendered as text, HTML or Markdown.

The work happens in three steps, so each can change on its own:

1. ``_summarize`` computes the figures from the CSV rows (``SalesSummary``).
2. ``_build_content`` turns the figures into format-neutral content: a title,
   tables of already-formatted cells, and labelled facts (``ReportContent``).
   Labels, number formatting and row order are decided here, once, for every
   format.
3. A renderer lays that content out in one output format.

To add a format, write a ``_render_<name>(content) -> str`` function and add it
to ``_RENDERERS``.
"""

import csv
from collections.abc import Callable, Iterable
from dataclasses import dataclass

TITLE = "Sales report"
TEXT_WIDTH = 40


@dataclass(frozen=True)
class SalesSummary:
    revenue_by_region: dict[str, float]
    units_by_product: dict[str, int]
    revenue_by_product: dict[str, float]
    top_product: str | None
    average_order_value: float


@dataclass(frozen=True)
class Column:
    header: str
    text_width: int  # characters this column takes in the plain-text layout


@dataclass(frozen=True)
class Table:
    heading: str
    columns: tuple[Column, ...]
    rows: list[tuple[str, ...]]


@dataclass(frozen=True)
class ReportContent:
    title: str
    tables: list[Table]
    facts: list[tuple[str, str]]  # (label, value) pairs


def generate(path, fmt):
    """Return the sales report for the orders CSV at ``path``.

    ``fmt`` is one of the keys of ``_RENDERERS`` ("text", "html" or "md");
    any other value raises ``ValueError`` before the file is read.
    """
    render = _renderer_for(fmt)
    return render(_build_content(_summarize(_read_rows(path))))


def _read_rows(path: str) -> list[dict[str, str]]:
    with open(path) as f:
        return list(csv.DictReader(f))


def _summarize(rows: list[dict[str, str]]) -> SalesSummary:
    revenue_by_region: dict[str, float] = {}
    revenue_by_product: dict[str, float] = {}
    units_by_product: dict[str, int] = {}
    total_revenue = 0.0
    for row in rows:
        units = int(row["units"])
        revenue = units * float(row["unit_price"])
        # Plain left-to-right addition on purpose: sum() uses compensated
        # summation since Python 3.12, which could change the rounded output.
        total_revenue += revenue
        _add(revenue_by_region, row["region"], revenue)
        _add(revenue_by_product, row["product"], revenue)
        _add(units_by_product, row["product"], units)

    return SalesSummary(
        revenue_by_region=revenue_by_region,
        units_by_product=units_by_product,
        revenue_by_product=revenue_by_product,
        # max() keeps the first product seen when revenues tie.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / len(rows) if rows else 0.0,
    )


def _add(totals: dict, key: str, amount: float) -> None:
    # Start from the first amount rather than from 0: 0 + -0.0 is 0.0, which
    # would print a total of -0.0 as "0.00" instead of "-0.00".
    totals[key] = totals[key] + amount if key in totals else amount


def _build_content(summary: SalesSummary) -> ReportContent:
    regions = Table(
        heading="Totals by region",
        columns=(Column("Region", 20), Column("Revenue", 20)),
        rows=[
            (region, _money(summary.revenue_by_region[region]))
            for region in sorted(summary.revenue_by_region)
        ],
    )
    products = Table(
        heading="Totals by product",
        columns=(Column("Product", 20), Column("Units", 8), Column("Revenue", 12)),
        rows=[
            (
                product,
                str(summary.units_by_product[product]),
                _money(summary.revenue_by_product[product]),
            )
            for product in sorted(summary.revenue_by_product)
        ],
    )
    facts = [
        ("Top product", str(summary.top_product)),
        ("Average order value", _money(summary.average_order_value)),
    ]
    return ReportContent(title=TITLE, tables=[regions, products], facts=facts)


def _money(amount: float) -> str:
    return f"{amount:.2f}"


# --- Renderers: each lays out a ReportContent in one format. ---------------


def _render_text(content: ReportContent) -> str:
    banner = content.title.upper() + "\n" + "=" * TEXT_WIDTH
    facts = "\n".join(f"{label}: {value}" for label, value in content.facts)
    blocks = [banner, *map(_text_table, content.tables), facts]
    return "\n\n".join(blocks) + "\n"


def _text_table(table: Table) -> str:
    # Headers are not shown; the first column is left-aligned, the rest right-aligned.
    widths = [column.text_width for column in table.columns]
    lines = [table.heading, "-" * TEXT_WIDTH]
    for first, *rest in table.rows:
        cells = [first.ljust(widths[0])]
        cells += [cell.rjust(width) for cell, width in zip(rest, widths[1:])]
        lines.append("".join(cells))
    return "\n".join(lines)


def _render_html(content: ReportContent) -> str:
    lines = ["<html><body>", f"<h1>{content.title}</h1>"]
    for table in content.tables:
        lines.append(f"<h2>{table.heading}</h2>")
        lines += _html_table(table)
    lines += [f"<p>{label}: {value}</p>" for label, value in content.facts]
    lines.append("</body></html>")
    return "\n".join(lines) + "\n"


def _html_table(table: Table) -> list[str]:
    return [
        "<table>",
        _html_row("th", [column.header for column in table.columns]),
        *(_html_row("td", row) for row in table.rows),
        "</table>",
    ]


def _html_row(tag: str, cells: Iterable[str]) -> str:
    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"


def _render_markdown(content: ReportContent) -> str:
    blocks = [f"# {content.title}"]
    for table in content.tables:
        blocks += [f"## {table.heading}", _markdown_table(table)]
    blocks += [f"**{label}:** {value}" for label, value in content.facts]
    return "\n\n".join(blocks) + "\n"


def _markdown_table(table: Table) -> str:
    lines = [
        _markdown_row([column.header for column in table.columns]),
        "|" + "---|" * len(table.columns),
    ]
    lines += [_markdown_row(row) for row in table.rows]
    return "\n".join(lines)


def _markdown_row(cells: Iterable[str]) -> str:
    return "| " + " | ".join(cells) + " |"


Renderer = Callable[[ReportContent], str]

_RENDERERS: dict[str, Renderer] = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}


def _renderer_for(fmt: str) -> Renderer:
    try:
        return _RENDERERS[fmt]
    except KeyError:
        expected = ", ".join(_RENDERERS)
        raise ValueError(f"bad format {fmt!r}; expected one of: {expected}") from None

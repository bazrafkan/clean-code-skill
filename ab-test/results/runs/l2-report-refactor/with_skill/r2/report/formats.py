"""Output formats of the sales report.

Each renderer turns a SalesSummary into the complete report in one format.
To support another format, write a renderer and add it to _RENDERERS.
"""

from collections.abc import Callable
from typing import NamedTuple

from .summary import SalesSummary

Renderer = Callable[[SalesSummary], str]

_TITLE = "Sales report"
_NO_TOP_PRODUCT = "None"  # what the report has always shown when there are no sales

_TEXT_LINE_WIDTH = 40
_TEXT_REGION_COLUMN_WIDTHS = (20, 20)
_TEXT_PRODUCT_COLUMN_WIDTHS = (20, 8, 12)


class _Table(NamedTuple):
    title: str
    columns: tuple[str, ...]
    rows: list[tuple[str, ...]]


def renderer_for(fmt: str) -> Renderer:
    if fmt not in _RENDERERS:
        supported = ", ".join(sorted(_RENDERERS))
        raise ValueError(f"unknown report format {fmt!r} (supported: {supported})")
    return _RENDERERS[fmt]


def _render_text(summary: SalesSummary) -> str:
    lines = [_TITLE.upper(), "=" * _TEXT_LINE_WIDTH]
    lines += _text_section(_region_table(summary), _TEXT_REGION_COLUMN_WIDTHS)
    lines += _text_section(_product_table(summary), _TEXT_PRODUCT_COLUMN_WIDTHS)
    lines.append("")
    lines += [f"{label}: {value}" for label, value in _key_figures(summary)]
    return _join_lines(lines)


def _text_section(table: _Table, column_widths: tuple[int, ...]) -> list[str]:
    lines = ["", table.title, "-" * _TEXT_LINE_WIDTH]
    lines += [_text_row(row, column_widths) for row in table.rows]
    return lines


def _text_row(cells: tuple[str, ...], column_widths: tuple[int, ...]) -> str:
    name, *figures = cells
    name_width, *figure_widths = column_widths
    aligned_figures = (
        figure.rjust(width)
        for figure, width in zip(figures, figure_widths, strict=True)
    )
    return name.ljust(name_width) + "".join(aligned_figures)


def _render_html(summary: SalesSummary) -> str:
    lines = ["<html><body>", f"<h1>{_TITLE}</h1>"]
    lines += _html_section(_region_table(summary))
    lines += _html_section(_product_table(summary))
    lines += [f"<p>{label}: {value}</p>" for label, value in _key_figures(summary)]
    lines.append("</body></html>")
    return _join_lines(lines)


def _html_section(table: _Table) -> list[str]:
    return [
        f"<h2>{table.title}</h2>",
        "<table>",
        _html_row("th", table.columns),
        *(_html_row("td", row) for row in table.rows),
        "</table>",
    ]


def _html_row(cell_tag: str, cells: tuple[str, ...]) -> str:
    # Cells are not HTML-escaped; escaping would change the existing output.
    tagged_cells = "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells)
    return f"<tr>{tagged_cells}</tr>"


def _render_markdown(summary: SalesSummary) -> str:
    blocks = [f"# {_TITLE}"]
    blocks += _markdown_section(_region_table(summary))
    blocks += _markdown_section(_product_table(summary))
    blocks += [f"**{label}:** {value}" for label, value in _key_figures(summary)]
    return "\n\n".join(blocks) + "\n"


def _markdown_section(table: _Table) -> list[str]:
    table_lines = [
        _markdown_row(table.columns),
        "|" + "---|" * len(table.columns),
        *(_markdown_row(row) for row in table.rows),
    ]
    return [f"## {table.title}", "\n".join(table_lines)]


def _markdown_row(cells: tuple[str, ...]) -> str:
    return "| " + " | ".join(cells) + " |"


_RENDERERS: dict[str, Renderer] = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}


def _region_table(summary: SalesSummary) -> _Table:
    return _Table(
        title="Totals by region",
        columns=("Region", "Revenue"),
        rows=[
            (region.name, _format_money(region.revenue)) for region in summary.regions
        ],
    )


def _product_table(summary: SalesSummary) -> _Table:
    return _Table(
        title="Totals by product",
        columns=("Product", "Units", "Revenue"),
        rows=[
            (product.name, str(product.units), _format_money(product.revenue))
            for product in summary.products
        ],
    )


def _key_figures(summary: SalesSummary) -> list[tuple[str, str]]:
    top_product = (
        _NO_TOP_PRODUCT if summary.top_product is None else summary.top_product
    )
    return [
        ("Top product", top_product),
        ("Average order value", _format_money(summary.average_order_value)),
    ]


def _format_money(amount: float) -> str:
    return f"{amount:.2f}"


def _join_lines(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)

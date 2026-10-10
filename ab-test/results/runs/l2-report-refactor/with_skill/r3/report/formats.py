"""Output formats for the sales report.

Each format is a function that renders a SalesSummary to a string. To add a
format, write its render function and register it in _RENDERERS at the bottom.
Warning: values go into HTML and Markdown unescaped, so a name containing
"<" or "|" breaks the markup.
"""

from collections.abc import Callable

from .sales import SalesSummary

Renderer = Callable[[SalesSummary], str]
_Row = tuple[str, ...]

_REGION_COLUMNS = ("Region", "Revenue")
_PRODUCT_COLUMNS = ("Product", "Units", "Revenue")


def renderer_for(fmt: str) -> Renderer:
    if fmt not in _RENDERERS:
        supported = ", ".join(sorted(_RENDERERS))
        raise ValueError(f"bad format {fmt!r}; supported formats: {supported}")
    return _RENDERERS[fmt]


_TEXT_LINE_WIDTH = 40
_TEXT_NAME_WIDTH = 20
_TEXT_UNITS_WIDTH = 8
_TEXT_REGION_WIDTHS = (_TEXT_NAME_WIDTH, _TEXT_LINE_WIDTH - _TEXT_NAME_WIDTH)
_TEXT_PRODUCT_WIDTHS = (
    _TEXT_NAME_WIDTH,
    _TEXT_UNITS_WIDTH,
    _TEXT_LINE_WIDTH - _TEXT_NAME_WIDTH - _TEXT_UNITS_WIDTH,
)


def _render_text(summary: SalesSummary) -> str:
    lines = ["SALES REPORT", "=" * _TEXT_LINE_WIDTH]
    lines += _text_section(
        "Totals by region", _region_rows(summary), _TEXT_REGION_WIDTHS
    )
    lines += _text_section(
        "Totals by product", _product_rows(summary), _TEXT_PRODUCT_WIDTHS
    )
    lines += [
        "",
        "Top product: " + _top_product_name(summary),
        "Average order value: " + _money(summary.average_order_value),
    ]
    return _end_each_line(lines)


def _text_section(
    title: str, rows: list[_Row], column_widths: tuple[int, ...]
) -> list[str]:
    return [
        "",
        title,
        "-" * _TEXT_LINE_WIDTH,
        *(_text_row(cells, column_widths) for cells in rows),
    ]


def _text_row(cells: _Row, column_widths: tuple[int, ...]) -> str:
    name, *figures = cells
    name_width, *figure_widths = column_widths
    aligned_figures = (
        figure.rjust(width)
        for figure, width in zip(figures, figure_widths, strict=True)
    )
    return name.ljust(name_width) + "".join(aligned_figures)


def _render_html(summary: SalesSummary) -> str:
    lines = ["<html><body>", "<h1>Sales report</h1>"]
    lines += _html_section("Totals by region", _REGION_COLUMNS, _region_rows(summary))
    lines += _html_section(
        "Totals by product", _PRODUCT_COLUMNS, _product_rows(summary)
    )
    lines += [
        "<p>Top product: " + _top_product_name(summary) + "</p>",
        "<p>Average order value: " + _money(summary.average_order_value) + "</p>",
        "</body></html>",
    ]
    return _end_each_line(lines)


def _html_section(heading: str, column_names: _Row, rows: list[_Row]) -> list[str]:
    return [
        "<h2>" + heading + "</h2>",
        "<table>",
        _html_row("th", column_names),
        *(_html_row("td", cells) for cells in rows),
        "</table>",
    ]


def _html_row(cell_tag: str, cells: _Row) -> str:
    cells_html = "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells)
    return "<tr>" + cells_html + "</tr>"


def _render_markdown(summary: SalesSummary) -> str:
    blocks = [
        "# Sales report",
        "## Totals by region",
        _markdown_table(_REGION_COLUMNS, _region_rows(summary)),
        "## Totals by product",
        _markdown_table(_PRODUCT_COLUMNS, _product_rows(summary)),
        "**Top product:** " + _top_product_name(summary),
        "**Average order value:** " + _money(summary.average_order_value),
    ]
    return "\n\n".join(blocks) + "\n"


def _markdown_table(column_names: _Row, rows: list[_Row]) -> str:
    lines = [
        _markdown_row(column_names),
        "|" + "---|" * len(column_names),
        *(_markdown_row(cells) for cells in rows),
    ]
    return "\n".join(lines)


def _markdown_row(cells: _Row) -> str:
    return "| " + " | ".join(cells) + " |"


def _region_rows(summary: SalesSummary) -> list[_Row]:
    return [(total.name, _money(total.revenue)) for total in summary.region_totals]


def _product_rows(summary: SalesSummary) -> list[_Row]:
    return [
        (total.name, str(total.units), _money(total.revenue))
        for total in summary.product_totals
    ]


def _top_product_name(summary: SalesSummary) -> str:
    # Reports without sales have always printed the literal "None".
    return str(summary.top_product)


def _money(amount: float) -> str:
    return f"{amount:.2f}"


def _end_each_line(lines: list[str]) -> str:
    return "".join(line + "\n" for line in lines)


_RENDERERS: dict[str, Renderer] = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}

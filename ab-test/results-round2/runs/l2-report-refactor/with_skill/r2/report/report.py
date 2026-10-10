import csv
from dataclasses import dataclass


def generate(path, fmt):
    if fmt not in _RENDERERS:
        raise ValueError(f"unknown format {fmt!r}, expected one of: {', '.join(_RENDERERS)}")
    summary = _summarize(_read_rows(path))
    return _RENDERERS[fmt](summary)


@dataclass(frozen=True)
class _SalesSummary:
    totals_by_region: tuple[tuple[str, float], ...]  # (region, revenue), sorted by region
    totals_by_product: tuple[tuple[str, int, float], ...]  # (product, units, revenue), sorted
    top_product: str | None  # None when there are no sales
    average_order_value: float


def _read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _summarize(rows):
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

    return _SalesSummary(
        totals_by_region=tuple(sorted(revenue_by_region.items())),
        totals_by_product=tuple(
            (product, units_by_product[product], revenue_by_product[product])
            for product in sorted(revenue_by_product)
        ),
        # Ties go to the product that appears first in the file.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=total_revenue / len(rows) if rows else 0,
    )


def _add_to_total(totals, key, amount):
    if key in totals:
        totals[key] += amount
    else:
        totals[key] = amount  # not 0 + amount, which would turn -0.0 into 0.0


def _render_text(summary):
    lines = ["SALES REPORT", "=" * 40]
    lines += ["", "Totals by region", "-" * 40]
    lines += [region.ljust(20) + revenue.rjust(20) for region, revenue in _region_rows(summary)]
    lines += ["", "Totals by product", "-" * 40]
    lines += [
        product.ljust(20) + units.rjust(8) + revenue.rjust(12)
        for product, units, revenue in _product_rows(summary)
    ]
    lines += [
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_format_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _render_html(summary):
    lines = ["<html><body>", "<h1>Sales report</h1>"]
    lines += ["<h2>Totals by region</h2>"]
    lines += _html_table(("Region", "Revenue"), _region_rows(summary))
    lines += ["<h2>Totals by product</h2>"]
    lines += _html_table(("Product", "Units", "Revenue"), _product_rows(summary))
    lines += [
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
        "</body></html>",
    ]
    return _join_lines(lines)


def _html_table(header, rows):
    return (
        ["<table>", _html_row("th", header)]
        + [_html_row("td", row) for row in rows]
        + ["</table>"]
    )


def _html_row(cell_tag, cells):
    return "<tr>" + "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells) + "</tr>"


def _render_markdown(summary):
    lines = ["# Sales report"]
    lines += ["", "## Totals by region", ""]
    lines += _markdown_table(("Region", "Revenue"), _region_rows(summary))
    lines += ["", "## Totals by product", ""]
    lines += _markdown_table(("Product", "Units", "Revenue"), _product_rows(summary))
    lines += [
        "",
        f"**Top product:** {summary.top_product}",
        "",
        f"**Average order value:** {_format_money(summary.average_order_value)}",
    ]
    return _join_lines(lines)


def _markdown_table(header, rows):
    separator = "|" + "---|" * len(header)
    return [_markdown_row(header), separator] + [_markdown_row(row) for row in rows]


def _markdown_row(cells):
    return "| " + " | ".join(cells) + " |"


def _region_rows(summary):
    return [(region, _format_money(revenue)) for region, revenue in summary.totals_by_region]


def _product_rows(summary):
    return [
        (product, str(units), _format_money(revenue))
        for product, units, revenue in summary.totals_by_product
    ]


def _format_money(amount):
    return f"{amount:.2f}"


def _join_lines(lines):
    return "".join(line + "\n" for line in lines)


_RENDERERS = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}

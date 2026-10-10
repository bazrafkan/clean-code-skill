You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{"pairs": [{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}, ...]}

Read only this packet file. Do not look at any other file or directory, and do not write any files.


## Task given to both developers

`report/report.py` has become hard to change. Add a Markdown output format (`"md"`), and leave the code easier to extend with further formats.

Constraints:
- `generate(path, fmt)` keeps its signature. `fmt` is `"text"`, `"html"` or `"md"`. An unknown format still raises an exception.
- `"text"` and `"html"` output must stay byte-for-byte identical to today's output, for every input.
- The Markdown output uses the same values and ordering as the other formats (rows sorted by name), in exactly this layout. Each line ends with `\n`, and there is one blank line between blocks:

```
# Sales report

## Totals by region

| Region | Revenue |
|---|---|
| East | 57.48 |
| North | 44.99 |
| South | 74.47 |

## Totals by product

| Product | Units | Revenue |
|---|---|---|
| Doohickey | 2 | 14.50 |
| Gadget | 6 | 119.94 |
| Widget | 17 | 42.50 |

**Top product:** Gadget

**Average order value:** 29.49
```

(This is the expected output for `samples/sales.csv`.)

## Pair 1

### Implementation 1

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,202 @@
-import csv
+"""Sales report built from a CSV file of orders.
 
+A report is produced in two steps: the orders are summarised into a
+``SalesSummary``, then the renderer registered for the requested format lays
+the summary out. To support another format, write a function that takes a
+``SalesSummary`` and returns the report as a string, and add it to
+``_RENDERERS`` at the bottom of this module.
+"""
 
-def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
-
-    reg = {}
-    prod = {}
-    units = {}
-    n = 0
-    tot = 0
-    for row in rows:
-        u = int(row["units"])
-        p = float(row["unit_price"])
-        v = u * p
-        n = n + 1
-        tot = tot + v
-        if row["region"] in reg:
-            reg[row["region"]] = reg[row["region"]] + v
-        else:
-            reg[row["region"]] = v
-        if row["product"] in prod:
-            prod[row["product"]] = prod[row["product"]] + v
-            units[row["product"]] = units[row["product"]] + u
-        else:
-            prod[row["product"]] = v
-            units[row["product"]] = u
-
-    out = ""
-    if fmt == "text":
-        out = out + "SALES REPORT\n"
-        out = out + "=" * 40 + "\n"
-    elif fmt == "html":
-        out = out + "<html><body>\n"
-        out = out + "<h1>Sales report</h1>\n"
-    else:
-        raise Exception("bad format")
+from __future__ import annotations
 
-    if fmt == "text":
-        out = out + "\nTotals by region\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(reg):
-            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by region</h2>\n<table>\n"
-        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
-        for k in sorted(reg):
-            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    if fmt == "text":
-        out = out + "\nTotals by product\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(prod):
-            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by product</h2>\n<table>\n"
-        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
-        for k in sorted(prod):
-            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    best = None
-    for k in prod:
-        if best is None or prod[k] > prod[best]:
-            best = k
-    if n > 0:
-        avg = tot / n
+import csv
+import os
+from collections.abc import Callable
+from dataclasses import dataclass
+from typing import NamedTuple
+
+
+class RegionTotal(NamedTuple):
+    region: str
+    revenue: float
+
+
+class ProductTotal(NamedTuple):
+    product: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    """The figures shown in a report, independent of the output format."""
+
+    regions: list[RegionTotal]  # sorted by region name
+    products: list[ProductTotal]  # sorted by product name
+    top_product: str | None  # highest revenue; None when there are no orders
+    average_order_value: float
+
+
+def generate(path: str | os.PathLike[str], fmt: str) -> str:
+    """Return the sales report for the orders CSV at ``path``.
+
+    ``fmt`` is the output format: "text", "html" or "md". Any other format
+    name raises ``ValueError``.
+    """
+    render = _RENDERERS.get(fmt)
+    if render is None:
+        supported = ", ".join(sorted(_RENDERERS))
+        raise ValueError(f"bad format {fmt!r}; expected one of: {supported}")
+    return render(_summarize(_read_orders(path)))
+
+
+def _read_orders(path: str | os.PathLike[str]) -> list[dict[str, str]]:
+    # The default newline handling and encoding are deliberate: changing them
+    # changes how some field values are read, and so the report output.
+    with open(path) as orders_file:
+        return list(csv.DictReader(orders_file))
+
+
+def _summarize(orders: list[dict[str, str]]) -> SalesSummary:
+    revenue_by_region: dict[str, float] = {}
+    revenue_by_product: dict[str, float] = {}
+    units_by_product: dict[str, int] = {}
+    total_revenue = 0.0
+    for order in orders:
+        units = int(order["units"])
+        revenue = units * float(order["unit_price"])
+        total_revenue += revenue
+        _add_to(revenue_by_region, order["region"], revenue)
+        _add_to(revenue_by_product, order["product"], revenue)
+        _add_to(units_by_product, order["product"], units)
+
+    return SalesSummary(
+        regions=[
+            RegionTotal(region, revenue_by_region[region])
+            for region in sorted(revenue_by_region)
+        ],
+        products=[
+            ProductTotal(product, units_by_product[product], revenue_by_product[product])
+            for product in sorted(revenue_by_product)
+        ],
+        # max() keeps the first of equal values: ties go to the product seen first.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / len(orders) if orders else 0.0,
+    )
+
+
+def _add_to(totals: dict, key: str, amount: float) -> None:
+    # Start from the first amount rather than from 0: 0 + -0.0 is 0.0, which
+    # would print as "0.00" instead of "-0.00".
+    if key in totals:
+        totals[key] += amount
     else:
-        avg = 0
+        totals[key] = amount
+
 
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+def _render_text(summary: SalesSummary) -> str:
+    lines = ["SALES REPORT", "=" * 40]
+    lines += ["", "Totals by region", "-" * 40]
+    lines += [
+        f"{row.region:<20}{_format_money(row.revenue):>20}" for row in summary.regions
+    ]
+    lines += ["", "Totals by product", "-" * 40]
+    lines += [
+        f"{row.product:<20}{row.units:>8}{_format_money(row.revenue):>12}"
+        for row in summary.products
+    ]
+    lines += [
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_format_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _render_html(summary: SalesSummary) -> str:
+    lines = ["<html><body>", "<h1>Sales report</h1>"]
+    lines += ["<h2>Totals by region</h2>"]
+    lines += _html_table(
+        ["Region", "Revenue"],
+        [[row.region, _format_money(row.revenue)] for row in summary.regions],
+    )
+    lines += ["<h2>Totals by product</h2>"]
+    lines += _html_table(
+        ["Product", "Units", "Revenue"],
+        [
+            [row.product, str(row.units), _format_money(row.revenue)]
+            for row in summary.products
+        ],
+    )
+    lines += [
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ]
+    return _join_lines(lines)
+
+
+def _html_table(headers: list[str], rows: list[list[str]]) -> list[str]:
+    return [
+        "<table>",
+        _html_row("th", headers),
+        *(_html_row("td", row) for row in rows),
+        "</table>",
+    ]
+
+
+def _html_row(cell_tag: str, cells: list[str]) -> str:
+    open_tag, close_tag = f"<{cell_tag}>", f"</{cell_tag}>"
+    return "<tr>" + "".join(open_tag + cell + close_tag for cell in cells) + "</tr>"
+
+
+def _render_markdown(summary: SalesSummary) -> str:
+    lines = ["# Sales report"]
+    lines += ["", "## Totals by region", ""]
+    lines += _markdown_table(
+        ["Region", "Revenue"],
+        [[row.region, _format_money(row.revenue)] for row in summary.regions],
+    )
+    lines += ["", "## Totals by product", ""]
+    lines += _markdown_table(
+        ["Product", "Units", "Revenue"],
+        [
+            [row.product, str(row.units), _format_money(row.revenue)]
+            for row in summary.products
+        ],
+    )
+    lines += [
+        "",
+        f"**Top product:** {summary.top_product}",
+        "",
+        f"**Average order value:** {_format_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
+    return [
+        _markdown_row(headers),
+        "|" + "---|" * len(headers),
+        *(_markdown_row(row) for row in rows),
+    ]
+
+
+def _markdown_row(cells: list[str]) -> str:
+    return "| " + " | ".join(cells) + " |"
+
+
+def _format_money(amount: float) -> str:
+    return f"{amount:.2f}"
+
+
+def _join_lines(lines: list[str]) -> str:
+    """Join ``lines`` into a document in which every line ends with a newline."""
+    return "".join(line + "\n" for line in lines)
+
+
+_RENDERERS: dict[str, Callable[[SalesSummary], str]] = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,104 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
+HEADER = "date,region,product,units,unit_price\n"
+
+EXPECTED_TEXT = """\
+SALES REPORT
+========================================
+
+Totals by region
+----------------------------------------
+East                               57.48
+North                              44.99
+South                              74.47
+
+Totals by product
+----------------------------------------
+Doohickey                  2       14.50
+Gadget                     6      119.94
+Widget                    17       42.50
+
+Top product: Gadget
+Average order value: 29.49
+"""
+
+EXPECTED_HTML = """\
+<html><body>
+<h1>Sales report</h1>
+<h2>Totals by region</h2>
+<table>
+<tr><th>Region</th><th>Revenue</th></tr>
+<tr><td>East</td><td>57.48</td></tr>
+<tr><td>North</td><td>44.99</td></tr>
+<tr><td>South</td><td>74.47</td></tr>
+</table>
+<h2>Totals by product</h2>
+<table>
+<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>
+<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>
+<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>
+<tr><td>Widget</td><td>17</td><td>42.50</td></tr>
+</table>
+<p>Top product: Gadget</p>
+<p>Average order value: 29.49</p>
+</body></html>
+"""
+
+EXPECTED_MARKDOWN = """\
+# Sales report
+
+## Totals by region
+
+| Region | Revenue |
+|---|---|
+| East | 57.48 |
+| North | 44.99 |
+| South | 74.47 |
+
+## Totals by product
+
+| Product | Units | Revenue |
+|---|---|---|
+| Doohickey | 2 | 14.50 |
+| Gadget | 6 | 119.94 |
+| Widget | 17 | 42.50 |
+
+**Top product:** Gadget
+
+**Average order value:** 29.49
+"""
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", EXPECTED_TEXT), ("html", EXPECTED_HTML), ("md", EXPECTED_MARKDOWN)],
+)
+def test_sample_report(fmt, expected):
+    assert generate(SAMPLE, fmt) == expected
+
+
+@pytest.mark.parametrize("fmt", ["pdf", "TEXT", "", None])
+def test_unknown_format_raises(fmt):
+    with pytest.raises(ValueError, match="bad format"):
+        generate(SAMPLE, fmt)
+
+
+def test_report_without_orders(tmp_path):
+    orders = tmp_path / "orders.csv"
+    orders.write_text(HEADER)
+
+    assert generate(orders, "md").endswith(
+        "**Top product:** None\n\n**Average order value:** 0.00\n"
+    )
+
+
+def test_top_product_tie_goes_to_first_seen(tmp_path):
+    orders = tmp_path / "orders.csv"
+    orders.write_text(HEADER + "2026-01-01,North,Zed,1,5.00\n2026-01-01,North,Abe,1,5.00\n")
+
+    assert "Top product: Zed\n" in generate(orders, "text")
```

### Implementation 2

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,283 @@
+"""Sales report: revenue by region and by product, rendered in a chosen format.
+
+To add a format, write a `_render_<name>(summary) -> str` function and register
+it in `_RENDERERS`.
+"""
+
 import csv
+import os
+from collections.abc import Callable, Iterable
+from dataclasses import dataclass
+from typing import TypeVar
+
+
+def generate(path: str | os.PathLike[str], fmt: str) -> str:
+    """Return the sales report for the orders CSV at `path`, rendered as `fmt`.
+
+    Supported formats are "text", "html" and "md". Raises ValueError for any
+    other format, before the file is read.
+    """
+    render = _renderer_for(fmt)
+    return render(_summarize(_read_orders(path)))
+
+
+@dataclass(frozen=True)
+class _Order:
+    region: str
+    product: str
+    units: int
+    # Binary float on purpose: the text and HTML output rely on its rounding.
+    revenue: float
+
+
+def _read_orders(path: str | os.PathLike[str]) -> list[_Order]:
+    # No newline="": universal newlines normalize line breaks inside quoted
+    # fields, and the report output depends on that.
+    with open(path) as file:
+        rows = list(csv.DictReader(file))
+    return [_parse_order(row) for row in rows]
+
+
+def _parse_order(row: dict[str, str | None]) -> _Order:
+    units = int(_required(row, "units"))
+    revenue = units * float(_required(row, "unit_price"))
+    return _Order(
+        region=_required(row, "region"),
+        product=_required(row, "product"),
+        units=units,
+        revenue=revenue,
+    )
+
+
+def _required(row: dict[str, str | None], column: str) -> str:
+    value = row[column]
+    if value is None:
+        raise ValueError(f"order row has no {column!r} value (row too short): {row}")
+    return value
+
+
+@dataclass(frozen=True)
+class _RegionTotal:
+    region: str
+    revenue: float
+
+
+@dataclass(frozen=True)
+class _ProductTotal:
+    product: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class _SalesSummary:
+    regions: tuple[_RegionTotal, ...]  # sorted by region
+    products: tuple[_ProductTotal, ...]  # sorted by product
+    top_product: str | None  # None when there are no orders
+    average_order_value: float
+
+
+def _summarize(orders: list[_Order]) -> _SalesSummary:
+    revenue_by_region = _total_by(
+        orders, key=lambda order: order.region, amount=lambda order: order.revenue
+    )
+    revenue_by_product = _total_by(
+        orders, key=lambda order: order.product, amount=lambda order: order.revenue
+    )
+    units_by_product = _total_by(
+        orders, key=lambda order: order.product, amount=lambda order: order.units
+    )
+    return _SalesSummary(
+        regions=tuple(
+            _RegionTotal(region, revenue_by_region[region])
+            for region in sorted(revenue_by_region)
+        ),
+        products=tuple(
+            _ProductTotal(
+                product, units_by_product[product], revenue_by_product[product]
+            )
+            for product in sorted(revenue_by_product)
+        ),
+        top_product=_top_product(revenue_by_product),
+        average_order_value=_average_order_value(orders),
+    )
+
+
+_Amount = TypeVar("_Amount", int, float)
+
+
+def _total_by(
+    orders: Iterable[_Order],
+    key: Callable[[_Order], str],
+    amount: Callable[[_Order], _Amount],
+) -> dict[str, _Amount]:
+    """Total `amount` per `key`, adding in file order; keys keep first-seen order."""
+    totals: dict[str, _Amount] = {}
+    for order in orders:
+        group, value = key(order), amount(order)
+        # Seeded with the first value rather than 0, so a group whose only
+        # revenue is -0.0 still prints "-0.00".
+        totals[group] = totals[group] + value if group in totals else value
+    return totals
+
+
+def _top_product(revenue_by_product: dict[str, float]) -> str | None:
+    """Highest-revenue product; a tie goes to the product that appears first."""
+    return max(
+        revenue_by_product,
+        key=lambda product: revenue_by_product[product],
+        default=None,
+    )
+
+
+def _average_order_value(orders: list[_Order]) -> float:
+    if not orders:
+        return 0.0
+    # A plain loop, not sum(): since Python 3.12 sum() compensates float
+    # rounding, which can shift the printed cents.
+    total = 0.0
+    for order in orders:
+        total += order.revenue
+    return total / len(orders)
+
+
+_REPORT_TITLE = "Sales report"
+_NO_TOP_PRODUCT = "None"
+
+
+@dataclass(frozen=True)
+class _Table:
+    heading: str
+    columns: tuple[str, ...]
+    rows: tuple[tuple[str, ...], ...]
+
+
+def _region_table(summary: _SalesSummary) -> _Table:
+    return _Table(
+        heading="Totals by region",
+        columns=("Region", "Revenue"),
+        rows=tuple((total.region, _money(total.revenue)) for total in summary.regions),
+    )
+
+
+def _product_table(summary: _SalesSummary) -> _Table:
+    return _Table(
+        heading="Totals by product",
+        columns=("Product", "Units", "Revenue"),
+        rows=tuple(
+            (total.product, str(total.units), _money(total.revenue))
+            for total in summary.products
+        ),
+    )
+
+
+def _highlights(summary: _SalesSummary) -> tuple[tuple[str, str], ...]:
+    """The (label, value) lines that close every report."""
+    top_product = summary.top_product
+    return (
+        ("Top product", _NO_TOP_PRODUCT if top_product is None else top_product),
+        ("Average order value", _money(summary.average_order_value)),
+    )
+
+
+def _money(amount: float) -> str:
+    return f"{amount:.2f}"
+
+
+_TEXT_RULE_WIDTH = 40
+_TEXT_REGION_COLUMN_WIDTHS = (20, 20)
+_TEXT_PRODUCT_COLUMN_WIDTHS = (20, 8, 12)
+
+
+def _render_text(summary: _SalesSummary) -> str:
+    lines = [
+        _REPORT_TITLE.upper(),
+        "=" * _TEXT_RULE_WIDTH,
+        *_text_table(_region_table(summary), _TEXT_REGION_COLUMN_WIDTHS),
+        *_text_table(_product_table(summary), _TEXT_PRODUCT_COLUMN_WIDTHS),
+        "",
+        *(f"{label}: {value}" for label, value in _highlights(summary)),
+    ]
+    return "\n".join(lines) + "\n"
+
+
+def _text_table(table: _Table, column_widths: tuple[int, ...]) -> list[str]:
+    rows = [_text_row(row, column_widths) for row in table.rows]
+    return ["", table.heading, "-" * _TEXT_RULE_WIDTH, *rows]
+
+
+def _text_row(cells: tuple[str, ...], column_widths: tuple[int, ...]) -> str:
+    """Left-align the name in the first column, right-align the figures after it."""
+    name, *figures = cells
+    name_width, *figure_widths = column_widths
+    aligned_figures = (
+        figure.rjust(width)
+        for figure, width in zip(figures, figure_widths, strict=True)
+    )
+    return name.ljust(name_width) + "".join(aligned_figures)
+
+
+def _render_html(summary: _SalesSummary) -> str:
+    lines = [
+        "<html><body>",
+        f"<h1>{_REPORT_TITLE}</h1>",
+        *_html_table(_region_table(summary)),
+        *_html_table(_product_table(summary)),
+        *(f"<p>{label}: {value}</p>" for label, value in _highlights(summary)),
+        "</body></html>",
+    ]
+    return "\n".join(lines) + "\n"
+
+
+def _html_table(table: _Table) -> list[str]:
+    return [
+        f"<h2>{table.heading}</h2>",
+        "<table>",
+        _html_row("th", table.columns),
+        *(_html_row("td", row) for row in table.rows),
+        "</table>",
+    ]
+
+
+def _html_row(cell_tag: str, cells: tuple[str, ...]) -> str:
+    # Warning: cells are not HTML-escaped, so names containing markup leak
+    # into the page. Escaping would change the established HTML output.
+    return (
+        "<tr>" + "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells) + "</tr>"
+    )
+
+
+def _render_markdown(summary: _SalesSummary) -> str:
+    blocks = [
+        f"# {_REPORT_TITLE}",
+        *_markdown_table(_region_table(summary)),
+        *_markdown_table(_product_table(summary)),
+        *(f"**{label}:** {value}" for label, value in _highlights(summary)),
+    ]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _markdown_table(table: _Table) -> list[str]:
+    """The heading block and the pipe-table block for `table`."""
+    header = _markdown_row(table.columns)
+    delimiter = "|" + "---|" * len(table.columns)
+    rows = [_markdown_row(row) for row in table.rows]
+    return [f"## {table.heading}", "\n".join([header, delimiter, *rows])]
+
+
+def _markdown_row(cells: tuple[str, ...]) -> str:
+    return "| " + " | ".join(cells) + " |"
+
+
+_RENDERERS: dict[str, Callable[[_SalesSummary], str]] = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
 
 
-def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
-
-    reg = {}
-    prod = {}
-    units = {}
-    n = 0
-    tot = 0
-    for row in rows:
-        u = int(row["units"])
-        p = float(row["unit_price"])
-        v = u * p
-        n = n + 1
-        tot = tot + v
-        if row["region"] in reg:
-            reg[row["region"]] = reg[row["region"]] + v
-        else:
-            reg[row["region"]] = v
-        if row["product"] in prod:
-            prod[row["product"]] = prod[row["product"]] + v
-            units[row["product"]] = units[row["product"]] + u
-        else:
-            prod[row["product"]] = v
-            units[row["product"]] = u
-
-    out = ""
-    if fmt == "text":
-        out = out + "SALES REPORT\n"
-        out = out + "=" * 40 + "\n"
-    elif fmt == "html":
-        out = out + "<html><body>\n"
-        out = out + "<h1>Sales report</h1>\n"
-    else:
-        raise Exception("bad format")
-
-    if fmt == "text":
-        out = out + "\nTotals by region\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(reg):
-            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by region</h2>\n<table>\n"
-        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
-        for k in sorted(reg):
-            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    if fmt == "text":
-        out = out + "\nTotals by product\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(prod):
-            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by product</h2>\n<table>\n"
-        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
-        for k in sorted(prod):
-            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    best = None
-    for k in prod:
-        if best is None or prod[k] > prod[best]:
-            best = k
-    if n > 0:
-        avg = tot / n
-    else:
-        avg = 0
-
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+def _renderer_for(fmt: str) -> Callable[[_SalesSummary], str]:
+    if fmt not in _RENDERERS:
+        supported = ", ".join(_RENDERERS)
+        raise ValueError(f"bad format {fmt!r}: expected one of {supported}")
+    return _RENDERERS[fmt]
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,186 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE_CSV = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
+CSV_HEADER = "date,region,product,units,unit_price\n"
+
+
+@pytest.fixture
+def empty_csv(tmp_path):
+    return write_csv(tmp_path, "")
+
+
+@pytest.fixture
+def tied_products_csv(tmp_path):
+    return write_csv(
+        tmp_path,
+        "2026-01-01,West,Bolt,2,5.00\n2026-01-02,West,Anchor,1,10.00\n",
+    )
+
+
+def write_csv(directory, rows):
+    path = directory / "sales.csv"
+    path.write_text(CSV_HEADER + rows)
+    return path
+
+
+def test_text_report_for_sample():
+    assert generate(SAMPLE_CSV, "text") == (
+        "SALES REPORT\n"
+        "========================================\n"
+        "\n"
+        "Totals by region\n"
+        "----------------------------------------\n"
+        "East                               57.48\n"
+        "North                              44.99\n"
+        "South                              74.47\n"
+        "\n"
+        "Totals by product\n"
+        "----------------------------------------\n"
+        "Doohickey                  2       14.50\n"
+        "Gadget                     6      119.94\n"
+        "Widget                    17       42.50\n"
+        "\n"
+        "Top product: Gadget\n"
+        "Average order value: 29.49\n"
+    )
+
+
+def test_html_report_for_sample():
+    assert generate(SAMPLE_CSV, "html") == (
+        "<html><body>\n"
+        "<h1>Sales report</h1>\n"
+        "<h2>Totals by region</h2>\n"
+        "<table>\n"
+        "<tr><th>Region</th><th>Revenue</th></tr>\n"
+        "<tr><td>East</td><td>57.48</td></tr>\n"
+        "<tr><td>North</td><td>44.99</td></tr>\n"
+        "<tr><td>South</td><td>74.47</td></tr>\n"
+        "</table>\n"
+        "<h2>Totals by product</h2>\n"
+        "<table>\n"
+        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
+        "<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>\n"
+        "<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>\n"
+        "<tr><td>Widget</td><td>17</td><td>42.50</td></tr>\n"
+        "</table>\n"
+        "<p>Top product: Gadget</p>\n"
+        "<p>Average order value: 29.49</p>\n"
+        "</body></html>\n"
+    )
+
+
+def test_markdown_report_for_sample():
+    assert generate(SAMPLE_CSV, "md") == (
+        "# Sales report\n"
+        "\n"
+        "## Totals by region\n"
+        "\n"
+        "| Region | Revenue |\n"
+        "|---|---|\n"
+        "| East | 57.48 |\n"
+        "| North | 44.99 |\n"
+        "| South | 74.47 |\n"
+        "\n"
+        "## Totals by product\n"
+        "\n"
+        "| Product | Units | Revenue |\n"
+        "|---|---|---|\n"
+        "| Doohickey | 2 | 14.50 |\n"
+        "| Gadget | 6 | 119.94 |\n"
+        "| Widget | 17 | 42.50 |\n"
+        "\n"
+        "**Top product:** Gadget\n"
+        "\n"
+        "**Average order value:** 29.49\n"
+    )
+
+
+def test_text_report_without_orders(empty_csv):
+    assert generate(empty_csv, "text") == (
+        "SALES REPORT\n"
+        "========================================\n"
+        "\n"
+        "Totals by region\n"
+        "----------------------------------------\n"
+        "\n"
+        "Totals by product\n"
+        "----------------------------------------\n"
+        "\n"
+        "Top product: None\n"
+        "Average order value: 0.00\n"
+    )
+
+
+def test_html_report_without_orders(empty_csv):
+    assert generate(empty_csv, "html") == (
+        "<html><body>\n"
+        "<h1>Sales report</h1>\n"
+        "<h2>Totals by region</h2>\n"
+        "<table>\n"
+        "<tr><th>Region</th><th>Revenue</th></tr>\n"
+        "</table>\n"
+        "<h2>Totals by product</h2>\n"
+        "<table>\n"
+        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
+        "</table>\n"
+        "<p>Top product: None</p>\n"
+        "<p>Average order value: 0.00</p>\n"
+        "</body></html>\n"
+    )
+
+
+def test_markdown_report_without_orders_keeps_empty_tables(empty_csv):
+    assert generate(empty_csv, "md") == (
+        "# Sales report\n"
+        "\n"
+        "## Totals by region\n"
+        "\n"
+        "| Region | Revenue |\n"
+        "|---|---|\n"
+        "\n"
+        "## Totals by product\n"
+        "\n"
+        "| Product | Units | Revenue |\n"
+        "|---|---|---|\n"
+        "\n"
+        "**Top product:** None\n"
+        "\n"
+        "**Average order value:** 0.00\n"
+    )
+
+
+@pytest.mark.parametrize(
+    ("fmt", "top_product_line"),
+    [
+        ("text", "Top product: Bolt\n"),
+        ("html", "<p>Top product: Bolt</p>\n"),
+        ("md", "**Top product:** Bolt\n"),
+    ],
+)
+def test_top_product_tie_goes_to_first_product_in_file(
+    tied_products_csv, fmt, top_product_line
+):
+    assert top_product_line in generate(tied_products_csv, fmt)
+
+
+@pytest.mark.parametrize("fmt", ["text", "html", "md"])
+def test_row_missing_trailing_columns_raises(tmp_path, fmt):
+    path = tmp_path / "sales.csv"
+    path.write_text("units,unit_price,region,product\n3,2.50\n")
+
+    with pytest.raises(ValueError, match="'region'"):
+        generate(path, fmt)
+
+
+def test_unknown_format_raises():
+    with pytest.raises(ValueError, match="'pdf'"):
+        generate(SAMPLE_CSV, "pdf")
+
+
+def test_unknown_format_is_rejected_before_reading_the_file(tmp_path):
+    with pytest.raises(ValueError):
+        generate(tmp_path / "missing.csv", "pdf")
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/report/formats.py after/report/formats.py
--- before/report/formats.py
+++ after/report/formats.py
@@ -0,0 +1,149 @@
+"""Output formats of the sales report.
+
+Each renderer turns a SalesSummary into the complete report in one format.
+To support another format, write a renderer and add it to _RENDERERS.
+"""
+
+from collections.abc import Callable
+from typing import NamedTuple
+
+from .summary import SalesSummary
+
+Renderer = Callable[[SalesSummary], str]
+
+_TITLE = "Sales report"
+_NO_TOP_PRODUCT = "None"  # what the report has always shown when there are no sales
+
+_TEXT_LINE_WIDTH = 40
+_TEXT_REGION_COLUMN_WIDTHS = (20, 20)
+_TEXT_PRODUCT_COLUMN_WIDTHS = (20, 8, 12)
+
+
+class _Table(NamedTuple):
+    title: str
+    columns: tuple[str, ...]
+    rows: list[tuple[str, ...]]
+
+
+def renderer_for(fmt: str) -> Renderer:
+    if fmt not in _RENDERERS:
+        supported = ", ".join(sorted(_RENDERERS))
+        raise ValueError(f"unknown report format {fmt!r} (supported: {supported})")
+    return _RENDERERS[fmt]
+
+
+def _render_text(summary: SalesSummary) -> str:
+    lines = [_TITLE.upper(), "=" * _TEXT_LINE_WIDTH]
+    lines += _text_section(_region_table(summary), _TEXT_REGION_COLUMN_WIDTHS)
+    lines += _text_section(_product_table(summary), _TEXT_PRODUCT_COLUMN_WIDTHS)
+    lines.append("")
+    lines += [f"{label}: {value}" for label, value in _key_figures(summary)]
+    return _join_lines(lines)
+
+
+def _text_section(table: _Table, column_widths: tuple[int, ...]) -> list[str]:
+    lines = ["", table.title, "-" * _TEXT_LINE_WIDTH]
+    lines += [_text_row(row, column_widths) for row in table.rows]
+    return lines
+
+
+def _text_row(cells: tuple[str, ...], column_widths: tuple[int, ...]) -> str:
+    name, *figures = cells
+    name_width, *figure_widths = column_widths
+    aligned_figures = (
+        figure.rjust(width)
+        for figure, width in zip(figures, figure_widths, strict=True)
+    )
+    return name.ljust(name_width) + "".join(aligned_figures)
+
+
+def _render_html(summary: SalesSummary) -> str:
+    lines = ["<html><body>", f"<h1>{_TITLE}</h1>"]
+    lines += _html_section(_region_table(summary))
+    lines += _html_section(_product_table(summary))
+    lines += [f"<p>{label}: {value}</p>" for label, value in _key_figures(summary)]
+    lines.append("</body></html>")
+    return _join_lines(lines)
+
+
+def _html_section(table: _Table) -> list[str]:
+    return [
+        f"<h2>{table.title}</h2>",
+        "<table>",
+        _html_row("th", table.columns),
+        *(_html_row("td", row) for row in table.rows),
+        "</table>",
+    ]
+
+
+def _html_row(cell_tag: str, cells: tuple[str, ...]) -> str:
+    # Cells are not HTML-escaped; escaping would change the existing output.
+    tagged_cells = "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells)
+    return f"<tr>{tagged_cells}</tr>"
+
+
+def _render_markdown(summary: SalesSummary) -> str:
+    blocks = [f"# {_TITLE}"]
+    blocks += _markdown_section(_region_table(summary))
+    blocks += _markdown_section(_product_table(summary))
+    blocks += [f"**{label}:** {value}" for label, value in _key_figures(summary)]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _markdown_section(table: _Table) -> list[str]:
+    table_lines = [
+        _markdown_row(table.columns),
+        "|" + "---|" * len(table.columns),
+        *(_markdown_row(row) for row in table.rows),
+    ]
+    return [f"## {table.title}", "\n".join(table_lines)]
+
+
+def _markdown_row(cells: tuple[str, ...]) -> str:
+    return "| " + " | ".join(cells) + " |"
+
+
+_RENDERERS: dict[str, Renderer] = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
+
+
+def _region_table(summary: SalesSummary) -> _Table:
+    return _Table(
+        title="Totals by region",
+        columns=("Region", "Revenue"),
+        rows=[
+            (region.name, _format_money(region.revenue)) for region in summary.regions
+        ],
+    )
+
+
+def _product_table(summary: SalesSummary) -> _Table:
+    return _Table(
+        title="Totals by product",
+        columns=("Product", "Units", "Revenue"),
+        rows=[
+            (product.name, str(product.units), _format_money(product.revenue))
+            for product in summary.products
+        ],
+    )
+
+
+def _key_figures(summary: SalesSummary) -> list[tuple[str, str]]:
+    top_product = (
+        _NO_TOP_PRODUCT if summary.top_product is None else summary.top_product
+    )
+    return [
+        ("Top product", top_product),
+        ("Average order value", _format_money(summary.average_order_value)),
+    ]
+
+
+def _format_money(amount: float) -> str:
+    return f"{amount:.2f}"
+
+
+def _join_lines(lines: list[str]) -> str:
+    return "".join(f"{line}\n" for line in lines)
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,36 @@
 import csv
 
+from .formats import renderer_for
+from .summary import Sale, summarize
+
+_REQUIRED_COLUMNS = ("region", "product", "units", "unit_price")
+
 
 def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
-
-    reg = {}
-    prod = {}
-    units = {}
-    n = 0
-    tot = 0
-    for row in rows:
-        u = int(row["units"])
-        p = float(row["unit_price"])
-        v = u * p
-        n = n + 1
-        tot = tot + v
-        if row["region"] in reg:
-            reg[row["region"]] = reg[row["region"]] + v
-        else:
-            reg[row["region"]] = v
-        if row["product"] in prod:
-            prod[row["product"]] = prod[row["product"]] + v
-            units[row["product"]] = units[row["product"]] + u
-        else:
-            prod[row["product"]] = v
-            units[row["product"]] = u
-
-    out = ""
-    if fmt == "text":
-        out = out + "SALES REPORT\n"
-        out = out + "=" * 40 + "\n"
-    elif fmt == "html":
-        out = out + "<html><body>\n"
-        out = out + "<h1>Sales report</h1>\n"
-    else:
-        raise Exception("bad format")
-
-    if fmt == "text":
-        out = out + "\nTotals by region\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(reg):
-            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by region</h2>\n<table>\n"
-        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
-        for k in sorted(reg):
-            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    if fmt == "text":
-        out = out + "\nTotals by product\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(prod):
-            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by product</h2>\n<table>\n"
-        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
-        for k in sorted(prod):
-            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    best = None
-    for k in prod:
-        if best is None or prod[k] > prod[best]:
-            best = k
-    if n > 0:
-        avg = tot / n
-    else:
-        avg = 0
-
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+    """Return the sales report for the CSV file at `path`, rendered in format `fmt`.
+
+    `fmt` must name a format registered in report.formats, such as "text";
+    any other value raises ValueError before the file is read.
+    """
+    render = renderer_for(fmt)
+    return render(summarize(_read_sales(path)))
+
+
+def _read_sales(path):
+    with open(path) as csv_file:
+        reader = csv.DictReader(csv_file)
+        return [_parse_sale(row, reader.line_num) for row in reader]
+
+
+def _parse_sale(row, line_num):
+    missing = [column for column in _REQUIRED_COLUMNS if row.get(column) is None]
+    if missing:
+        raise ValueError(
+            f"line {line_num} of the sales CSV has no {', '.join(missing)}"
+        )
+    return Sale(
+        region=row["region"],
+        product=row["product"],
+        units=int(row["units"]),
+        unit_price=float(row["unit_price"]),
+    )
diff -ruN before/report/summary.py after/report/summary.py
--- before/report/summary.py
+++ after/report/summary.py
@@ -0,0 +1,85 @@
+"""The figures shown in a sales report, computed from individual sales."""
+
+from collections.abc import Iterable
+from dataclasses import dataclass
+from typing import TypeVar
+
+_Amount = TypeVar("_Amount", int, float)
+
+
+@dataclass(frozen=True)
+class Sale:
+    region: str
+    product: str
+    units: int
+    unit_price: float
+
+    @property
+    def revenue(self) -> float:
+        return self.units * self.unit_price
+
+
+@dataclass(frozen=True)
+class RegionTotal:
+    name: str
+    revenue: float
+
+
+@dataclass(frozen=True)
+class ProductTotal:
+    name: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    """Report figures, with regions and products sorted by name."""
+
+    regions: tuple[RegionTotal, ...]
+    products: tuple[ProductTotal, ...]
+    top_product: str | None  # None when there are no sales
+    average_order_value: float
+
+
+def summarize(sales: list[Sale]) -> SalesSummary:
+    revenue_by_region = _sum_by_key((sale.region, sale.revenue) for sale in sales)
+    revenue_by_product = _sum_by_key((sale.product, sale.revenue) for sale in sales)
+    units_by_product = _sum_by_key((sale.product, sale.units) for sale in sales)
+    return SalesSummary(
+        regions=tuple(
+            RegionTotal(name, revenue_by_region[name])
+            for name in sorted(revenue_by_region)
+        ),
+        products=tuple(
+            ProductTotal(name, units_by_product[name], revenue_by_product[name])
+            for name in sorted(revenue_by_product)
+        ),
+        top_product=_top_product(revenue_by_product),
+        average_order_value=_average_order_value(sales),
+    )
+
+
+def _sum_by_key(pairs: Iterable[tuple[str, _Amount]]) -> dict[str, _Amount]:
+    totals: dict[str, _Amount] = {}
+    for key, amount in pairs:
+        # Seed each key with its first amount instead of adding it to 0:
+        # 0 + -0.0 is 0.0, which would print "0.00" where the report shows "-0.00".
+        totals[key] = totals[key] + amount if key in totals else amount
+    return totals
+
+
+def _top_product(revenue_by_product: dict[str, float]) -> str | None:
+    # max() keeps the first of equal values: a tie goes to the product seen first.
+    return max(revenue_by_product, key=revenue_by_product.__getitem__, default=None)
+
+
+def _average_order_value(sales: list[Sale]) -> float:
+    if not sales:
+        return 0.0
+    # Added left to right on purpose: sum() compensates float rounding (Python 3.12+),
+    # which can change the rounded average the report has always shown.
+    total = 0.0
+    for sale in sales:
+        total += sale.revenue
+    return total / len(sales)
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,202 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE_CSV = Path(__file__).parent.parent / "samples" / "sales.csv"
+CSV_HEADER = "date,region,product,units,unit_price\n"
+
+SAMPLE_TEXT = """\
+SALES REPORT
+========================================
+
+Totals by region
+----------------------------------------
+East                               57.48
+North                              44.99
+South                              74.47
+
+Totals by product
+----------------------------------------
+Doohickey                  2       14.50
+Gadget                     6      119.94
+Widget                    17       42.50
+
+Top product: Gadget
+Average order value: 29.49
+"""
+
+SAMPLE_HTML = """\
+<html><body>
+<h1>Sales report</h1>
+<h2>Totals by region</h2>
+<table>
+<tr><th>Region</th><th>Revenue</th></tr>
+<tr><td>East</td><td>57.48</td></tr>
+<tr><td>North</td><td>44.99</td></tr>
+<tr><td>South</td><td>74.47</td></tr>
+</table>
+<h2>Totals by product</h2>
+<table>
+<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>
+<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>
+<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>
+<tr><td>Widget</td><td>17</td><td>42.50</td></tr>
+</table>
+<p>Top product: Gadget</p>
+<p>Average order value: 29.49</p>
+</body></html>
+"""
+
+SAMPLE_MARKDOWN = """\
+# Sales report
+
+## Totals by region
+
+| Region | Revenue |
+|---|---|
+| East | 57.48 |
+| North | 44.99 |
+| South | 74.47 |
+
+## Totals by product
+
+| Product | Units | Revenue |
+|---|---|---|
+| Doohickey | 2 | 14.50 |
+| Gadget | 6 | 119.94 |
+| Widget | 17 | 42.50 |
+
+**Top product:** Gadget
+
+**Average order value:** 29.49
+"""
+
+EMPTY_TEXT = """\
+SALES REPORT
+========================================
+
+Totals by region
+----------------------------------------
+
+Totals by product
+----------------------------------------
+
+Top product: None
+Average order value: 0.00
+"""
+
+EMPTY_HTML = """\
+<html><body>
+<h1>Sales report</h1>
+<h2>Totals by region</h2>
+<table>
+<tr><th>Region</th><th>Revenue</th></tr>
+</table>
+<h2>Totals by product</h2>
+<table>
+<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>
+</table>
+<p>Top product: None</p>
+<p>Average order value: 0.00</p>
+</body></html>
+"""
+
+EMPTY_MARKDOWN = """\
+# Sales report
+
+## Totals by region
+
+| Region | Revenue |
+|---|---|
+
+## Totals by product
+
+| Product | Units | Revenue |
+|---|---|---|
+
+**Top product:** None
+
+**Average order value:** 0.00
+"""
+
+
+def write_sales_csv(directory, *rows):
+    path = directory / "sales.csv"
+    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows))
+    return path
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", SAMPLE_TEXT), ("html", SAMPLE_HTML), ("md", SAMPLE_MARKDOWN)],
+    ids=["text", "html", "md"],
+)
+def test_sample_report_in_each_format(fmt, expected):
+    assert generate(SAMPLE_CSV, fmt) == expected
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", EMPTY_TEXT), ("html", EMPTY_HTML), ("md", EMPTY_MARKDOWN)],
+    ids=["text", "html", "md"],
+)
+def test_report_without_sales_in_each_format(tmp_path, fmt, expected):
+    path = write_sales_csv(tmp_path)
+
+    assert generate(path, fmt) == expected
+
+
+def test_top_product_tie_goes_to_product_listed_first_in_file(tmp_path):
+    path = write_sales_csv(
+        tmp_path,
+        "2026-01-01,North,Zeta,1,5.00",
+        "2026-01-02,South,Alpha,1,5.00",
+    )
+
+    assert "Top product: Zeta\n" in generate(path, "text")
+
+
+def test_average_order_value_adds_revenues_in_file_order(tmp_path):
+    # Exact summation gives 1.10 / 4 = 0.275 -> "0.28". Adding left to right
+    # gives 1.0999999999999999 / 4 -> "0.27", which the report has always shown.
+    path = write_sales_csv(
+        tmp_path,
+        "2026-01-01,North,Widget,1,0.10",
+        "2026-01-02,North,Widget,1,0.10",
+        "2026-01-03,North,Widget,1,0.70",
+        "2026-01-04,North,Widget,1,0.20",
+    )
+
+    assert "Average order value: 0.27\n" in generate(path, "text")
+
+
+def test_zero_units_at_negative_price_show_as_negative_zero(tmp_path):
+    path = write_sales_csv(tmp_path, "2026-01-01,West,Refund,0,-5.00")
+
+    report = generate(path, "text")
+
+    assert "West                               -0.00\n" in report
+    assert "Refund                     0       -0.00\n" in report
+
+
+@pytest.mark.parametrize("fmt", ["text", "html", "md"])
+def test_row_missing_a_field_is_rejected(tmp_path, fmt):
+    path = tmp_path / "sales.csv"
+    path.write_text("units,unit_price,region,product\n3,2.50,North\n")
+
+    with pytest.raises(ValueError, match="line 2 .* no product"):
+        generate(path, fmt)
+
+
+def test_unknown_format_raises_value_error_naming_it():
+    with pytest.raises(ValueError, match="'pdf'"):
+        generate(SAMPLE_CSV, "pdf")
+
+
+def test_unknown_format_is_rejected_before_reading_the_file(tmp_path):
+    missing_path = tmp_path / "missing.csv"
+
+    with pytest.raises(ValueError):
+        generate(missing_path, "pdf")
```

### Implementation 2

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,175 @@
+"""Sales report built from a CSV of orders, rendered as plain text, HTML or Markdown.
+
+The figures are computed once, by ``summarize``, independently of any output format.
+Each format is a single ``_render_<format>(summary)`` function registered in
+``_RENDERERS``; adding a format means writing one such function and registering it.
+"""
+
 import csv
+from dataclasses import dataclass
+from typing import Optional
+
+REGION_COLUMNS = ("Region", "Revenue")
+PRODUCT_COLUMNS = ("Product", "Units", "Revenue")
+
+TEXT_RULE_WIDTH = 40
+TEXT_REGION_WIDTHS = (20, 20)
+TEXT_PRODUCT_WIDTHS = (20, 8, 12)
+
+
+@dataclass(frozen=True)
+class RegionTotal:
+    name: str
+    revenue: float
+
+
+@dataclass(frozen=True)
+class ProductTotal:
+    name: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    """Format-independent figures of a sales report; totals are sorted by name."""
+
+    regions: list[RegionTotal]
+    products: list[ProductTotal]
+    top_product: Optional[str]
+    average_order_value: float
 
 
 def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
-
-    reg = {}
-    prod = {}
-    units = {}
-    n = 0
-    tot = 0
-    for row in rows:
-        u = int(row["units"])
-        p = float(row["unit_price"])
-        v = u * p
-        n = n + 1
-        tot = tot + v
-        if row["region"] in reg:
-            reg[row["region"]] = reg[row["region"]] + v
-        else:
-            reg[row["region"]] = v
-        if row["product"] in prod:
-            prod[row["product"]] = prod[row["product"]] + v
-            units[row["product"]] = units[row["product"]] + u
-        else:
-            prod[row["product"]] = v
-            units[row["product"]] = u
-
-    out = ""
-    if fmt == "text":
-        out = out + "SALES REPORT\n"
-        out = out + "=" * 40 + "\n"
-    elif fmt == "html":
-        out = out + "<html><body>\n"
-        out = out + "<h1>Sales report</h1>\n"
-    else:
-        raise Exception("bad format")
-
-    if fmt == "text":
-        out = out + "\nTotals by region\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(reg):
-            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by region</h2>\n<table>\n"
-        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
-        for k in sorted(reg):
-            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    if fmt == "text":
-        out = out + "\nTotals by product\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(prod):
-            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by product</h2>\n<table>\n"
-        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
-        for k in sorted(prod):
-            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    best = None
-    for k in prod:
-        if best is None or prod[k] > prod[best]:
-            best = k
-    if n > 0:
-        avg = tot / n
-    else:
-        avg = 0
-
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+    """Return the sales report for the orders CSV at ``path``, rendered as ``fmt``.
+
+    ``fmt`` is "text", "html" or "md"; any other value raises ``ValueError``.
+    """
+    try:
+        render = _RENDERERS[fmt]
+    except KeyError:
+        supported = ", ".join(_RENDERERS)
+        raise ValueError(f"bad format: {fmt!r} (expected one of: {supported})") from None
+    return render(summarize(_read_orders(path)))
+
+
+def summarize(orders):
+    """Compute the report figures from order rows (dicts with region, product, units, unit_price)."""
+    revenue_by_region = {}
+    revenue_by_product = {}
+    units_by_product = {}
+    total_revenue = 0
+    for order in orders:
+        units = int(order["units"])
+        revenue = units * float(order["unit_price"])
+        total_revenue += revenue
+        _add(revenue_by_region, order["region"], revenue)
+        _add(revenue_by_product, order["product"], revenue)
+        _add(units_by_product, order["product"], units)
+
+    return SalesSummary(
+        regions=[RegionTotal(name, revenue_by_region[name]) for name in sorted(revenue_by_region)],
+        products=[
+            ProductTotal(name, units_by_product[name], revenue_by_product[name])
+            for name in sorted(revenue_by_product)
+        ],
+        # Ties go to the product seen first in the file.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / len(orders) if orders else 0,
+    )
+
+
+def _read_orders(path):
+    with open(path) as f:
+        return list(csv.DictReader(f))
+
+
+def _add(totals, key, amount):
+    # A new key starts at `amount` itself rather than 0 + amount, so a -0.0 total still prints "-0.00".
+    totals[key] = totals[key] + amount if key in totals else amount
+
+
+def _money(amount):
+    return f"{amount:.2f}"
+
+
+def _region_cells(summary):
+    return [(region.name, _money(region.revenue)) for region in summary.regions]
+
+
+def _product_cells(summary):
+    return [
+        (product.name, str(product.units), _money(product.revenue))
+        for product in summary.products
+    ]
+
+
+def _render_text(summary):
+    lines = ["SALES REPORT", "=" * TEXT_RULE_WIDTH]
+    lines += _text_section("Totals by region", TEXT_REGION_WIDTHS, _region_cells(summary))
+    lines += _text_section("Totals by product", TEXT_PRODUCT_WIDTHS, _product_cells(summary))
+    lines += [
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_money(summary.average_order_value)}",
+    ]
+    return "\n".join(lines) + "\n"
+
+
+def _text_section(title, widths, rows):
+    """A blank line, an underlined title, then the rows: first column left-aligned, the rest right-aligned."""
+    lines = ["", title, "-" * TEXT_RULE_WIDTH]
+    for first, *rest in rows:
+        right_aligned = "".join(cell.rjust(width) for cell, width in zip(rest, widths[1:]))
+        lines.append(first.ljust(widths[0]) + right_aligned)
+    return lines
+
+
+def _render_html(summary):
+    lines = ["<html><body>", "<h1>Sales report</h1>"]
+    lines += ["<h2>Totals by region</h2>", *_html_table(REGION_COLUMNS, _region_cells(summary))]
+    lines += ["<h2>Totals by product</h2>", *_html_table(PRODUCT_COLUMNS, _product_cells(summary))]
+    lines += [
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ]
+    return "\n".join(lines) + "\n"
+
+
+def _html_table(columns, rows):
+    return ["<table>", _html_row("th", columns), *(_html_row("td", row) for row in rows), "</table>"]
+
+
+def _html_row(tag, cells):
+    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"
+
+
+def _render_markdown(summary):
+    blocks = [
+        "# Sales report",
+        "## Totals by region",
+        _markdown_table(REGION_COLUMNS, _region_cells(summary)),
+        "## Totals by product",
+        _markdown_table(PRODUCT_COLUMNS, _product_cells(summary)),
+        f"**Top product:** {summary.top_product}",
+        f"**Average order value:** {_money(summary.average_order_value)}",
+    ]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _markdown_table(columns, rows):
+    lines = [_markdown_row(columns), "|" + "|".join("---" for _ in columns) + "|"]
+    lines += [_markdown_row(row) for row in rows]
+    return "\n".join(lines)
+
+
+def _markdown_row(cells):
+    return "| " + " | ".join(cells) + " |"
+
+
+_RENDERERS = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,97 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
+
+# Captured from report.py before the Markdown refactor: these must never change.
+EXPECTED_TEXT = (
+    "SALES REPORT\n"
+    "========================================\n"
+    "\n"
+    "Totals by region\n"
+    "----------------------------------------\n"
+    "East                               57.48\n"
+    "North                              44.99\n"
+    "South                              74.47\n"
+    "\n"
+    "Totals by product\n"
+    "----------------------------------------\n"
+    "Doohickey                  2       14.50\n"
+    "Gadget                     6      119.94\n"
+    "Widget                    17       42.50\n"
+    "\n"
+    "Top product: Gadget\n"
+    "Average order value: 29.49\n"
+)
+
+EXPECTED_HTML = (
+    "<html><body>\n"
+    "<h1>Sales report</h1>\n"
+    "<h2>Totals by region</h2>\n"
+    "<table>\n"
+    "<tr><th>Region</th><th>Revenue</th></tr>\n"
+    "<tr><td>East</td><td>57.48</td></tr>\n"
+    "<tr><td>North</td><td>44.99</td></tr>\n"
+    "<tr><td>South</td><td>74.47</td></tr>\n"
+    "</table>\n"
+    "<h2>Totals by product</h2>\n"
+    "<table>\n"
+    "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
+    "<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>\n"
+    "<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>\n"
+    "<tr><td>Widget</td><td>17</td><td>42.50</td></tr>\n"
+    "</table>\n"
+    "<p>Top product: Gadget</p>\n"
+    "<p>Average order value: 29.49</p>\n"
+    "</body></html>\n"
+)
+
+EXPECTED_MD = """\
+# Sales report
+
+## Totals by region
+
+| Region | Revenue |
+|---|---|
+| East | 57.48 |
+| North | 44.99 |
+| South | 74.47 |
+
+## Totals by product
+
+| Product | Units | Revenue |
+|---|---|---|
+| Doohickey | 2 | 14.50 |
+| Gadget | 6 | 119.94 |
+| Widget | 17 | 42.50 |
+
+**Top product:** Gadget
+
+**Average order value:** 29.49
+"""
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", EXPECTED_TEXT), ("html", EXPECTED_HTML), ("md", EXPECTED_MD)],
+)
+def test_sample_report(fmt, expected):
+    assert generate(SAMPLE, fmt) == expected
+
+
+def test_empty_csv_reports_no_top_product_and_zero_average(tmp_path):
+    empty = tmp_path / "empty.csv"
+    empty.write_text("date,region,product,units,unit_price\n")
+
+    report = generate(empty, "md")
+
+    assert "**Top product:** None\n" in report
+    assert report.endswith("**Average order value:** 0.00\n")
+
+
+def test_unknown_format_raises():
+    with pytest.raises(ValueError, match="bad format"):
+        generate(SAMPLE, "pdf")
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/report/formats.py after/report/formats.py
--- before/report/formats.py
+++ after/report/formats.py
@@ -0,0 +1,158 @@
+"""Output formats for the sales report.
+
+Each format is a function that renders a SalesSummary to a string. To add a
+format, write its render function and register it in _RENDERERS at the bottom.
+Warning: values go into HTML and Markdown unescaped, so a name containing
+"<" or "|" breaks the markup.
+"""
+
+from collections.abc import Callable
+
+from .sales import SalesSummary
+
+Renderer = Callable[[SalesSummary], str]
+_Row = tuple[str, ...]
+
+_REGION_COLUMNS = ("Region", "Revenue")
+_PRODUCT_COLUMNS = ("Product", "Units", "Revenue")
+
+
+def renderer_for(fmt: str) -> Renderer:
+    if fmt not in _RENDERERS:
+        supported = ", ".join(sorted(_RENDERERS))
+        raise ValueError(f"bad format {fmt!r}; supported formats: {supported}")
+    return _RENDERERS[fmt]
+
+
+_TEXT_LINE_WIDTH = 40
+_TEXT_NAME_WIDTH = 20
+_TEXT_UNITS_WIDTH = 8
+_TEXT_REGION_WIDTHS = (_TEXT_NAME_WIDTH, _TEXT_LINE_WIDTH - _TEXT_NAME_WIDTH)
+_TEXT_PRODUCT_WIDTHS = (
+    _TEXT_NAME_WIDTH,
+    _TEXT_UNITS_WIDTH,
+    _TEXT_LINE_WIDTH - _TEXT_NAME_WIDTH - _TEXT_UNITS_WIDTH,
+)
+
+
+def _render_text(summary: SalesSummary) -> str:
+    lines = ["SALES REPORT", "=" * _TEXT_LINE_WIDTH]
+    lines += _text_section(
+        "Totals by region", _region_rows(summary), _TEXT_REGION_WIDTHS
+    )
+    lines += _text_section(
+        "Totals by product", _product_rows(summary), _TEXT_PRODUCT_WIDTHS
+    )
+    lines += [
+        "",
+        "Top product: " + _top_product_name(summary),
+        "Average order value: " + _money(summary.average_order_value),
+    ]
+    return _end_each_line(lines)
+
+
+def _text_section(
+    title: str, rows: list[_Row], column_widths: tuple[int, ...]
+) -> list[str]:
+    return [
+        "",
+        title,
+        "-" * _TEXT_LINE_WIDTH,
+        *(_text_row(cells, column_widths) for cells in rows),
+    ]
+
+
+def _text_row(cells: _Row, column_widths: tuple[int, ...]) -> str:
+    name, *figures = cells
+    name_width, *figure_widths = column_widths
+    aligned_figures = (
+        figure.rjust(width)
+        for figure, width in zip(figures, figure_widths, strict=True)
+    )
+    return name.ljust(name_width) + "".join(aligned_figures)
+
+
+def _render_html(summary: SalesSummary) -> str:
+    lines = ["<html><body>", "<h1>Sales report</h1>"]
+    lines += _html_section("Totals by region", _REGION_COLUMNS, _region_rows(summary))
+    lines += _html_section(
+        "Totals by product", _PRODUCT_COLUMNS, _product_rows(summary)
+    )
+    lines += [
+        "<p>Top product: " + _top_product_name(summary) + "</p>",
+        "<p>Average order value: " + _money(summary.average_order_value) + "</p>",
+        "</body></html>",
+    ]
+    return _end_each_line(lines)
+
+
+def _html_section(heading: str, column_names: _Row, rows: list[_Row]) -> list[str]:
+    return [
+        "<h2>" + heading + "</h2>",
+        "<table>",
+        _html_row("th", column_names),
+        *(_html_row("td", cells) for cells in rows),
+        "</table>",
+    ]
+
+
+def _html_row(cell_tag: str, cells: _Row) -> str:
+    cells_html = "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells)
+    return "<tr>" + cells_html + "</tr>"
+
+
+def _render_markdown(summary: SalesSummary) -> str:
+    blocks = [
+        "# Sales report",
+        "## Totals by region",
+        _markdown_table(_REGION_COLUMNS, _region_rows(summary)),
+        "## Totals by product",
+        _markdown_table(_PRODUCT_COLUMNS, _product_rows(summary)),
+        "**Top product:** " + _top_product_name(summary),
+        "**Average order value:** " + _money(summary.average_order_value),
+    ]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _markdown_table(column_names: _Row, rows: list[_Row]) -> str:
+    lines = [
+        _markdown_row(column_names),
+        "|" + "---|" * len(column_names),
+        *(_markdown_row(cells) for cells in rows),
+    ]
+    return "\n".join(lines)
+
+
+def _markdown_row(cells: _Row) -> str:
+    return "| " + " | ".join(cells) + " |"
+
+
+def _region_rows(summary: SalesSummary) -> list[_Row]:
+    return [(total.name, _money(total.revenue)) for total in summary.region_totals]
+
+
+def _product_rows(summary: SalesSummary) -> list[_Row]:
+    return [
+        (total.name, str(total.units), _money(total.revenue))
+        for total in summary.product_totals
+    ]
+
+
+def _top_product_name(summary: SalesSummary) -> str:
+    # Reports without sales have always printed the literal "None".
+    return str(summary.top_product)
+
+
+def _money(amount: float) -> str:
+    return f"{amount:.2f}"
+
+
+def _end_each_line(lines: list[str]) -> str:
+    return "".join(line + "\n" for line in lines)
+
+
+_RENDERERS: dict[str, Renderer] = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,11 @@
-import csv
+from .formats import renderer_for
+from .sales import read_sales, summarize
 
 
 def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
+    """Return the sales report for the CSV file at path, rendered in format fmt.
 
-    reg = {}
-    prod = {}
-    units = {}
-    n = 0
-    tot = 0
-    for row in rows:
-        u = int(row["units"])
-        p = float(row["unit_price"])
-        v = u * p
-        n = n + 1
-        tot = tot + v
-        if row["region"] in reg:
-            reg[row["region"]] = reg[row["region"]] + v
-        else:
-            reg[row["region"]] = v
-        if row["product"] in prod:
-            prod[row["product"]] = prod[row["product"]] + v
-            units[row["product"]] = units[row["product"]] + u
-        else:
-            prod[row["product"]] = v
-            units[row["product"]] = u
-
-    out = ""
-    if fmt == "text":
-        out = out + "SALES REPORT\n"
-        out = out + "=" * 40 + "\n"
-    elif fmt == "html":
-        out = out + "<html><body>\n"
-        out = out + "<h1>Sales report</h1>\n"
-    else:
-        raise Exception("bad format")
-
-    if fmt == "text":
-        out = out + "\nTotals by region\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(reg):
-            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by region</h2>\n<table>\n"
-        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
-        for k in sorted(reg):
-            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    if fmt == "text":
-        out = out + "\nTotals by product\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(prod):
-            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by product</h2>\n<table>\n"
-        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
-        for k in sorted(prod):
-            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    best = None
-    for k in prod:
-        if best is None or prod[k] > prod[best]:
-            best = k
-    if n > 0:
-        avg = tot / n
-    else:
-        avg = 0
-
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+    Raises ValueError if fmt is not a supported format.
+    """
+    render = renderer_for(fmt)
+    return render(summarize(read_sales(path)))
diff -ruN before/report/sales.py after/report/sales.py
--- before/report/sales.py
+++ after/report/sales.py
@@ -0,0 +1,106 @@
+"""Reading sales records from CSV and aggregating them into report figures."""
+
+import csv
+from collections.abc import Iterable
+from dataclasses import dataclass
+from os import PathLike
+from typing import TypeVar
+
+_Amount = TypeVar("_Amount", int, float)
+
+
+@dataclass(frozen=True)
+class Sale:
+    region: str
+    product: str
+    units: int
+    unit_price: float
+
+    @property
+    def revenue(self) -> float:
+        return self.units * self.unit_price
+
+
+@dataclass(frozen=True)
+class RegionTotal:
+    name: str
+    revenue: float
+
+
+@dataclass(frozen=True)
+class ProductTotal:
+    name: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    """Figures shown in every report format.
+
+    Totals are sorted by name. top_product is None when there are no sales.
+    """
+
+    region_totals: tuple[RegionTotal, ...]
+    product_totals: tuple[ProductTotal, ...]
+    top_product: str | None
+    average_order_value: float
+
+
+def read_sales(path: str | PathLike[str]) -> list[Sale]:
+    with open(path) as csv_file:
+        rows = list(csv.DictReader(csv_file))
+    return [_parse_sale(row) for row in rows]
+
+
+def _parse_sale(row: dict[str, str]) -> Sale:
+    return Sale(
+        region=row["region"],
+        product=row["product"],
+        units=int(row["units"]),
+        unit_price=float(row["unit_price"]),
+    )
+
+
+def summarize(sales: list[Sale]) -> SalesSummary:
+    revenue_by_region = _totals_by_name((sale.region, sale.revenue) for sale in sales)
+    revenue_by_product = _totals_by_name((sale.product, sale.revenue) for sale in sales)
+    units_by_product = _totals_by_name((sale.product, sale.units) for sale in sales)
+    return SalesSummary(
+        region_totals=tuple(
+            RegionTotal(region, revenue_by_region[region])
+            for region in sorted(revenue_by_region)
+        ),
+        product_totals=tuple(
+            ProductTotal(
+                product, units_by_product[product], revenue_by_product[product]
+            )
+            for product in sorted(revenue_by_product)
+        ),
+        # max() keeps the first of equal values: a tie goes to the first product listed.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=_average_order_value(sales),
+    )
+
+
+def _totals_by_name(amounts: Iterable[tuple[str, _Amount]]) -> dict[str, _Amount]:
+    # Revenue is a float, added one row at a time in file order and seeded with the
+    # first amount rather than 0, so existing reports stay identical down to rounding
+    # and "-0.00". Decimal, sum() (compensated on Python 3.12+) or a 0.0 seed would
+    # each change some printed totals.
+    totals: dict[str, _Amount] = {}
+    for name, amount in amounts:
+        if name in totals:
+            totals[name] += amount
+        else:
+            totals[name] = amount
+    return totals
+
+
+def _average_order_value(sales: list[Sale]) -> float:
+    if not sales:
+        return 0.0
+    total = 0.0
+    for sale in sales:  # Not sum(): see _totals_by_name.
+        total += sale.revenue
+    return total / len(sales)
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,180 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE_CSV = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
+CSV_HEADER = "date,region,product,units,unit_price\n"
+
+
+def write_sales_csv(directory, *rows):
+    path = directory / "sales.csv"
+    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows))
+    return path
+
+
+def test_text_report_for_sample():
+    expected = (
+        "SALES REPORT\n"
+        "========================================\n"
+        "\n"
+        "Totals by region\n"
+        "----------------------------------------\n"
+        "East                               57.48\n"
+        "North                              44.99\n"
+        "South                              74.47\n"
+        "\n"
+        "Totals by product\n"
+        "----------------------------------------\n"
+        "Doohickey                  2       14.50\n"
+        "Gadget                     6      119.94\n"
+        "Widget                    17       42.50\n"
+        "\n"
+        "Top product: Gadget\n"
+        "Average order value: 29.49\n"
+    )
+
+    assert generate(SAMPLE_CSV, "text") == expected
+
+
+def test_html_report_for_sample():
+    expected = (
+        "<html><body>\n"
+        "<h1>Sales report</h1>\n"
+        "<h2>Totals by region</h2>\n"
+        "<table>\n"
+        "<tr><th>Region</th><th>Revenue</th></tr>\n"
+        "<tr><td>East</td><td>57.48</td></tr>\n"
+        "<tr><td>North</td><td>44.99</td></tr>\n"
+        "<tr><td>South</td><td>74.47</td></tr>\n"
+        "</table>\n"
+        "<h2>Totals by product</h2>\n"
+        "<table>\n"
+        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
+        "<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>\n"
+        "<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>\n"
+        "<tr><td>Widget</td><td>17</td><td>42.50</td></tr>\n"
+        "</table>\n"
+        "<p>Top product: Gadget</p>\n"
+        "<p>Average order value: 29.49</p>\n"
+        "</body></html>\n"
+    )
+
+    assert generate(SAMPLE_CSV, "html") == expected
+
+
+def test_markdown_report_for_sample():
+    expected = (
+        "# Sales report\n"
+        "\n"
+        "## Totals by region\n"
+        "\n"
+        "| Region | Revenue |\n"
+        "|---|---|\n"
+        "| East | 57.48 |\n"
+        "| North | 44.99 |\n"
+        "| South | 74.47 |\n"
+        "\n"
+        "## Totals by product\n"
+        "\n"
+        "| Product | Units | Revenue |\n"
+        "|---|---|---|\n"
+        "| Doohickey | 2 | 14.50 |\n"
+        "| Gadget | 6 | 119.94 |\n"
+        "| Widget | 17 | 42.50 |\n"
+        "\n"
+        "**Top product:** Gadget\n"
+        "\n"
+        "**Average order value:** 29.49\n"
+    )
+
+    assert generate(SAMPLE_CSV, "md") == expected
+
+
+def test_text_report_without_sales(tmp_path):
+    expected = (
+        "SALES REPORT\n"
+        "========================================\n"
+        "\n"
+        "Totals by region\n"
+        "----------------------------------------\n"
+        "\n"
+        "Totals by product\n"
+        "----------------------------------------\n"
+        "\n"
+        "Top product: None\n"
+        "Average order value: 0.00\n"
+    )
+
+    assert generate(write_sales_csv(tmp_path), "text") == expected
+
+
+def test_html_report_without_sales(tmp_path):
+    expected = (
+        "<html><body>\n"
+        "<h1>Sales report</h1>\n"
+        "<h2>Totals by region</h2>\n"
+        "<table>\n"
+        "<tr><th>Region</th><th>Revenue</th></tr>\n"
+        "</table>\n"
+        "<h2>Totals by product</h2>\n"
+        "<table>\n"
+        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
+        "</table>\n"
+        "<p>Top product: None</p>\n"
+        "<p>Average order value: 0.00</p>\n"
+        "</body></html>\n"
+    )
+
+    assert generate(write_sales_csv(tmp_path), "html") == expected
+
+
+def test_markdown_report_without_sales(tmp_path):
+    expected = (
+        "# Sales report\n"
+        "\n"
+        "## Totals by region\n"
+        "\n"
+        "| Region | Revenue |\n"
+        "|---|---|\n"
+        "\n"
+        "## Totals by product\n"
+        "\n"
+        "| Product | Units | Revenue |\n"
+        "|---|---|---|\n"
+        "\n"
+        "**Top product:** None\n"
+        "\n"
+        "**Average order value:** 0.00\n"
+    )
+
+    assert generate(write_sales_csv(tmp_path), "md") == expected
+
+
+def test_top_product_tie_goes_to_first_product_in_file(tmp_path):
+    path = write_sales_csv(
+        tmp_path,
+        "2026-01-01,West,Zed,1,5.00",
+        "2026-01-01,West,Alpha,2,2.50",
+    )
+
+    assert "Top product: Zed\n" in generate(path, "text")
+
+
+def test_revenue_is_summed_in_file_order(tmp_path):
+    # Compensated summation (e.g. sum() on Python 3.12+) would print 1.00 here.
+    path = write_sales_csv(
+        tmp_path,
+        "2026-01-01,East,Widget,1,1e16",
+        "2026-01-01,East,Widget,1,1",
+        "2026-01-01,East,Widget,1,-1e16",
+    )
+
+    assert "East                                0.00\n" in generate(path, "text")
+
+
+@pytest.mark.parametrize("fmt", ["pdf", "TEXT", ""])
+def test_unknown_format_raises(fmt):
+    with pytest.raises(ValueError, match="bad format"):
+        generate(SAMPLE_CSV, fmt)
```

### Implementation 2

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,210 @@
+"""Sales report built from a CSV of orders, rendered as text, HTML or Markdown.
+
+The work happens in three steps, so each can change on its own:
+
+1. ``_summarize`` computes the figures from the CSV rows (``SalesSummary``).
+2. ``_build_content`` turns the figures into format-neutral content: a title,
+   tables of already-formatted cells, and labelled facts (``ReportContent``).
+   Labels, number formatting and row order are decided here, once, for every
+   format.
+3. A renderer lays that content out in one output format.
+
+To add a format, write a ``_render_<name>(content) -> str`` function and add it
+to ``_RENDERERS``.
+"""
+
 import csv
+from collections.abc import Callable, Iterable
+from dataclasses import dataclass
+
+TITLE = "Sales report"
+TEXT_WIDTH = 40
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    revenue_by_region: dict[str, float]
+    units_by_product: dict[str, int]
+    revenue_by_product: dict[str, float]
+    top_product: str | None
+    average_order_value: float
+
+
+@dataclass(frozen=True)
+class Column:
+    header: str
+    text_width: int  # characters this column takes in the plain-text layout
+
+
+@dataclass(frozen=True)
+class Table:
+    heading: str
+    columns: tuple[Column, ...]
+    rows: list[tuple[str, ...]]
+
+
+@dataclass(frozen=True)
+class ReportContent:
+    title: str
+    tables: list[Table]
+    facts: list[tuple[str, str]]  # (label, value) pairs
 
 
 def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
-
-    reg = {}
-    prod = {}
-    units = {}
-    n = 0
-    tot = 0
+    """Return the sales report for the orders CSV at ``path``.
+
+    ``fmt`` is one of the keys of ``_RENDERERS`` ("text", "html" or "md");
+    any other value raises ``ValueError`` before the file is read.
+    """
+    render = _renderer_for(fmt)
+    return render(_build_content(_summarize(_read_rows(path))))
+
+
+def _read_rows(path: str) -> list[dict[str, str]]:
+    with open(path) as f:
+        return list(csv.DictReader(f))
+
+
+def _summarize(rows: list[dict[str, str]]) -> SalesSummary:
+    revenue_by_region: dict[str, float] = {}
+    revenue_by_product: dict[str, float] = {}
+    units_by_product: dict[str, int] = {}
+    total_revenue = 0.0
     for row in rows:
-        u = int(row["units"])
-        p = float(row["unit_price"])
-        v = u * p
-        n = n + 1
-        tot = tot + v
-        if row["region"] in reg:
-            reg[row["region"]] = reg[row["region"]] + v
-        else:
-            reg[row["region"]] = v
-        if row["product"] in prod:
-            prod[row["product"]] = prod[row["product"]] + v
-            units[row["product"]] = units[row["product"]] + u
-        else:
-            prod[row["product"]] = v
-            units[row["product"]] = u
-
-    out = ""
-    if fmt == "text":
-        out = out + "SALES REPORT\n"
-        out = out + "=" * 40 + "\n"
-    elif fmt == "html":
-        out = out + "<html><body>\n"
-        out = out + "<h1>Sales report</h1>\n"
-    else:
-        raise Exception("bad format")
-
-    if fmt == "text":
-        out = out + "\nTotals by region\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(reg):
-            out = out + k.ljust(20) + ("%.2f" % reg[k]).rjust(20) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by region</h2>\n<table>\n"
-        out = out + "<tr><th>Region</th><th>Revenue</th></tr>\n"
-        for k in sorted(reg):
-            out = out + "<tr><td>" + k + "</td><td>" + "%.2f" % reg[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    if fmt == "text":
-        out = out + "\nTotals by product\n"
-        out = out + "-" * 40 + "\n"
-        for k in sorted(prod):
-            out = out + k.ljust(20) + str(units[k]).rjust(8) + ("%.2f" % prod[k]).rjust(12) + "\n"
-    elif fmt == "html":
-        out = out + "<h2>Totals by product</h2>\n<table>\n"
-        out = out + "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
-        for k in sorted(prod):
-            out = out + "<tr><td>" + k + "</td><td>" + str(units[k]) + "</td><td>" + "%.2f" % prod[k] + "</td></tr>\n"
-        out = out + "</table>\n"
-
-    best = None
-    for k in prod:
-        if best is None or prod[k] > prod[best]:
-            best = k
-    if n > 0:
-        avg = tot / n
-    else:
-        avg = 0
-
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+        units = int(row["units"])
+        revenue = units * float(row["unit_price"])
+        # Plain left-to-right addition on purpose: sum() uses compensated
+        # summation since Python 3.12, which could change the rounded output.
+        total_revenue += revenue
+        _add(revenue_by_region, row["region"], revenue)
+        _add(revenue_by_product, row["product"], revenue)
+        _add(units_by_product, row["product"], units)
+
+    return SalesSummary(
+        revenue_by_region=revenue_by_region,
+        units_by_product=units_by_product,
+        revenue_by_product=revenue_by_product,
+        # max() keeps the first product seen when revenues tie.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / len(rows) if rows else 0.0,
+    )
+
+
+def _add(totals: dict, key: str, amount: float) -> None:
+    # Start from the first amount rather than from 0: 0 + -0.0 is 0.0, which
+    # would print a total of -0.0 as "0.00" instead of "-0.00".
+    totals[key] = totals[key] + amount if key in totals else amount
+
+
+def _build_content(summary: SalesSummary) -> ReportContent:
+    regions = Table(
+        heading="Totals by region",
+        columns=(Column("Region", 20), Column("Revenue", 20)),
+        rows=[
+            (region, _money(summary.revenue_by_region[region]))
+            for region in sorted(summary.revenue_by_region)
+        ],
+    )
+    products = Table(
+        heading="Totals by product",
+        columns=(Column("Product", 20), Column("Units", 8), Column("Revenue", 12)),
+        rows=[
+            (
+                product,
+                str(summary.units_by_product[product]),
+                _money(summary.revenue_by_product[product]),
+            )
+            for product in sorted(summary.revenue_by_product)
+        ],
+    )
+    facts = [
+        ("Top product", str(summary.top_product)),
+        ("Average order value", _money(summary.average_order_value)),
+    ]
+    return ReportContent(title=TITLE, tables=[regions, products], facts=facts)
+
+
+def _money(amount: float) -> str:
+    return f"{amount:.2f}"
+
+
+# --- Renderers: each lays out a ReportContent in one format. ---------------
+
+
+def _render_text(content: ReportContent) -> str:
+    banner = content.title.upper() + "\n" + "=" * TEXT_WIDTH
+    facts = "\n".join(f"{label}: {value}" for label, value in content.facts)
+    blocks = [banner, *map(_text_table, content.tables), facts]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _text_table(table: Table) -> str:
+    # Headers are not shown; the first column is left-aligned, the rest right-aligned.
+    widths = [column.text_width for column in table.columns]
+    lines = [table.heading, "-" * TEXT_WIDTH]
+    for first, *rest in table.rows:
+        cells = [first.ljust(widths[0])]
+        cells += [cell.rjust(width) for cell, width in zip(rest, widths[1:])]
+        lines.append("".join(cells))
+    return "\n".join(lines)
+
+
+def _render_html(content: ReportContent) -> str:
+    lines = ["<html><body>", f"<h1>{content.title}</h1>"]
+    for table in content.tables:
+        lines.append(f"<h2>{table.heading}</h2>")
+        lines += _html_table(table)
+    lines += [f"<p>{label}: {value}</p>" for label, value in content.facts]
+    lines.append("</body></html>")
+    return "\n".join(lines) + "\n"
+
+
+def _html_table(table: Table) -> list[str]:
+    return [
+        "<table>",
+        _html_row("th", [column.header for column in table.columns]),
+        *(_html_row("td", row) for row in table.rows),
+        "</table>",
+    ]
+
+
+def _html_row(tag: str, cells: Iterable[str]) -> str:
+    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"
+
+
+def _render_markdown(content: ReportContent) -> str:
+    blocks = [f"# {content.title}"]
+    for table in content.tables:
+        blocks += [f"## {table.heading}", _markdown_table(table)]
+    blocks += [f"**{label}:** {value}" for label, value in content.facts]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _markdown_table(table: Table) -> str:
+    lines = [
+        _markdown_row([column.header for column in table.columns]),
+        "|" + "---|" * len(table.columns),
+    ]
+    lines += [_markdown_row(row) for row in table.rows]
+    return "\n".join(lines)
+
+
+def _markdown_row(cells: Iterable[str]) -> str:
+    return "| " + " | ".join(cells) + " |"
+
+
+Renderer = Callable[[ReportContent], str]
+
+_RENDERERS: dict[str, Renderer] = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
+
+
+def _renderer_for(fmt: str) -> Renderer:
+    try:
+        return _RENDERERS[fmt]
+    except KeyError:
+        expected = ", ".join(_RENDERERS)
+        raise ValueError(f"bad format {fmt!r}; expected one of: {expected}") from None
diff -ruN before/tests/test_report_output.py after/tests/test_report_output.py
--- before/tests/test_report_output.py
+++ after/tests/test_report_output.py
@@ -0,0 +1,122 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = str(Path(__file__).resolve().parent.parent / "samples" / "sales.csv")
+
+# Captured from report.py before the Markdown refactor; must not change.
+EXPECTED_TEXT = """\
+SALES REPORT
+========================================
+
+Totals by region
+----------------------------------------
+East                               57.48
+North                              44.99
+South                              74.47
+
+Totals by product
+----------------------------------------
+Doohickey                  2       14.50
+Gadget                     6      119.94
+Widget                    17       42.50
+
+Top product: Gadget
+Average order value: 29.49
+"""
+
+EXPECTED_HTML = """\
+<html><body>
+<h1>Sales report</h1>
+<h2>Totals by region</h2>
+<table>
+<tr><th>Region</th><th>Revenue</th></tr>
+<tr><td>East</td><td>57.48</td></tr>
+<tr><td>North</td><td>44.99</td></tr>
+<tr><td>South</td><td>74.47</td></tr>
+</table>
+<h2>Totals by product</h2>
+<table>
+<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>
+<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>
+<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>
+<tr><td>Widget</td><td>17</td><td>42.50</td></tr>
+</table>
+<p>Top product: Gadget</p>
+<p>Average order value: 29.49</p>
+</body></html>
+"""
+
+EXPECTED_MD = """\
+# Sales report
+
+## Totals by region
+
+| Region | Revenue |
+|---|---|
+| East | 57.48 |
+| North | 44.99 |
+| South | 74.47 |
+
+## Totals by product
+
+| Product | Units | Revenue |
+|---|---|---|
+| Doohickey | 2 | 14.50 |
+| Gadget | 6 | 119.94 |
+| Widget | 17 | 42.50 |
+
+**Top product:** Gadget
+
+**Average order value:** 29.49
+"""
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", EXPECTED_TEXT), ("html", EXPECTED_HTML), ("md", EXPECTED_MD)],
+)
+def test_sample_report(fmt, expected):
+    assert generate(SAMPLE, fmt) == expected
+
+
+def test_empty_csv(tmp_path):
+    path = tmp_path / "empty.csv"
+    path.write_text("date,region,product,units,unit_price\n")
+
+    assert generate(str(path), "text").endswith(
+        "Top product: None\nAverage order value: 0.00\n"
+    )
+    assert generate(str(path), "md") == (
+        "# Sales report\n\n"
+        "## Totals by region\n\n| Region | Revenue |\n|---|---|\n\n"
+        "## Totals by product\n\n| Product | Units | Revenue |\n|---|---|---|\n\n"
+        "**Top product:** None\n\n"
+        "**Average order value:** 0.00\n"
+    )
+
+
+def test_top_product_tie_keeps_first_seen(tmp_path):
+    path = tmp_path / "tie.csv"
+    path.write_text(
+        "date,region,product,units,unit_price\n"
+        "d,North,Zed,1,3.00\n"
+        "d,North,Abe,2,1.50\n"
+    )
+
+    assert "**Top product:** Zed\n" in generate(str(path), "md")
+
+
+def test_negative_zero_total_keeps_its_sign(tmp_path):
+    path = tmp_path / "zero.csv"
+    path.write_text("date,region,product,units,unit_price\nd,North,Widget,0,-1.00\n")
+
+    assert "North                              -0.00\n" in generate(str(path), "text")
+
+
+@pytest.mark.parametrize("fmt", ["pdf", "", "MD", "markdown"])
+def test_unknown_format_raises_before_reading_the_file(fmt):
+    with pytest.raises(ValueError, match="bad format"):
+        generate("does-not-exist.csv", fmt)
```

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
@@ -1,84 +1,222 @@
+"""Sales report generation.
+
+A report is built in two independent steps:
+
+1. ``summarize`` turns the CSV rows into a format-neutral ``SalesSummary``.
+2. A renderer turns that summary into a string. Renderers are registered in
+   ``RENDERERS`` under their format name.
+
+To add a format, write a ``render_<name>(summary) -> str`` function and register
+it in ``RENDERERS``. Build table rows with ``_region_rows`` / ``_product_rows`` so
+every format shows the same values in the same order.
+"""
+
+from __future__ import annotations
+
 import csv
+import os
+from typing import Callable, Mapping, NamedTuple, Sequence
+
+TITLE = "Sales report"
+REGION_HEADING = "Totals by region"
+REGION_COLUMNS = ("Region", "Revenue")
+PRODUCT_HEADING = "Totals by product"
+PRODUCT_COLUMNS = ("Product", "Units", "Revenue")
+TOP_PRODUCT_LABEL = "Top product"
+AVERAGE_ORDER_LABEL = "Average order value"
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
 
+class SalesSummary(NamedTuple):
+    regions: list[RegionTotal]  # sorted by region name
+    products: list[ProductTotal]  # sorted by product name
+    top_product: str | None  # highest revenue; on a tie, the first one in the file
+    average_order_value: float
 
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
+
+def generate(path: str | os.PathLike, fmt: str) -> str:
+    """Return the sales report for the CSV at ``path`` in format ``fmt``.
+
+    Raises ``ValueError`` if ``fmt`` is not a key of ``RENDERERS``.
+    """
+    render = _renderer_for(fmt)
+    return render(summarize(_read_rows(path)))
+
+
+# --- Data -------------------------------------------------------------------
+
+
+def _read_rows(path: str | os.PathLike) -> list[dict[str, str]]:
+    # open() keeps its default newline/encoding handling on purpose: changing it
+    # would change how some files are parsed, and with it the report output.
+    with open(path) as f:
+        return list(csv.DictReader(f))
+
+
+def summarize(rows: Sequence[Mapping[str, str]]) -> SalesSummary:
+    revenue_by_region: dict[str, float] = {}
+    revenue_by_product: dict[str, float] = {}
+    units_by_product: dict[str, int] = {}
+    # A running total in file order, not sum(): since Python 3.12 sum() rounds
+    # floats differently, which could change the last printed digit.
+    total_revenue = 0
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
+        total_revenue += revenue
+        _add(revenue_by_region, row["region"], revenue)
+        _add(revenue_by_product, row["product"], revenue)
+        _add(units_by_product, row["product"], units)
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
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / len(rows) if rows else 0,
+    )
+
+
+def _add(totals: dict, key: str, amount: float) -> None:
+    # Start from the first amount rather than from 0, so a total of -0.0 still
+    # prints as "-0.00".
+    totals[key] = totals[key] + amount if key in totals else amount
+
+
+# --- Formats ----------------------------------------------------------------
+
+
+def render_text(summary: SalesSummary) -> str:
+    return _join_lines([
+        TITLE.upper(),
+        "=" * 40,
+        "",
+        REGION_HEADING,
+        "-" * 40,
+        *(_text_row(cells, widths=(20, 20)) for cells in _region_rows(summary)),
+        "",
+        PRODUCT_HEADING,
+        "-" * 40,
+        *(_text_row(cells, widths=(20, 8, 12)) for cells in _product_rows(summary)),
+        "",
+        f"{TOP_PRODUCT_LABEL}: {summary.top_product}",
+        f"{AVERAGE_ORDER_LABEL}: {_money(summary.average_order_value)}",
+    ])
+
+
+def render_html(summary: SalesSummary) -> str:
+    return _join_lines([
+        "<html><body>",
+        f"<h1>{TITLE}</h1>",
+        f"<h2>{REGION_HEADING}</h2>",
+        *_html_table(REGION_COLUMNS, _region_rows(summary)),
+        f"<h2>{PRODUCT_HEADING}</h2>",
+        *_html_table(PRODUCT_COLUMNS, _product_rows(summary)),
+        f"<p>{TOP_PRODUCT_LABEL}: {summary.top_product}</p>",
+        f"<p>{AVERAGE_ORDER_LABEL}: {_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ])
+
+
+def render_markdown(summary: SalesSummary) -> str:
+    return _join_lines([
+        f"# {TITLE}",
+        "",
+        f"## {REGION_HEADING}",
+        "",
+        *_markdown_table(REGION_COLUMNS, _region_rows(summary)),
+        "",
+        f"## {PRODUCT_HEADING}",
+        "",
+        *_markdown_table(PRODUCT_COLUMNS, _product_rows(summary)),
+        "",
+        f"**{TOP_PRODUCT_LABEL}:** {summary.top_product}",
+        "",
+        f"**{AVERAGE_ORDER_LABEL}:** {_money(summary.average_order_value)}",
+    ])
+
+
+Renderer = Callable[[SalesSummary], str]
+
+RENDERERS: dict[str, Renderer] = {
+    "text": render_text,
+    "html": render_html,
+    "md": render_markdown,
+}
+
+
+def _renderer_for(fmt: str) -> Renderer:
+    try:
+        return RENDERERS[fmt]
+    except KeyError:
+        known = ", ".join(repr(name) for name in RENDERERS)
+        raise ValueError(f"unknown format {fmt!r}; expected one of {known}") from None
+
+
+# --- Helpers shared by the formats -------------------------------------------
+
+
+def _money(amount: float) -> str:
+    return "%.2f" % amount
+
+
+def _region_rows(summary: SalesSummary) -> list[tuple[str, ...]]:
+    return [(t.region, _money(t.revenue)) for t in summary.regions]
+
+
+def _product_rows(summary: SalesSummary) -> list[tuple[str, ...]]:
+    return [(t.product, str(t.units), _money(t.revenue)) for t in summary.products]
+
+
+def _join_lines(lines: Sequence[str]) -> str:
+    return "".join(line + "\n" for line in lines)
+
+
+def _text_row(cells: Sequence[str], widths: Sequence[int]) -> str:
+    """Pad each cell to its width: the first left-aligned, the rest right-aligned."""
+    first, *rest = cells
+    first_width, *rest_widths = widths
+    return first.ljust(first_width) + "".join(
+        cell.rjust(width) for cell, width in zip(rest, rest_widths)
+    )
+
+
+def _html_table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
+    return [
+        "<table>",
+        _html_row("th", columns),
+        *(_html_row("td", cells) for cells in rows),
+        "</table>",
+    ]
+
+
+def _html_row(tag: str, cells: Sequence[str]) -> str:
+    open_tag, close_tag = f"<{tag}>", f"</{tag}>"
+    return "<tr>" + "".join(open_tag + cell + close_tag for cell in cells) + "</tr>"
+
+
+def _markdown_table(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
+    return [
+        _markdown_row(columns),
+        "|" + "---|" * len(columns),
+        *(_markdown_row(cells) for cells in rows),
+    ]
+
+
+def _markdown_row(cells: Sequence[str]) -> str:
+    return "| " + " | ".join(cells) + " |"
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,96 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
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
+def test_empty_report(tmp_path):
+    path = tmp_path / "empty.csv"
+    path.write_text("date,region,product,units,unit_price\n")
+
+    assert generate(path, "md").endswith(
+        "| Product | Units | Revenue |\n|---|---|---|\n\n"
+        "**Top product:** None\n\n**Average order value:** 0.00\n"
+    )
+
+
+def test_unknown_format_raises():
+    with pytest.raises(ValueError, match="unknown format 'pdf'"):
+        generate(SAMPLE, "pdf")
```

### Implementation 2

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,156 @@
 import csv
+from dataclasses import dataclass
 
 
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
+    if fmt not in _RENDERERS:
+        raise ValueError(f"unknown report format {fmt!r}, expected one of: {', '.join(_RENDERERS)}")
+    summary = _summarize(_read_rows(path))
+    return _RENDERERS[fmt](summary)
+
+
+@dataclass(frozen=True)
+class RegionTotal:
+    region: str
+    revenue: float
+
+
+@dataclass(frozen=True)
+class ProductTotal:
+    product: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    regions: list[RegionTotal]  # sorted by region
+    products: list[ProductTotal]  # sorted by product
+    top_product: str | None  # None when there are no sales; rendered as "None"
+    average_order_value: float
+
+
+def _read_rows(path):
+    with open(path) as f:
+        return list(csv.DictReader(f))
+
+
+def _summarize(rows):
+    # Printed totals depend on this exact accumulation: sum() rounds differently since Python 3.12,
+    # and starting the per-key totals from 0 would print a lone -0.0 as "0.00" instead of "-0.00".
+    revenue_by_region = {}
+    revenue_by_product = {}
+    units_by_product = {}
+    total_revenue = 0
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
+        total_revenue += revenue
+        _add_to_total(revenue_by_region, row["region"], revenue)
+        _add_to_total(revenue_by_product, row["product"], revenue)
+        _add_to_total(units_by_product, row["product"], units)
+
+    return SalesSummary(
+        regions=[RegionTotal(region, revenue_by_region[region]) for region in sorted(revenue_by_region)],
+        products=[
+            ProductTotal(product, units_by_product[product], revenue_by_product[product])
+            for product in sorted(revenue_by_product)
+        ],
+        # max() keeps the first of equal values, so a tie goes to the product seen first in the file.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / len(rows) if rows else 0,
+    )
+
+
+def _add_to_total(totals, key, amount):
+    totals[key] = totals[key] + amount if key in totals else amount
+
+
+def _format_money(amount):
+    return "%.2f" % amount
+
+
+def _render_text(summary):
+    lines = [
+        "SALES REPORT",
+        "=" * 40,
+        "",
+        "Totals by region",
+        "-" * 40,
+        *[total.region.ljust(20) + _format_money(total.revenue).rjust(20) for total in summary.regions],
+        "",
+        "Totals by product",
+        "-" * 40,
+        *[
+            total.product.ljust(20) + str(total.units).rjust(8) + _format_money(total.revenue).rjust(12)
+            for total in summary.products
+        ],
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_format_money(summary.average_order_value)}",
+    ]
+    return "\n".join(lines) + "\n"
+
+
+def _render_html(summary):
+    lines = [
+        "<html><body>",
+        "<h1>Sales report</h1>",
+        "<h2>Totals by region</h2>",
+        "<table>",
+        _html_row("th", ["Region", "Revenue"]),
+        *[_html_row("td", [total.region, _format_money(total.revenue)]) for total in summary.regions],
+        "</table>",
+        "<h2>Totals by product</h2>",
+        "<table>",
+        _html_row("th", ["Product", "Units", "Revenue"]),
+        *[
+            _html_row("td", [total.product, str(total.units), _format_money(total.revenue)])
+            for total in summary.products
+        ],
+        "</table>",
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ]
+    return "\n".join(lines) + "\n"
+
+
+def _html_row(cell_tag, cells):
+    opening, closing = f"<{cell_tag}>", f"</{cell_tag}>"
+    return "<tr>" + "".join(opening + cell + closing for cell in cells) + "</tr>"
+
+
+def _render_markdown(summary):
+    blocks = [
+        "# Sales report",
+        "## Totals by region",
+        _markdown_table(
+            ["Region", "Revenue"],
+            [[total.region, _format_money(total.revenue)] for total in summary.regions],
+        ),
+        "## Totals by product",
+        _markdown_table(
+            ["Product", "Units", "Revenue"],
+            [[total.product, str(total.units), _format_money(total.revenue)] for total in summary.products],
+        ),
+        f"**Top product:** {summary.top_product}",
+        f"**Average order value:** {_format_money(summary.average_order_value)}",
+    ]
+    return "\n\n".join(blocks) + "\n"
+
+
+def _markdown_table(headers, rows):
+    separator = "|" + "---|" * len(headers)
+    return "\n".join([_markdown_row(headers), separator, *[_markdown_row(row) for row in rows]])
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
@@ -0,0 +1,175 @@
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
+def write_csv(tmp_path, *rows):
+    path = tmp_path / "sales.csv"
+    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows))
+    return path
+
+
+FORMATS = ["text", "html", "md"]
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", SAMPLE_TEXT), ("html", SAMPLE_HTML), ("md", SAMPLE_MARKDOWN)],
+    ids=FORMATS,
+)
+def test_sample_report(fmt, expected):
+    assert generate(SAMPLE_CSV, fmt) == expected
+
+
+@pytest.mark.parametrize(
+    "fmt, expected",
+    [("text", EMPTY_TEXT), ("html", EMPTY_HTML), ("md", EMPTY_MARKDOWN)],
+    ids=FORMATS,
+)
+def test_report_without_sales_has_no_top_product_and_zero_average(tmp_path, fmt, expected):
+    assert generate(write_csv(tmp_path), fmt) == expected
+
+
+@pytest.mark.parametrize(
+    "fmt, expected_line",
+    [
+        ("text", "Top product: Zeta\n"),
+        ("html", "<p>Top product: Zeta</p>\n"),
+        ("md", "**Top product:** Zeta\n"),
+    ],
+    ids=FORMATS,
+)
+def test_top_product_tie_goes_to_the_product_seen_first(tmp_path, fmt, expected_line):
+    path = write_csv(tmp_path, "2026-01-01,West,Zeta,1,5.00", "2026-01-02,West,Alpha,1,5.00")
+
+    assert expected_line in generate(path, fmt)
+
+
+def test_single_negative_zero_revenue_keeps_its_sign(tmp_path):
+    path = write_csv(tmp_path, "2026-01-01,West,Freebie,-1,0.00")
+
+    assert "West                               -0.00\n" in generate(path, "text")
+
+
+def test_unknown_format_raises(tmp_path):
+    with pytest.raises(ValueError, match="'pdf'"):
+        generate(write_csv(tmp_path), "pdf")
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,147 @@
 import csv
+from dataclasses import dataclass
 
 
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
+    if fmt not in _RENDERERS:
+        raise ValueError(f"unknown format {fmt!r}, expected one of: {', '.join(_RENDERERS)}")
+    summary = _summarize(_read_rows(path))
+    return _RENDERERS[fmt](summary)
+
+
+@dataclass(frozen=True)
+class _SalesSummary:
+    totals_by_region: tuple[tuple[str, float], ...]  # (region, revenue), sorted by region
+    totals_by_product: tuple[tuple[str, int, float], ...]  # (product, units, revenue), sorted
+    top_product: str | None  # None when there are no sales
+    average_order_value: float
+
+
+def _read_rows(path):
+    with open(path) as f:
+        return list(csv.DictReader(f))
+
+
+def _summarize(rows):
+    revenue_by_region = {}
+    revenue_by_product = {}
+    units_by_product = {}
+    total_revenue = 0
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
+        units = int(row["units"])
+        revenue = units * float(row["unit_price"])
+        total_revenue += revenue
+        _add_to_total(revenue_by_region, row["region"], revenue)
+        _add_to_total(revenue_by_product, row["product"], revenue)
+        _add_to_total(units_by_product, row["product"], units)
+
+    return _SalesSummary(
+        totals_by_region=tuple(sorted(revenue_by_region.items())),
+        totals_by_product=tuple(
+            (product, units_by_product[product], revenue_by_product[product])
+            for product in sorted(revenue_by_product)
+        ),
+        # Ties go to the product that appears first in the file.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / len(rows) if rows else 0,
+    )
+
+
+def _add_to_total(totals, key, amount):
+    if key in totals:
+        totals[key] += amount
     else:
-        raise Exception("bad format")
+        totals[key] = amount  # not 0 + amount, which would turn -0.0 into 0.0
+
+
+def _render_text(summary):
+    lines = ["SALES REPORT", "=" * 40]
+    lines += ["", "Totals by region", "-" * 40]
+    lines += [region.ljust(20) + revenue.rjust(20) for region, revenue in _region_rows(summary)]
+    lines += ["", "Totals by product", "-" * 40]
+    lines += [
+        product.ljust(20) + units.rjust(8) + revenue.rjust(12)
+        for product, units, revenue in _product_rows(summary)
+    ]
+    lines += [
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_format_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _render_html(summary):
+    lines = ["<html><body>", "<h1>Sales report</h1>"]
+    lines += ["<h2>Totals by region</h2>"]
+    lines += _html_table(("Region", "Revenue"), _region_rows(summary))
+    lines += ["<h2>Totals by product</h2>"]
+    lines += _html_table(("Product", "Units", "Revenue"), _product_rows(summary))
+    lines += [
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ]
+    return _join_lines(lines)
+
+
+def _html_table(header, rows):
+    return (
+        ["<table>", _html_row("th", header)]
+        + [_html_row("td", row) for row in rows]
+        + ["</table>"]
+    )
+
+
+def _html_row(cell_tag, cells):
+    return "<tr>" + "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells) + "</tr>"
+
+
+def _render_markdown(summary):
+    lines = ["# Sales report"]
+    lines += ["", "## Totals by region", ""]
+    lines += _markdown_table(("Region", "Revenue"), _region_rows(summary))
+    lines += ["", "## Totals by product", ""]
+    lines += _markdown_table(("Product", "Units", "Revenue"), _product_rows(summary))
+    lines += [
+        "",
+        f"**Top product:** {summary.top_product}",
+        "",
+        f"**Average order value:** {_format_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _markdown_table(header, rows):
+    separator = "|" + "---|" * len(header)
+    return [_markdown_row(header), separator] + [_markdown_row(row) for row in rows]
+
+
+def _markdown_row(cells):
+    return "| " + " | ".join(cells) + " |"
+
+
+def _region_rows(summary):
+    return [(region, _format_money(revenue)) for region, revenue in summary.totals_by_region]
+
+
+def _product_rows(summary):
+    return [
+        (product, str(units), _format_money(revenue))
+        for product, units, revenue in summary.totals_by_product
+    ]
+
+
+def _format_money(amount):
+    return f"{amount:.2f}"
+
+
+def _join_lines(lines):
+    return "".join(line + "\n" for line in lines)
 
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
 
-    if fmt == "text":
-        out = out + "\nTop product: " + str(best) + "\n"
-        out = out + "Average order value: " + "%.2f" % avg + "\n"
-    elif fmt == "html":
-        out = out + "<p>Top product: " + str(best) + "</p>\n"
-        out = out + "<p>Average order value: " + "%.2f" % avg + "</p>\n"
-        out = out + "</body></html>\n"
-    return out
+_RENDERERS = {
+    "text": _render_text,
+    "html": _render_html,
+    "md": _render_markdown,
+}
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,157 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE_CSV = Path(__file__).parent.parent / "samples" / "sales.csv"
+CSV_HEADER = "date,region,product,units,unit_price\n"
+
+
+@pytest.fixture
+def empty_csv(tmp_path):
+    path = tmp_path / "empty.csv"
+    path.write_text(CSV_HEADER)
+    return path
+
+
+def test_text_report():
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
+def test_html_report():
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
+def test_markdown_report():
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
+def test_text_report_without_sales(empty_csv):
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
+def test_html_report_without_sales(empty_csv):
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
+def test_markdown_report_without_sales(empty_csv):
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
+def test_top_product_tie_goes_to_product_listed_first(tmp_path):
+    path = tmp_path / "tie.csv"
+    path.write_text(
+        CSV_HEADER
+        + "2026-01-01,North,Zed,1,5.00\n"
+        + "2026-01-02,South,Alpha,1,5.00\n"
+    )
+
+    assert "Top product: Zed\n" in generate(path, "text")
+
+
+def test_unknown_format_is_rejected():
+    with pytest.raises(ValueError, match="'pdf'"):
+        generate(SAMPLE_CSV, "pdf")
```

### Implementation 2

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,187 @@
+"""Sales report: read a sales CSV, summarise it, render it in one of several formats.
+
+The work is split into three steps so that each can change on its own:
+
+1. ``_read_rows`` loads the CSV.
+2. ``summarize`` turns the rows into a format-independent ``SalesSummary``.
+3. A renderer turns the summary into text. Renderers are listed in ``RENDERERS``.
+
+To add an output format, write a ``render_<name>(summary) -> str`` function and
+add it to ``RENDERERS``. Nothing else needs to change.
+"""
+
 import csv
+from typing import Callable, NamedTuple
 
 
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
+class RegionTotal(NamedTuple):
+    name: str
+    revenue: float
+
+
+class ProductTotal(NamedTuple):
+    name: str
+    units: int
+    revenue: float
+
+
+class SalesSummary(NamedTuple):
+    regions: list[RegionTotal]  # sorted by name
+    products: list[ProductTotal]  # sorted by name
+    top_product: str | None  # None when there are no rows
+    average_order_value: float
+
+
+# --- Input ------------------------------------------------------------------
+
+
+def _read_rows(path):
+    with open(path) as f:
+        return list(csv.DictReader(f))
+
+
+def _accumulate(totals, key, amount):
+    # The first amount is stored as is rather than added to a zero start
+    # value, so the totals are exactly what earlier versions produced
+    # (0 + -0.0 would otherwise turn "-0.00" into "0.00").
+    totals[key] = totals[key] + amount if key in totals else amount
+
+
+def summarize(rows):
+    revenue_by_region = {}
+    revenue_by_product = {}
+    units_by_product = {}
+    total_revenue = 0
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
+        # Add in row order with a plain loop: sum() uses compensated
+        # summation on Python 3.12+ and could change the rounded output.
+        total_revenue = total_revenue + revenue
+        _accumulate(revenue_by_region, row["region"], revenue)
+        _accumulate(revenue_by_product, row["product"], revenue)
+        _accumulate(units_by_product, row["product"], units)
+
+    # Ties go to the product seen first in the file.
+    top_product = max(revenue_by_product, key=revenue_by_product.get, default=None)
+    average = total_revenue / len(rows) if rows else 0.0
+
+    return SalesSummary(
+        regions=[RegionTotal(name, revenue_by_region[name]) for name in sorted(revenue_by_region)],
+        products=[
+            ProductTotal(name, units_by_product[name], revenue_by_product[name])
+            for name in sorted(revenue_by_product)
+        ],
+        top_product=top_product,
+        average_order_value=average,
+    )
+
+
+# --- Renderers --------------------------------------------------------------
+
+
+def _money(amount):
+    return "%.2f" % amount
+
+
+def _join_lines(lines):
+    return "".join(line + "\n" for line in lines)
+
+
+def render_text(summary):
+    rule_width = 40
+    lines = ["SALES REPORT", "=" * rule_width]
+
+    lines += ["", "Totals by region", "-" * rule_width]
+    for region in summary.regions:
+        lines.append(region.name.ljust(20) + _money(region.revenue).rjust(20))
+
+    lines += ["", "Totals by product", "-" * rule_width]
+    for product in summary.products:
+        lines.append(
+            product.name.ljust(20) + str(product.units).rjust(8) + _money(product.revenue).rjust(12)
+        )
+
+    lines += [
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _html_row(cell_tag, cells):
+    return "<tr>" + "".join(f"<{cell_tag}>{cell}</{cell_tag}>" for cell in cells) + "</tr>"
+
+
+def render_html(summary):
+    # Values are inserted unescaped, as they always have been.
+    lines = ["<html><body>", "<h1>Sales report</h1>"]
+
+    lines += ["<h2>Totals by region</h2>", "<table>", _html_row("th", ["Region", "Revenue"])]
+    for region in summary.regions:
+        lines.append(_html_row("td", [region.name, _money(region.revenue)]))
+    lines.append("</table>")
+
+    lines += ["<h2>Totals by product</h2>", "<table>", _html_row("th", ["Product", "Units", "Revenue"])]
+    for product in summary.products:
+        lines.append(_html_row("td", [product.name, str(product.units), _money(product.revenue)]))
+    lines.append("</table>")
+
+    lines += [
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ]
+    return _join_lines(lines)
+
+
+def _md_row(cells):
+    return "| " + " | ".join(cells) + " |"
+
+
+def _md_table(headers, rows):
+    separator = "|" + "---|" * len(headers)
+    return [_md_row(headers), separator] + [_md_row(row) for row in rows]
+
+
+def render_markdown(summary):
+    # Like the HTML renderer, values are inserted unescaped.
+    region_rows = [[region.name, _money(region.revenue)] for region in summary.regions]
+    product_rows = [
+        [product.name, str(product.units), _money(product.revenue)] for product in summary.products
+    ]
+    blocks = [
+        ["# Sales report"],
+        ["## Totals by region"],
+        _md_table(["Region", "Revenue"], region_rows),
+        ["## Totals by product"],
+        _md_table(["Product", "Units", "Revenue"], product_rows),
+        [f"**Top product:** {summary.top_product}"],
+        [f"**Average order value:** {_money(summary.average_order_value)}"],
+    ]
+    lines = []
+    for block in blocks:
+        if lines:
+            lines.append("")
+        lines += block
+    return _join_lines(lines)
+
+
+Renderer = Callable[[SalesSummary], str]
+
+RENDERERS: dict[str, Renderer] = {
+    "text": render_text,
+    "html": render_html,
+    "md": render_markdown,
+}
+
+
+# --- Entry point ------------------------------------------------------------
+
+
+def generate(path, fmt):
+    render = RENDERERS.get(fmt)
+    if render is None:
+        raise ValueError(f"bad format: {fmt!r} (expected one of: {', '.join(RENDERERS)})")
+    return render(summarize(_read_rows(path)))
diff -ruN before/tests/test_report_formats.py after/tests/test_report_formats.py
--- before/tests/test_report_formats.py
+++ after/tests/test_report_formats.py
@@ -0,0 +1,107 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = str(Path(__file__).resolve().parent.parent / "samples" / "sales.csv")
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
+def test_sample_output(fmt, expected):
+    assert generate(SAMPLE, fmt) == expected
+
+
+@pytest.mark.parametrize("fmt", ["pdf", "markdown", "TEXT", ""])
+def test_unknown_format_raises(fmt):
+    with pytest.raises(Exception, match="bad format"):
+        generate(SAMPLE, fmt)
+
+
+def test_empty_csv(tmp_path):
+    path = tmp_path / "empty.csv"
+    path.write_text("date,region,product,units,unit_price\n")
+    assert generate(str(path), "text").endswith("Top product: None\nAverage order value: 0.00\n")
+    assert generate(str(path), "md").endswith(
+        "| Product | Units | Revenue |\n|---|---|---|\n\n"
+        "**Top product:** None\n\n**Average order value:** 0.00\n"
+    )
+
+
+def test_top_product_tie_goes_to_first_in_file(tmp_path):
+    path = tmp_path / "tie.csv"
+    path.write_text(
+        "date,region,product,units,unit_price\n"
+        "d,R,Zed,1,5\n"
+        "d,R,Abe,1,5\n"
+    )
+    assert "**Top product:** Zed\n" in generate(str(path), "md")
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,164 @@
 import csv
+from dataclasses import dataclass
 
 
 def generate(path, fmt):
-    rows = []
-    f = open(path)
-    r = csv.DictReader(f)
-    for row in r:
-        rows.append(row)
-    f.close()
+    render = _RENDERERS.get(fmt)
+    if render is None:
+        raise ValueError(f"bad format {fmt!r}, expected one of: {', '.join(_RENDERERS)}")
+    return render(_summarize(_read_sales(path)))
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
+    def revenue(self):
+        return self.units * self.unit_price
+
+
+def _read_sales(path):
+    with open(path) as file:
+        return [
+            Sale(row["region"], row["product"], int(row["units"]), float(row["unit_price"]))
+            for row in csv.DictReader(file)
+        ]
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    region_totals: list[tuple[str, float]]  # (region, revenue), sorted by region
+    product_totals: list[tuple[str, int, float]]  # (product, units, revenue), sorted by product
+    top_product: str | None
+    average_order_value: float
+
+
+def _summarize(sales):
+    revenue_by_product = _revenue_by(sales, lambda sale: sale.product)
+    units_by_product = _units_by_product(sales)
+    return SalesSummary(
+        region_totals=sorted(_revenue_by(sales, lambda sale: sale.region).items()),
+        product_totals=[
+            (product, units_by_product[product], revenue)
+            for product, revenue in sorted(revenue_by_product.items())
+        ],
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=_average_order_value(sales),
+    )
+
+
+def _revenue_by(sales, group_of):
+    totals = {}
+    for sale in sales:
+        group = group_of(sale)
+        # Seed with the first revenue, not 0: 0 + -0.0 == 0.0 would print "0.00" instead of "-0.00".
+        totals[group] = totals[group] + sale.revenue if group in totals else sale.revenue
+    return totals
 
-    reg = {}
-    prod = {}
+
+def _units_by_product(sales):
     units = {}
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
+    for sale in sales:
+        units[sale.product] = units.get(sale.product, 0) + sale.units
+    return units
+
+
+def _average_order_value(sales):
+    if not sales:
+        return 0.0
+    # Not sum(): since Python 3.12 its compensated float summation can change the printed average.
+    total_revenue = 0
+    for sale in sales:
+        total_revenue += sale.revenue
+    return total_revenue / len(sales)
+
+
+def _render_text(summary):
+    return _join_lines([
+        "SALES REPORT",
+        "=" * 40,
+        "",
+        "Totals by region",
+        "-" * 40,
+        *(f"{region:<20}{_format_money(revenue):>20}" for region, revenue in summary.region_totals),
+        "",
+        "Totals by product",
+        "-" * 40,
+        *(
+            f"{product:<20}{units:>8}{_format_money(revenue):>12}"
+            for product, units, revenue in summary.product_totals
+        ),
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_format_money(summary.average_order_value)}",
+    ])
+
+
+def _render_html(summary):
+    return _join_lines([
+        "<html><body>",
+        "<h1>Sales report</h1>",
+        "<h2>Totals by region</h2>",
+        "<table>",
+        "<tr><th>Region</th><th>Revenue</th></tr>",
+        *(
+            f"<tr><td>{region}</td><td>{_format_money(revenue)}</td></tr>"
+            for region, revenue in summary.region_totals
+        ),
+        "</table>",
+        "<h2>Totals by product</h2>",
+        "<table>",
+        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>",
+        *(
+            f"<tr><td>{product}</td><td>{units}</td><td>{_format_money(revenue)}</td></tr>"
+            for product, units, revenue in summary.product_totals
+        ),
+        "</table>",
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ])
+
+
+def _render_markdown(summary):
+    return _join_lines([
+        "# Sales report",
+        "",
+        "## Totals by region",
+        "",
+        "| Region | Revenue |",
+        "|---|---|",
+        *(f"| {region} | {_format_money(revenue)} |" for region, revenue in summary.region_totals),
+        "",
+        "## Totals by product",
+        "",
+        "| Product | Units | Revenue |",
+        "|---|---|---|",
+        *(
+            f"| {product} | {units} | {_format_money(revenue)} |"
+            for product, units, revenue in summary.product_totals
+        ),
+        "",
+        f"**Top product:** {summary.top_product}",
+        "",
+        f"**Average order value:** {_format_money(summary.average_order_value)}",
+    ])
+
+
+def _format_money(amount):
+    return f"{amount:.2f}"
+
+
+def _join_lines(lines):
+    return "\n".join(lines) + "\n"
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
@@ -0,0 +1,129 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = Path(__file__).parent.parent / "samples" / "sales.csv"
+
+
+def write_sales(tmp_path, *rows):
+    path = tmp_path / "sales.csv"
+    path.write_text("\n".join(["date,region,product,units,unit_price", *rows]) + "\n")
+    return path
+
+
+def test_text_report_for_sample():
+    assert generate(SAMPLE, "text") == (
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
+    assert generate(SAMPLE, "html") == (
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
+    assert generate(SAMPLE, "md") == (
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
+def test_unknown_format_raises():
+    with pytest.raises(ValueError, match="bad format"):
+        generate(SAMPLE, "pdf")
+
+
+def test_text_report_without_sales(tmp_path):
+    assert generate(write_sales(tmp_path), "text") == (
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
+def test_top_product_tie_goes_to_first_product_in_file(tmp_path):
+    path = write_sales(tmp_path, "2026-01-01,North,Zeta,1,5.00", "2026-01-02,North,Alpha,1,5.00")
+
+    assert "<p>Top product: Zeta</p>\n" in generate(path, "html")
+
+
+def test_region_total_keeps_sign_of_negative_zero_revenue(tmp_path):
+    path = write_sales(tmp_path, "2026-01-01,North,Widget,0,-1.00")
+
+    assert "<tr><td>North</td><td>-0.00</td></tr>\n" in generate(path, "html")
+
+
+def test_average_order_value_adds_revenue_in_file_order(tmp_path):
+    path = write_sales(
+        tmp_path,
+        "2026-01-01,North,Widget,1,9.062",
+        "2026-01-02,North,Widget,1,5.63",
+        "2026-01-03,North,Widget,1,2.783",
+    )
+
+    assert "<p>Average order value: 5.83</p>\n" in generate(path, "html")
```

### Implementation 2

```diff
diff -ruN before/report/report.py after/report/report.py
--- before/report/report.py
+++ after/report/report.py
@@ -1,84 +1,232 @@
+"""Sales report: read a CSV of sales, summarise it, render it in a chosen format.
+
+The work is split into three independent steps:
+
+1. ``read_sales``  -- parse the CSV into ``Sale`` records.
+2. ``summarize``   -- compute every figure the report shows (``SalesSummary``).
+3. a renderer      -- turn a ``SalesSummary`` into text for one output format.
+
+To add an output format, write a ``render_<name>(summary) -> str`` function
+and register it in ``RENDERERS``. Renderers only lay out values; they never
+compute or re-sort them, so every format shows the same figures in the same
+order.
+"""
+
 import csv
+from collections.abc import Callable, Iterable
+from dataclasses import dataclass
+
+
+# --- Reading -----------------------------------------------------------------
+
+
+@dataclass(frozen=True)
+class Sale:
+    region: str
+    product: str
+    units: int
+    revenue: float
+
+
+def read_sales(path) -> list[Sale]:
+    with open(path) as f:
+        return [_parse_sale(row) for row in csv.DictReader(f)]
+
+
+def _parse_sale(row: dict[str, str]) -> Sale:
+    units = int(row["units"])
+    unit_price = float(row["unit_price"])
+    return Sale(
+        region=row["region"],
+        product=row["product"],
+        units=units,
+        revenue=units * unit_price,
+    )
+
+
+# --- Summarising -------------------------------------------------------------
+
+
+@dataclass(frozen=True)
+class RegionTotal:
+    region: str
+    revenue: float
+
+
+@dataclass(frozen=True)
+class ProductTotal:
+    product: str
+    units: int
+    revenue: float
+
+
+@dataclass(frozen=True)
+class SalesSummary:
+    regions: list[RegionTotal]  # sorted by region name
+    products: list[ProductTotal]  # sorted by product name
+    top_product: str | None  # None when there are no sales
+    average_order_value: float
+
+
+def summarize(sales: Iterable[Sale]) -> SalesSummary:
+    revenue_by_region: dict[str, float] = {}
+    revenue_by_product: dict[str, float] = {}
+    units_by_product: dict[str, int] = {}
+    order_count = 0
+    total_revenue = 0
+    for sale in sales:
+        order_count += 1
+        total_revenue += sale.revenue
+        _accumulate(revenue_by_region, sale.region, sale.revenue)
+        _accumulate(revenue_by_product, sale.product, sale.revenue)
+        _accumulate(units_by_product, sale.product, sale.units)
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
+        # On a tie, max() keeps the product that appeared first in the file.
+        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
+        average_order_value=total_revenue / order_count if order_count else 0,
+    )
+
+
+def _accumulate(totals: dict, key: str, amount) -> None:
+    # The first amount is stored as-is rather than added to 0.0, so a lone
+    # -0.0 revenue still prints as "-0.00", exactly as the report always has.
+    totals[key] = totals[key] + amount if key in totals else amount
+
+
+# --- Rendering ---------------------------------------------------------------
+
+
+def _money(amount: float) -> str:
+    return f"{amount:.2f}"
+
+
+def _join_lines(lines: Iterable[str]) -> str:
+    return "".join(line + "\n" for line in lines)
+
+
+TEXT_WIDTH = 40
+
+
+def render_text(summary: SalesSummary) -> str:
+    lines = ["SALES REPORT", "=" * TEXT_WIDTH]
+
+    lines += _text_heading("Totals by region")
+    for row in summary.regions:
+        lines.append(row.region.ljust(20) + _money(row.revenue).rjust(20))
+
+    lines += _text_heading("Totals by product")
+    for row in summary.products:
+        lines.append(
+            row.product.ljust(20) + str(row.units).rjust(8) + _money(row.revenue).rjust(12)
+        )
+
+    lines += [
+        "",
+        f"Top product: {summary.top_product}",
+        f"Average order value: {_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _text_heading(title: str) -> list[str]:
+    return ["", title, "-" * TEXT_WIDTH]
+
+
+def render_html(summary: SalesSummary) -> str:
+    # Values are inserted unescaped, as the report always has.
+    lines = ["<html><body>", "<h1>Sales report</h1>"]
+    lines += _html_table("Totals by region", ["Region", "Revenue"], _region_cells(summary))
+    lines += _html_table(
+        "Totals by product", ["Product", "Units", "Revenue"], _product_cells(summary)
+    )
+    lines += [
+        f"<p>Top product: {summary.top_product}</p>",
+        f"<p>Average order value: {_money(summary.average_order_value)}</p>",
+        "</body></html>",
+    ]
+    return _join_lines(lines)
+
+
+def _html_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
+    return [
+        f"<h2>{title}</h2>",
+        "<table>",
+        _html_row("th", headers),
+        *(_html_row("td", cells) for cells in rows),
+        "</table>",
+    ]
+
+
+def _html_row(tag: str, cells: list[str]) -> str:
+    return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"
+
+
+def render_markdown(summary: SalesSummary) -> str:
+    lines = ["# Sales report", ""]
+    lines += _markdown_table("Totals by region", ["Region", "Revenue"], _region_cells(summary))
+    lines += [""]
+    lines += _markdown_table(
+        "Totals by product", ["Product", "Units", "Revenue"], _product_cells(summary)
+    )
+    lines += [
+        "",
+        f"**Top product:** {summary.top_product}",
+        "",
+        f"**Average order value:** {_money(summary.average_order_value)}",
+    ]
+    return _join_lines(lines)
+
+
+def _markdown_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
+    return [
+        f"## {title}",
+        "",
+        _markdown_row(headers),
+        "|" + "|".join("---" for _ in headers) + "|",
+        *(_markdown_row(cells) for cells in rows),
+    ]
+
+
+def _markdown_row(cells: list[str]) -> str:
+    return "| " + " | ".join(cells) + " |"
+
+
+def _region_cells(summary: SalesSummary) -> list[list[str]]:
+    return [[row.region, _money(row.revenue)] for row in summary.regions]
+
+
+def _product_cells(summary: SalesSummary) -> list[list[str]]:
+    return [[row.product, str(row.units), _money(row.revenue)] for row in summary.products]
+
+
+# --- Entry point -------------------------------------------------------------
+
+
+RENDERERS: dict[str, Callable[[SalesSummary], str]] = {
+    "text": render_text,
+    "html": render_html,
+    "md": render_markdown,
+}
 
 
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
+    """Return the sales report for the CSV file at ``path`` in format ``fmt``.
+
+    ``fmt`` is one of the keys of ``RENDERERS``; anything else raises ValueError.
+    """
+    try:
+        render = RENDERERS[fmt]
+    except KeyError:
+        raise ValueError(
+            f"bad format {fmt!r}; expected one of: {', '.join(sorted(RENDERERS))}"
+        ) from None
+    return render(summarize(read_sales(path)))
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,110 @@
+from pathlib import Path
+
+import pytest
+
+from report.report import generate
+
+SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
+
+# Captured from the report before the refactoring; must not change.
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
+def test_unknown_format_raises():
+    with pytest.raises(ValueError, match="bad format"):
+        generate(SAMPLE, "xml")
+
+
+def test_empty_file_reports_no_top_product(tmp_path):
+    csv_path = tmp_path / "empty.csv"
+    csv_path.write_text("date,region,product,units,unit_price\n")
+
+    assert generate(csv_path, "md") == (
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
```

from pathlib import Path

import pytest

from report.report import generate

SAMPLE_CSV = Path(__file__).parent.parent / "samples" / "sales.csv"
CSV_HEADER = "date,region,product,units,unit_price\n"

SAMPLE_TEXT = """\
SALES REPORT
========================================

Totals by region
----------------------------------------
East                               57.48
North                              44.99
South                              74.47

Totals by product
----------------------------------------
Doohickey                  2       14.50
Gadget                     6      119.94
Widget                    17       42.50

Top product: Gadget
Average order value: 29.49
"""

SAMPLE_HTML = """\
<html><body>
<h1>Sales report</h1>
<h2>Totals by region</h2>
<table>
<tr><th>Region</th><th>Revenue</th></tr>
<tr><td>East</td><td>57.48</td></tr>
<tr><td>North</td><td>44.99</td></tr>
<tr><td>South</td><td>74.47</td></tr>
</table>
<h2>Totals by product</h2>
<table>
<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>
<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>
<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>
<tr><td>Widget</td><td>17</td><td>42.50</td></tr>
</table>
<p>Top product: Gadget</p>
<p>Average order value: 29.49</p>
</body></html>
"""

SAMPLE_MARKDOWN = """\
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
"""

EMPTY_TEXT = """\
SALES REPORT
========================================

Totals by region
----------------------------------------

Totals by product
----------------------------------------

Top product: None
Average order value: 0.00
"""

EMPTY_HTML = """\
<html><body>
<h1>Sales report</h1>
<h2>Totals by region</h2>
<table>
<tr><th>Region</th><th>Revenue</th></tr>
</table>
<h2>Totals by product</h2>
<table>
<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>
</table>
<p>Top product: None</p>
<p>Average order value: 0.00</p>
</body></html>
"""

EMPTY_MARKDOWN = """\
# Sales report

## Totals by region

| Region | Revenue |
|---|---|

## Totals by product

| Product | Units | Revenue |
|---|---|---|

**Top product:** None

**Average order value:** 0.00
"""


def write_csv(tmp_path, *rows):
    path = tmp_path / "sales.csv"
    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows))
    return path


FORMATS = ["text", "html", "md"]


@pytest.mark.parametrize(
    "fmt, expected",
    [("text", SAMPLE_TEXT), ("html", SAMPLE_HTML), ("md", SAMPLE_MARKDOWN)],
    ids=FORMATS,
)
def test_sample_report(fmt, expected):
    assert generate(SAMPLE_CSV, fmt) == expected


@pytest.mark.parametrize(
    "fmt, expected",
    [("text", EMPTY_TEXT), ("html", EMPTY_HTML), ("md", EMPTY_MARKDOWN)],
    ids=FORMATS,
)
def test_report_without_sales_has_no_top_product_and_zero_average(tmp_path, fmt, expected):
    assert generate(write_csv(tmp_path), fmt) == expected


@pytest.mark.parametrize(
    "fmt, expected_line",
    [
        ("text", "Top product: Zeta\n"),
        ("html", "<p>Top product: Zeta</p>\n"),
        ("md", "**Top product:** Zeta\n"),
    ],
    ids=FORMATS,
)
def test_top_product_tie_goes_to_the_product_seen_first(tmp_path, fmt, expected_line):
    path = write_csv(tmp_path, "2026-01-01,West,Zeta,1,5.00", "2026-01-02,West,Alpha,1,5.00")

    assert expected_line in generate(path, fmt)


def test_single_negative_zero_revenue_keeps_its_sign(tmp_path):
    path = write_csv(tmp_path, "2026-01-01,West,Freebie,-1,0.00")

    assert "West                               -0.00\n" in generate(path, "text")


def test_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError, match="'pdf'"):
        generate(write_csv(tmp_path), "pdf")

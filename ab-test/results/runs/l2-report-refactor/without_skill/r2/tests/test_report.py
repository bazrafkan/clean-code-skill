from pathlib import Path

import pytest

from report.report import generate

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"

# Captured from report.py before the Markdown refactor: these must never change.
EXPECTED_TEXT = (
    "SALES REPORT\n"
    "========================================\n"
    "\n"
    "Totals by region\n"
    "----------------------------------------\n"
    "East                               57.48\n"
    "North                              44.99\n"
    "South                              74.47\n"
    "\n"
    "Totals by product\n"
    "----------------------------------------\n"
    "Doohickey                  2       14.50\n"
    "Gadget                     6      119.94\n"
    "Widget                    17       42.50\n"
    "\n"
    "Top product: Gadget\n"
    "Average order value: 29.49\n"
)

EXPECTED_HTML = (
    "<html><body>\n"
    "<h1>Sales report</h1>\n"
    "<h2>Totals by region</h2>\n"
    "<table>\n"
    "<tr><th>Region</th><th>Revenue</th></tr>\n"
    "<tr><td>East</td><td>57.48</td></tr>\n"
    "<tr><td>North</td><td>44.99</td></tr>\n"
    "<tr><td>South</td><td>74.47</td></tr>\n"
    "</table>\n"
    "<h2>Totals by product</h2>\n"
    "<table>\n"
    "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
    "<tr><td>Doohickey</td><td>2</td><td>14.50</td></tr>\n"
    "<tr><td>Gadget</td><td>6</td><td>119.94</td></tr>\n"
    "<tr><td>Widget</td><td>17</td><td>42.50</td></tr>\n"
    "</table>\n"
    "<p>Top product: Gadget</p>\n"
    "<p>Average order value: 29.49</p>\n"
    "</body></html>\n"
)

EXPECTED_MD = """\
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


@pytest.mark.parametrize(
    "fmt, expected",
    [("text", EXPECTED_TEXT), ("html", EXPECTED_HTML), ("md", EXPECTED_MD)],
)
def test_sample_report(fmt, expected):
    assert generate(SAMPLE, fmt) == expected


def test_empty_csv_reports_no_top_product_and_zero_average(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("date,region,product,units,unit_price\n")

    report = generate(empty, "md")

    assert "**Top product:** None\n" in report
    assert report.endswith("**Average order value:** 0.00\n")


def test_unknown_format_raises():
    with pytest.raises(ValueError, match="bad format"):
        generate(SAMPLE, "pdf")

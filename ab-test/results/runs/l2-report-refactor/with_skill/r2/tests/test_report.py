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


def write_sales_csv(directory, *rows):
    path = directory / "sales.csv"
    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows))
    return path


@pytest.mark.parametrize(
    "fmt, expected",
    [("text", SAMPLE_TEXT), ("html", SAMPLE_HTML), ("md", SAMPLE_MARKDOWN)],
    ids=["text", "html", "md"],
)
def test_sample_report_in_each_format(fmt, expected):
    assert generate(SAMPLE_CSV, fmt) == expected


@pytest.mark.parametrize(
    "fmt, expected",
    [("text", EMPTY_TEXT), ("html", EMPTY_HTML), ("md", EMPTY_MARKDOWN)],
    ids=["text", "html", "md"],
)
def test_report_without_sales_in_each_format(tmp_path, fmt, expected):
    path = write_sales_csv(tmp_path)

    assert generate(path, fmt) == expected


def test_top_product_tie_goes_to_product_listed_first_in_file(tmp_path):
    path = write_sales_csv(
        tmp_path,
        "2026-01-01,North,Zeta,1,5.00",
        "2026-01-02,South,Alpha,1,5.00",
    )

    assert "Top product: Zeta\n" in generate(path, "text")


def test_average_order_value_adds_revenues_in_file_order(tmp_path):
    # Exact summation gives 1.10 / 4 = 0.275 -> "0.28". Adding left to right
    # gives 1.0999999999999999 / 4 -> "0.27", which the report has always shown.
    path = write_sales_csv(
        tmp_path,
        "2026-01-01,North,Widget,1,0.10",
        "2026-01-02,North,Widget,1,0.10",
        "2026-01-03,North,Widget,1,0.70",
        "2026-01-04,North,Widget,1,0.20",
    )

    assert "Average order value: 0.27\n" in generate(path, "text")


def test_zero_units_at_negative_price_show_as_negative_zero(tmp_path):
    path = write_sales_csv(tmp_path, "2026-01-01,West,Refund,0,-5.00")

    report = generate(path, "text")

    assert "West                               -0.00\n" in report
    assert "Refund                     0       -0.00\n" in report


@pytest.mark.parametrize("fmt", ["text", "html", "md"])
def test_row_missing_a_field_is_rejected(tmp_path, fmt):
    path = tmp_path / "sales.csv"
    path.write_text("units,unit_price,region,product\n3,2.50,North\n")

    with pytest.raises(ValueError, match="line 2 .* no product"):
        generate(path, fmt)


def test_unknown_format_raises_value_error_naming_it():
    with pytest.raises(ValueError, match="'pdf'"):
        generate(SAMPLE_CSV, "pdf")


def test_unknown_format_is_rejected_before_reading_the_file(tmp_path):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(ValueError):
        generate(missing_path, "pdf")

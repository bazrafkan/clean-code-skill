from pathlib import Path

import pytest

from report.report import generate

SAMPLE = str(Path(__file__).resolve().parent.parent / "samples" / "sales.csv")

EXPECTED_TEXT = """\
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

EXPECTED_HTML = """\
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
def test_sample_output(fmt, expected):
    assert generate(SAMPLE, fmt) == expected


@pytest.mark.parametrize("fmt", ["pdf", "markdown", "TEXT", ""])
def test_unknown_format_raises(fmt):
    with pytest.raises(Exception, match="bad format"):
        generate(SAMPLE, fmt)


def test_empty_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("date,region,product,units,unit_price\n")
    assert generate(str(path), "text").endswith("Top product: None\nAverage order value: 0.00\n")
    assert generate(str(path), "md").endswith(
        "| Product | Units | Revenue |\n|---|---|---|\n\n"
        "**Top product:** None\n\n**Average order value:** 0.00\n"
    )


def test_top_product_tie_goes_to_first_in_file(tmp_path):
    path = tmp_path / "tie.csv"
    path.write_text(
        "date,region,product,units,unit_price\n"
        "d,R,Zed,1,5\n"
        "d,R,Abe,1,5\n"
    )
    assert "**Top product:** Zed\n" in generate(str(path), "md")

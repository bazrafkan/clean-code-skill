from pathlib import Path

import pytest

from report.report import generate

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "samples" / "sales.csv"
CSV_HEADER = "date,region,product,units,unit_price\n"


def write_sales_csv(directory, *rows):
    path = directory / "sales.csv"
    path.write_text(CSV_HEADER + "".join(row + "\n" for row in rows))
    return path


def test_text_report_for_sample():
    expected = (
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

    assert generate(SAMPLE_CSV, "text") == expected


def test_html_report_for_sample():
    expected = (
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

    assert generate(SAMPLE_CSV, "html") == expected


def test_markdown_report_for_sample():
    expected = (
        "# Sales report\n"
        "\n"
        "## Totals by region\n"
        "\n"
        "| Region | Revenue |\n"
        "|---|---|\n"
        "| East | 57.48 |\n"
        "| North | 44.99 |\n"
        "| South | 74.47 |\n"
        "\n"
        "## Totals by product\n"
        "\n"
        "| Product | Units | Revenue |\n"
        "|---|---|---|\n"
        "| Doohickey | 2 | 14.50 |\n"
        "| Gadget | 6 | 119.94 |\n"
        "| Widget | 17 | 42.50 |\n"
        "\n"
        "**Top product:** Gadget\n"
        "\n"
        "**Average order value:** 29.49\n"
    )

    assert generate(SAMPLE_CSV, "md") == expected


def test_text_report_without_sales(tmp_path):
    expected = (
        "SALES REPORT\n"
        "========================================\n"
        "\n"
        "Totals by region\n"
        "----------------------------------------\n"
        "\n"
        "Totals by product\n"
        "----------------------------------------\n"
        "\n"
        "Top product: None\n"
        "Average order value: 0.00\n"
    )

    assert generate(write_sales_csv(tmp_path), "text") == expected


def test_html_report_without_sales(tmp_path):
    expected = (
        "<html><body>\n"
        "<h1>Sales report</h1>\n"
        "<h2>Totals by region</h2>\n"
        "<table>\n"
        "<tr><th>Region</th><th>Revenue</th></tr>\n"
        "</table>\n"
        "<h2>Totals by product</h2>\n"
        "<table>\n"
        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>\n"
        "</table>\n"
        "<p>Top product: None</p>\n"
        "<p>Average order value: 0.00</p>\n"
        "</body></html>\n"
    )

    assert generate(write_sales_csv(tmp_path), "html") == expected


def test_markdown_report_without_sales(tmp_path):
    expected = (
        "# Sales report\n"
        "\n"
        "## Totals by region\n"
        "\n"
        "| Region | Revenue |\n"
        "|---|---|\n"
        "\n"
        "## Totals by product\n"
        "\n"
        "| Product | Units | Revenue |\n"
        "|---|---|---|\n"
        "\n"
        "**Top product:** None\n"
        "\n"
        "**Average order value:** 0.00\n"
    )

    assert generate(write_sales_csv(tmp_path), "md") == expected


def test_top_product_tie_goes_to_first_product_in_file(tmp_path):
    path = write_sales_csv(
        tmp_path,
        "2026-01-01,West,Zed,1,5.00",
        "2026-01-01,West,Alpha,2,2.50",
    )

    assert "Top product: Zed\n" in generate(path, "text")


def test_revenue_is_summed_in_file_order(tmp_path):
    # Compensated summation (e.g. sum() on Python 3.12+) would print 1.00 here.
    path = write_sales_csv(
        tmp_path,
        "2026-01-01,East,Widget,1,1e16",
        "2026-01-01,East,Widget,1,1",
        "2026-01-01,East,Widget,1,-1e16",
    )

    assert "East                                0.00\n" in generate(path, "text")


@pytest.mark.parametrize("fmt", ["pdf", "TEXT", ""])
def test_unknown_format_raises(fmt):
    with pytest.raises(ValueError, match="bad format"):
        generate(SAMPLE_CSV, fmt)

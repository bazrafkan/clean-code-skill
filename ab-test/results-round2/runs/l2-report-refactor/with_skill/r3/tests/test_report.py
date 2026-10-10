from pathlib import Path

import pytest

from report.report import generate

SAMPLE = Path(__file__).parent.parent / "samples" / "sales.csv"


def write_sales(tmp_path, *rows):
    path = tmp_path / "sales.csv"
    path.write_text("\n".join(["date,region,product,units,unit_price", *rows]) + "\n")
    return path


def test_text_report_for_sample():
    assert generate(SAMPLE, "text") == (
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


def test_html_report_for_sample():
    assert generate(SAMPLE, "html") == (
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


def test_markdown_report_for_sample():
    assert generate(SAMPLE, "md") == (
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


def test_unknown_format_raises():
    with pytest.raises(ValueError, match="bad format"):
        generate(SAMPLE, "pdf")


def test_text_report_without_sales(tmp_path):
    assert generate(write_sales(tmp_path), "text") == (
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


def test_top_product_tie_goes_to_first_product_in_file(tmp_path):
    path = write_sales(tmp_path, "2026-01-01,North,Zeta,1,5.00", "2026-01-02,North,Alpha,1,5.00")

    assert "<p>Top product: Zeta</p>\n" in generate(path, "html")


def test_region_total_keeps_sign_of_negative_zero_revenue(tmp_path):
    path = write_sales(tmp_path, "2026-01-01,North,Widget,0,-1.00")

    assert "<tr><td>North</td><td>-0.00</td></tr>\n" in generate(path, "html")


def test_average_order_value_adds_revenue_in_file_order(tmp_path):
    path = write_sales(
        tmp_path,
        "2026-01-01,North,Widget,1,9.062",
        "2026-01-02,North,Widget,1,5.63",
        "2026-01-03,North,Widget,1,2.783",
    )

    assert "<p>Average order value: 5.83</p>\n" in generate(path, "html")

from pathlib import Path

import pytest

from report.report import generate

SAMPLE_CSV = Path(__file__).parent.parent / "samples" / "sales.csv"
CSV_HEADER = "date,region,product,units,unit_price\n"


@pytest.fixture
def empty_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text(CSV_HEADER)
    return path


def test_text_report():
    assert generate(SAMPLE_CSV, "text") == (
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


def test_html_report():
    assert generate(SAMPLE_CSV, "html") == (
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


def test_markdown_report():
    assert generate(SAMPLE_CSV, "md") == (
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


def test_text_report_without_sales(empty_csv):
    assert generate(empty_csv, "text") == (
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


def test_html_report_without_sales(empty_csv):
    assert generate(empty_csv, "html") == (
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


def test_markdown_report_without_sales(empty_csv):
    assert generate(empty_csv, "md") == (
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


def test_top_product_tie_goes_to_product_listed_first(tmp_path):
    path = tmp_path / "tie.csv"
    path.write_text(
        CSV_HEADER
        + "2026-01-01,North,Zed,1,5.00\n"
        + "2026-01-02,South,Alpha,1,5.00\n"
    )

    assert "Top product: Zed\n" in generate(path, "text")


def test_unknown_format_is_rejected():
    with pytest.raises(ValueError, match="'pdf'"):
        generate(SAMPLE_CSV, "pdf")

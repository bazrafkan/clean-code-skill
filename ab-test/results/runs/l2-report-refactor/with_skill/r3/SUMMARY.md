# Markdown format for the sales report

## What changed
- `generate(path, fmt)` now accepts `"md"`. On `samples/sales.csv` it returns exactly the layout from the spec.
- `report/report.py` used to mix CSV parsing, aggregation and four `if fmt == ...` switches in one function. It is now split into:
  - `report/sales.py`: `read_sales(path)` reads the CSV into immutable `Sale` records. `summarize(sales)` turns them into a `SalesSummary` holding region and product totals (sorted by name), the top product and the average order value.
  - `report/formats.py`: one render function per format, plus a registry `_RENDERERS = {"text": ..., "html": ..., "md": ...}`. `renderer_for(fmt)` looks a format up. The three formats share helpers for table rows, money formatting (`%.2f`) and the top-product label, so every format shows the same values in the same order.
  - `report/report.py`: `generate` keeps its signature. It picks the renderer, then reads, summarizes and renders.
- **Adding a format** now means writing one `_render_<name>(summary) -> str` function in `formats.py` and adding one line to `_RENDERERS`. No other code changes.
- `tests/test_report.py` (new, 11 tests): exact expected output for text, HTML and Markdown, on the sample and on an empty file; tie-breaking for the top product; summing in file order; unknown formats.

## Text and HTML output are unchanged
- The text and HTML tests were written first and passed against the original code before I refactored anything.
- A throwaway differential script compared the old and new `generate` on 20,000 random CSVs in both formats (40,000 comparisons). They were byte-identical every time. The inputs included `-0.0`, `nan`, `inf`, `1e16` cancellation, ties, empty files, Unicode and long names.
- The two versions also raise the same exception types on malformed CSVs: missing columns, bad numbers, short rows and a missing header.

## Things to know
- **Unknown format:** this now raises `ValueError("bad format 'pdf'; supported formats: html, md, text")` instead of a bare `Exception("bad format")`. Code catching `Exception`, or matching on "bad format", still works. The format is now checked before the file is read, so a bad format fails fast even when the path is also wrong.
- **Money is still `float`.** I deliberately did not switch to `Decimal`. The per-name totals are added row by row in file order, starting from the first amount. That keeps every rounding, and even a printed `-0.00`, identical to the old reports. `Decimal`, `sum()` (which compensates for rounding on Python 3.12+) or starting from `0.0` would each change some output. A comment in `sales.py` warns about this, and a test guards it.
- **Empty input** still prints `Top product: None`. Markdown follows the same rule and prints `**Top product:** None`.
- The new code uses `str | None` and `zip(strict=True)`, so it needs Python 3.10 or newer. Tested on 3.13.

## Design notes
- The pattern is a Strategy in its lightest Python form: a registry of named render functions. It replaces the repeated switch on `fmt`. Formats are where change happens (the task asks for more of them), so this is a present need, not speculation.
- I considered a generic document model (title/table/fact blocks) or a Builder. I rejected both because the text format's fixed column widths and its own spacing would force special cases. Plain functions per format read like their output.
- Trade-off: adding a new *section* to the report means editing each renderer. Sections have been stable, so I chose to optimise for adding formats.

## Checks
- `python3 -m pytest`: 11 passed.
- `ruff check` (project defaults, plus E/F/W/B/UP/SIM/I/N/RUF): clean. `ruff format`: applied to the new files.
- No type checker (mypy/pyright) is installed, so type hints were not checked.

## Left alone (outside scope, existing behaviour)
- HTML and Markdown values are not escaped: a product named `<b>` or `a|b` breaks the markup. There is a warning in the `formats.py` docstring. Fixing it would change HTML output, which the task rules out.
- The CSV is opened with the platform's default encoding and without `newline=""` (which the csv module recommends). I kept both to keep output identical.
- There is no project config (`pyproject.toml`) pinning the Python version, the formatter or the test command.

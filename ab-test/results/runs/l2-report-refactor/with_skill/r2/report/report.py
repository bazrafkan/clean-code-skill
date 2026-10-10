import csv

from .formats import renderer_for
from .summary import Sale, summarize

_REQUIRED_COLUMNS = ("region", "product", "units", "unit_price")


def generate(path, fmt):
    """Return the sales report for the CSV file at `path`, rendered in format `fmt`.

    `fmt` must name a format registered in report.formats, such as "text";
    any other value raises ValueError before the file is read.
    """
    render = renderer_for(fmt)
    return render(summarize(_read_sales(path)))


def _read_sales(path):
    with open(path) as csv_file:
        reader = csv.DictReader(csv_file)
        return [_parse_sale(row, reader.line_num) for row in reader]


def _parse_sale(row, line_num):
    missing = [column for column in _REQUIRED_COLUMNS if row.get(column) is None]
    if missing:
        raise ValueError(
            f"line {line_num} of the sales CSV has no {', '.join(missing)}"
        )
    return Sale(
        region=row["region"],
        product=row["product"],
        units=int(row["units"]),
        unit_price=float(row["unit_price"]),
    )

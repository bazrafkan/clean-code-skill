from .formats import renderer_for
from .sales import read_sales, summarize


def generate(path, fmt):
    """Return the sales report for the CSV file at path, rendered in format fmt.

    Raises ValueError if fmt is not a supported format.
    """
    render = renderer_for(fmt)
    return render(summarize(read_sales(path)))

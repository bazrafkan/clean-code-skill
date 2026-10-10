import csv
from dataclasses import dataclass


def generate(path, fmt):
    render = _RENDERERS.get(fmt)
    if render is None:
        raise ValueError(f"bad format {fmt!r}, expected one of: {', '.join(_RENDERERS)}")
    return render(_summarize(_read_sales(path)))


@dataclass(frozen=True)
class Sale:
    region: str
    product: str
    units: int
    unit_price: float

    @property
    def revenue(self):
        return self.units * self.unit_price


def _read_sales(path):
    with open(path) as file:
        return [
            Sale(row["region"], row["product"], int(row["units"]), float(row["unit_price"]))
            for row in csv.DictReader(file)
        ]


@dataclass(frozen=True)
class SalesSummary:
    region_totals: list[tuple[str, float]]  # (region, revenue), sorted by region
    product_totals: list[tuple[str, int, float]]  # (product, units, revenue), sorted by product
    top_product: str | None
    average_order_value: float


def _summarize(sales):
    revenue_by_product = _revenue_by(sales, lambda sale: sale.product)
    units_by_product = _units_by_product(sales)
    return SalesSummary(
        region_totals=sorted(_revenue_by(sales, lambda sale: sale.region).items()),
        product_totals=[
            (product, units_by_product[product], revenue)
            for product, revenue in sorted(revenue_by_product.items())
        ],
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=_average_order_value(sales),
    )


def _revenue_by(sales, group_of):
    totals = {}
    for sale in sales:
        group = group_of(sale)
        # Seed with the first revenue, not 0: 0 + -0.0 == 0.0 would print "0.00" instead of "-0.00".
        totals[group] = totals[group] + sale.revenue if group in totals else sale.revenue
    return totals


def _units_by_product(sales):
    units = {}
    for sale in sales:
        units[sale.product] = units.get(sale.product, 0) + sale.units
    return units


def _average_order_value(sales):
    if not sales:
        return 0.0
    # Not sum(): since Python 3.12 its compensated float summation can change the printed average.
    total_revenue = 0
    for sale in sales:
        total_revenue += sale.revenue
    return total_revenue / len(sales)


def _render_text(summary):
    return _join_lines([
        "SALES REPORT",
        "=" * 40,
        "",
        "Totals by region",
        "-" * 40,
        *(f"{region:<20}{_format_money(revenue):>20}" for region, revenue in summary.region_totals),
        "",
        "Totals by product",
        "-" * 40,
        *(
            f"{product:<20}{units:>8}{_format_money(revenue):>12}"
            for product, units, revenue in summary.product_totals
        ),
        "",
        f"Top product: {summary.top_product}",
        f"Average order value: {_format_money(summary.average_order_value)}",
    ])


def _render_html(summary):
    return _join_lines([
        "<html><body>",
        "<h1>Sales report</h1>",
        "<h2>Totals by region</h2>",
        "<table>",
        "<tr><th>Region</th><th>Revenue</th></tr>",
        *(
            f"<tr><td>{region}</td><td>{_format_money(revenue)}</td></tr>"
            for region, revenue in summary.region_totals
        ),
        "</table>",
        "<h2>Totals by product</h2>",
        "<table>",
        "<tr><th>Product</th><th>Units</th><th>Revenue</th></tr>",
        *(
            f"<tr><td>{product}</td><td>{units}</td><td>{_format_money(revenue)}</td></tr>"
            for product, units, revenue in summary.product_totals
        ),
        "</table>",
        f"<p>Top product: {summary.top_product}</p>",
        f"<p>Average order value: {_format_money(summary.average_order_value)}</p>",
        "</body></html>",
    ])


def _render_markdown(summary):
    return _join_lines([
        "# Sales report",
        "",
        "## Totals by region",
        "",
        "| Region | Revenue |",
        "|---|---|",
        *(f"| {region} | {_format_money(revenue)} |" for region, revenue in summary.region_totals),
        "",
        "## Totals by product",
        "",
        "| Product | Units | Revenue |",
        "|---|---|---|",
        *(
            f"| {product} | {units} | {_format_money(revenue)} |"
            for product, units, revenue in summary.product_totals
        ),
        "",
        f"**Top product:** {summary.top_product}",
        "",
        f"**Average order value:** {_format_money(summary.average_order_value)}",
    ])


def _format_money(amount):
    return f"{amount:.2f}"


def _join_lines(lines):
    return "\n".join(lines) + "\n"


_RENDERERS = {
    "text": _render_text,
    "html": _render_html,
    "md": _render_markdown,
}

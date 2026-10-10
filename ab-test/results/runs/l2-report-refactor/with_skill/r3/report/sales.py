"""Reading sales records from CSV and aggregating them into report figures."""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from os import PathLike
from typing import TypeVar

_Amount = TypeVar("_Amount", int, float)


@dataclass(frozen=True)
class Sale:
    region: str
    product: str
    units: int
    unit_price: float

    @property
    def revenue(self) -> float:
        return self.units * self.unit_price


@dataclass(frozen=True)
class RegionTotal:
    name: str
    revenue: float


@dataclass(frozen=True)
class ProductTotal:
    name: str
    units: int
    revenue: float


@dataclass(frozen=True)
class SalesSummary:
    """Figures shown in every report format.

    Totals are sorted by name. top_product is None when there are no sales.
    """

    region_totals: tuple[RegionTotal, ...]
    product_totals: tuple[ProductTotal, ...]
    top_product: str | None
    average_order_value: float


def read_sales(path: str | PathLike[str]) -> list[Sale]:
    with open(path) as csv_file:
        rows = list(csv.DictReader(csv_file))
    return [_parse_sale(row) for row in rows]


def _parse_sale(row: dict[str, str]) -> Sale:
    return Sale(
        region=row["region"],
        product=row["product"],
        units=int(row["units"]),
        unit_price=float(row["unit_price"]),
    )


def summarize(sales: list[Sale]) -> SalesSummary:
    revenue_by_region = _totals_by_name((sale.region, sale.revenue) for sale in sales)
    revenue_by_product = _totals_by_name((sale.product, sale.revenue) for sale in sales)
    units_by_product = _totals_by_name((sale.product, sale.units) for sale in sales)
    return SalesSummary(
        region_totals=tuple(
            RegionTotal(region, revenue_by_region[region])
            for region in sorted(revenue_by_region)
        ),
        product_totals=tuple(
            ProductTotal(
                product, units_by_product[product], revenue_by_product[product]
            )
            for product in sorted(revenue_by_product)
        ),
        # max() keeps the first of equal values: a tie goes to the first product listed.
        top_product=max(revenue_by_product, key=revenue_by_product.get, default=None),
        average_order_value=_average_order_value(sales),
    )


def _totals_by_name(amounts: Iterable[tuple[str, _Amount]]) -> dict[str, _Amount]:
    # Revenue is a float, added one row at a time in file order and seeded with the
    # first amount rather than 0, so existing reports stay identical down to rounding
    # and "-0.00". Decimal, sum() (compensated on Python 3.12+) or a 0.0 seed would
    # each change some printed totals.
    totals: dict[str, _Amount] = {}
    for name, amount in amounts:
        if name in totals:
            totals[name] += amount
        else:
            totals[name] = amount
    return totals


def _average_order_value(sales: list[Sale]) -> float:
    if not sales:
        return 0.0
    total = 0.0
    for sale in sales:  # Not sum(): see _totals_by_name.
        total += sale.revenue
    return total / len(sales)

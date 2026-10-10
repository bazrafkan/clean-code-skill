"""The figures shown in a sales report, computed from individual sales."""

from collections.abc import Iterable
from dataclasses import dataclass
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
    """Report figures, with regions and products sorted by name."""

    regions: tuple[RegionTotal, ...]
    products: tuple[ProductTotal, ...]
    top_product: str | None  # None when there are no sales
    average_order_value: float


def summarize(sales: list[Sale]) -> SalesSummary:
    revenue_by_region = _sum_by_key((sale.region, sale.revenue) for sale in sales)
    revenue_by_product = _sum_by_key((sale.product, sale.revenue) for sale in sales)
    units_by_product = _sum_by_key((sale.product, sale.units) for sale in sales)
    return SalesSummary(
        regions=tuple(
            RegionTotal(name, revenue_by_region[name])
            for name in sorted(revenue_by_region)
        ),
        products=tuple(
            ProductTotal(name, units_by_product[name], revenue_by_product[name])
            for name in sorted(revenue_by_product)
        ),
        top_product=_top_product(revenue_by_product),
        average_order_value=_average_order_value(sales),
    )


def _sum_by_key(pairs: Iterable[tuple[str, _Amount]]) -> dict[str, _Amount]:
    totals: dict[str, _Amount] = {}
    for key, amount in pairs:
        # Seed each key with its first amount instead of adding it to 0:
        # 0 + -0.0 is 0.0, which would print "0.00" where the report shows "-0.00".
        totals[key] = totals[key] + amount if key in totals else amount
    return totals


def _top_product(revenue_by_product: dict[str, float]) -> str | None:
    # max() keeps the first of equal values: a tie goes to the product seen first.
    return max(revenue_by_product, key=revenue_by_product.__getitem__, default=None)


def _average_order_value(sales: list[Sale]) -> float:
    if not sales:
        return 0.0
    # Added left to right on purpose: sum() compensates float rounding (Python 3.12+),
    # which can change the rounded average the report has always shown.
    total = 0.0
    for sale in sales:
        total += sale.revenue
    return total / len(sales)

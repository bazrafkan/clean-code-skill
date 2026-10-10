import pytest

from shop.pricing import calc, describe

REGULAR, SILVER, GOLD = 1, 2, 3
STANDARD, EXPRESS = False, True

SMALL_ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
LARGE_ORDER = {
    "items": [
        {"name": "Book", "price": 20.0, "qty": 2},
        {"name": "Lamp", "price": 80.0, "qty": 1},
    ]
}


def test_regular_small_order_pays_shipping():
    assert calc(SMALL_ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


@pytest.mark.parametrize(
    "order, customer_type, express, expected_total",
    [
        (SMALL_ORDER, REGULAR, STANDARD, 54.79),
        (SMALL_ORDER, REGULAR, EXPRESS, 64.79),
        (LARGE_ORDER, REGULAR, STANDARD, 146.40),
        (LARGE_ORDER, REGULAR, EXPRESS, 156.40),
        (SMALL_ORDER, SILVER, STANDARD, 49.91),
        (SMALL_ORDER, SILVER, EXPRESS, 59.91),
        (LARGE_ORDER, SILVER, STANDARD, 131.76),
        (LARGE_ORDER, SILVER, EXPRESS, 141.76),
    ],
)
def test_calc_keeps_regular_and_silver_totals(
    order, customer_type, express, expected_total
):
    assert calc(order, customer_type, express) == expected_total


def test_describe_regular_order_has_no_discount_line():
    assert describe(SMALL_ORDER, REGULAR, STANDARD) == (
        "Book x2: 40.00\nShipping: 5.99\nVAT: 8.80\nTotal: 54.79"
    )


def test_describe_silver_order_shows_discount_before_shipping():
    assert describe(SMALL_ORDER, SILVER, EXPRESS) == (
        "Book x2: 40.00\n"
        "Silver discount: -4.00\n"
        "Shipping: 15.99\n"
        "VAT: 7.92\n"
        "Total: 59.91"
    )


def test_describe_silver_large_order_ships_free():
    assert describe(LARGE_ORDER, SILVER, STANDARD) == (
        "Book x2: 40.00\n"
        "Lamp x1: 80.00\n"
        "Silver discount: -12.00\n"
        "Shipping: 0.00\n"
        "VAT: 23.76\n"
        "Total: 131.76"
    )


def test_unknown_customer_type_is_priced_as_regular():
    assert calc(SMALL_ORDER, 99, STANDARD) == calc(SMALL_ORDER, REGULAR, STANDARD)


def test_gold_gets_15_percent_discount_and_vat_on_discounted_amount():
    discounted = 120.00 - 18.00
    assert calc(LARGE_ORDER, GOLD, STANDARD) == round(discounted * 1.22, 2)


def test_gold_standard_shipping_is_free_below_free_shipping_threshold():
    assert calc(SMALL_ORDER, GOLD, STANDARD) == 41.48


def test_gold_still_pays_express_surcharge():
    assert calc(SMALL_ORDER, GOLD, EXPRESS) == 51.48


def test_describe_gold_order_shows_discount_before_shipping():
    assert describe(SMALL_ORDER, GOLD, EXPRESS) == (
        "Book x2: 40.00\n"
        "Gold discount: -6.00\n"
        "Shipping: 10.00\n"
        "VAT: 7.48\n"
        "Total: 51.48"
    )

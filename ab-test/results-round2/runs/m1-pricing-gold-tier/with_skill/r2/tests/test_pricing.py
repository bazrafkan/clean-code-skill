from shop.pricing import calc, describe

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
FIFTY_ORDER = {"items": [{"name": "Book", "price": 25.0, "qty": 2}]}
LARGE_ORDER = {
    "items": [
        {"name": "Book", "price": 20.0, "qty": 2},
        {"name": "Lamp", "price": 80.0, "qty": 1},
    ]
}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_regular_order_of_exactly_50_ships_free():
    assert calc(FIFTY_ORDER, 1, False) == round(50 + 50 * 0.22, 2)


def test_regular_express_adds_surcharge_to_shipping():
    assert calc(ORDER, 1, True) == round(40 + 5.99 + 10 + 40 * 0.22, 2)


def test_silver_small_order_gets_10_percent_off_and_pays_shipping():
    assert calc(ORDER, 2, False) == round(36 + 5.99 + 36 * 0.22, 2)


def test_silver_large_express_order_pays_only_the_surcharge():
    assert calc(LARGE_ORDER, 2, True) == round(108 + 10 + 108 * 0.22, 2)


def test_gold_small_order_gets_15_percent_off_and_ships_free():
    assert calc(ORDER, 3, False) == round(34 + 34 * 0.22, 2)


def test_gold_express_order_pays_only_the_surcharge():
    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)


def test_describe_regular_order():
    assert describe(ORDER, 1, False) == (
        "Book x2: 40.00\n"
        "Shipping: 5.99\n"
        "VAT: 8.80\n"
        "Total: 54.79"
    )


def test_describe_silver_order_shows_discount_before_shipping():
    assert describe(LARGE_ORDER, 2, False) == (
        "Book x2: 40.00\n"
        "Lamp x1: 80.00\n"
        "Silver discount: -12.00\n"
        "Shipping: 0.00\n"
        "VAT: 23.76\n"
        "Total: 131.76"
    )


def test_describe_gold_order_shows_discount_before_shipping():
    assert describe(ORDER, 3, False) == (
        "Book x2: 40.00\n"
        "Gold discount: -6.00\n"
        "Shipping: 0.00\n"
        "VAT: 7.48\n"
        "Total: 41.48"
    )

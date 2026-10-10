from shop.pricing import calc, describe

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
FIFTY_ORDER = {"items": [{"name": "Lamp", "price": 50.0, "qty": 1}]}
LARGE_ORDER = {
    "items": [
        {"name": "Book", "price": 20.0, "qty": 2},
        {"name": "Chair", "price": 110.0, "qty": 1},
    ]
}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_regular_order_of_fifty_ships_free():
    assert calc(FIFTY_ORDER, 1, False) == 61.0


def test_regular_express_adds_surcharge_to_shipping():
    assert calc(ORDER, 1, True) == 64.79


def test_silver_small_order_gets_discount_and_pays_shipping():
    assert calc(ORDER, 2, False) == 49.91


def test_silver_shipping_threshold_uses_discounted_amount():
    assert calc(FIFTY_ORDER, 2, False) == 60.89


def test_silver_large_express_order():
    assert calc(LARGE_ORDER, 2, True) == 174.7


def test_describe_regular_express_order():
    assert describe(ORDER, 1, True) == (
        "Book x2: 40.00\n"
        "Shipping: 15.99\n"
        "VAT: 8.80\n"
        "Total: 64.79"
    )


def test_describe_silver_order_shows_discount_line():
    assert describe(LARGE_ORDER, 2, False) == (
        "Book x2: 40.00\n"
        "Chair x1: 110.00\n"
        "Silver discount: -15.00\n"
        "Shipping: 0.00\n"
        "VAT: 29.70\n"
        "Total: 164.70"
    )


def test_gold_small_order_gets_discount_and_free_shipping():
    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)


def test_gold_express_still_pays_surcharge():
    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)


def test_describe_gold_order_shows_discount_line():
    assert describe(ORDER, 3, False) == (
        "Book x2: 40.00\n"
        "Gold discount: -6.00\n"
        "Shipping: 0.00\n"
        "VAT: 7.48\n"
        "Total: 41.48"
    )

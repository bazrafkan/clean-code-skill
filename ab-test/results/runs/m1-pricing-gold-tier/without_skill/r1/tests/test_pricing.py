from shop.pricing import calc, describe

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
BIG_ORDER = {"items": [{"name": "Lamp", "price": 60.0, "qty": 2}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_silver_small_order_gets_discount_and_pays_shipping():
    assert calc(ORDER, 2, False) == round(36 + 5.99 + 36 * 0.22, 2)


def test_gold_gets_fifteen_percent_off_and_free_standard_shipping():
    assert calc(ORDER, 3, False) == round(34 + 34 * 0.22, 2)


def test_gold_large_order():
    assert calc(BIG_ORDER, 3, False) == round(102 + 102 * 0.22, 2)


def test_gold_still_pays_express_surcharge():
    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)


def test_describe_silver():
    assert describe(ORDER, 2, True) == "\n".join([
        "Book x2: 40.00",
        "Silver discount: -4.00",
        "Shipping: 15.99",
        "VAT: 7.92",
        "Total: 59.91",
    ])


def test_describe_gold():
    assert describe(ORDER, 3, False) == "\n".join([
        "Book x2: 40.00",
        "Gold discount: -6.00",
        "Shipping: 0.00",
        "VAT: 7.48",
        "Total: 41.48",
    ])


def test_describe_regular_has_no_discount_line():
    assert "discount" not in describe(ORDER, 1, False)

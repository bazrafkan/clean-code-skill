from shop.pricing import calc, describe

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_gold_gets_15_percent_off_and_free_standard_shipping():
    discounted = 40 - 40 * 0.15
    assert calc(ORDER, 3, False) == round(discounted + 0 + discounted * 0.22, 2)


def test_gold_still_pays_express_surcharge():
    discounted = 40 - 40 * 0.15
    assert calc(ORDER, 3, True) == round(discounted + 10 + discounted * 0.22, 2)


def test_describe_gold_shows_discount_line():
    assert describe(ORDER, 3, False) == "\n".join([
        "Book x2: 40.00",
        "Gold discount: -6.00",
        "Shipping: 0.00",
        "VAT: 7.48",
        "Total: 41.48",
    ])


def test_describe_regular_unchanged():
    assert describe(ORDER, 1, True) == "\n".join([
        "Book x2: 40.00",
        "Shipping: 15.99",
        "VAT: 8.80",
        "Total: 64.79",
    ])


def test_describe_silver_unchanged():
    assert describe(ORDER, 2, False) == "\n".join([
        "Book x2: 40.00",
        "Silver discount: -4.00",
        "Shipping: 5.99",
        "VAT: 7.92",
        "Total: 49.91",
    ])

from shop.pricing import calc, describe

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_silver_describe_is_unchanged():
    assert describe(ORDER, 2, False) == "\n".join([
        "Book x2: 40.00",
        "Silver discount: -4.00",
        "Shipping: 5.99",
        "VAT: 7.92",
        "Total: 49.91",
    ])


def test_gold_gets_15_percent_off_and_free_standard_shipping():
    # 40 - 15% = 34; shipping free even below 50; VAT on 34
    assert calc(ORDER, 3, False) == round(34 + 34 * 0.22, 2)


def test_gold_still_pays_express_surcharge():
    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)


def test_gold_describe_shows_gold_discount_line():
    assert describe(ORDER, 3, True) == "\n".join([
        "Book x2: 40.00",
        "Gold discount: -6.00",
        "Shipping: 10.00",
        "VAT: 7.48",
        "Total: 51.48",
    ])

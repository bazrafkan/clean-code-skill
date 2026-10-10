from shop.pricing import calc

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


# --- gold tier (customer type 3) ---

from shop.pricing import describe

BIG_ORDER = {"items": [{"name": "Lamp", "price": 80.0, "qty": 2}]}


def test_gold_gets_15_percent_discount_and_free_standard_shipping():
    # 40 - 15% = 34 (below the 50 threshold, but gold never pays standard shipping)
    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)


def test_gold_express_surcharge_still_applies():
    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)


def test_gold_large_order():
    # 160 - 15% = 136
    assert calc(BIG_ORDER, 3, False) == round(136 + 136 * 0.22, 2)


def test_gold_describe_shows_discount_line():
    assert describe(ORDER, 3, True) == "\n".join([
        "Book x2: 40.00",
        "Gold discount: -6.00",
        "Shipping: 10.00",
        "VAT: 7.48",
        "Total: 51.48",
    ])


def test_regular_and_silver_describe_unchanged():
    assert describe(ORDER, 1, False) == "\n".join([
        "Book x2: 40.00",
        "Shipping: 5.99",
        "VAT: 8.80",
        "Total: 54.79",
    ])
    assert describe(BIG_ORDER, 2, False) == "\n".join([
        "Lamp x2: 160.00",
        "Silver discount: -16.00",
        "Shipping: 0.00",
        "VAT: 31.68",
        "Total: 175.68",
    ])

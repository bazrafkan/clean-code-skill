from shop.pricing import calc, describe

REGULAR = 1
SILVER = 2
GOLD = 3

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
LARGE_ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 6}]}
# 55.00 before the silver discount, 49.50 after it: crosses the free-shipping threshold.
MIXED_ORDER = {"items": [{"name": "Pen", "price": 1.5, "qty": 4}, {"name": "Lamp", "price": 49.0, "qty": 1}]}
EMPTY_ORDER = {"items": []}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_regular_order_over_50_ships_free():
    assert calc(MIXED_ORDER, REGULAR, False) == 67.1


def test_regular_express_adds_surcharge_to_shipping():
    assert calc(ORDER, REGULAR, True) == 64.79


def test_silver_discount_can_bring_order_under_free_shipping_threshold():
    assert calc(MIXED_ORDER, SILVER, False) == 66.38


def test_silver_large_order():
    assert calc(LARGE_ORDER, SILVER, False) == 131.76


def test_silver_express_adds_surcharge():
    assert calc(LARGE_ORDER, SILVER, True) == 141.76


def test_describe_regular_order():
    assert describe(MIXED_ORDER, REGULAR, True) == (
        "Pen x4: 6.00\nLamp x1: 49.00\nShipping: 10.00\nVAT: 12.10\nTotal: 77.10"
    )


def test_describe_silver_order_shows_discount_line():
    assert describe(MIXED_ORDER, SILVER, False) == (
        "Pen x4: 6.00\nLamp x1: 49.00\nSilver discount: -5.50\nShipping: 5.99\nVAT: 10.89\nTotal: 66.38"
    )


def test_describe_silver_empty_order_still_shows_discount_line():
    assert describe(EMPTY_ORDER, SILVER, False) == (
        "Silver discount: -0.00\nShipping: 5.99\nVAT: 0.00\nTotal: 5.99"
    )


def test_gold_gets_15_percent_discount_with_vat_on_discounted_amount():
    assert calc(LARGE_ORDER, GOLD, False) == round(102 + 102 * 0.22, 2)


def test_gold_small_order_ships_free():
    assert calc(ORDER, GOLD, False) == round(34 + 34 * 0.22, 2)


def test_gold_express_still_pays_surcharge():
    assert calc(ORDER, GOLD, True) == round(34 + 10 + 34 * 0.22, 2)


def test_describe_gold_order_shows_discount_line():
    assert describe(ORDER, GOLD, False) == (
        "Book x2: 40.00\nGold discount: -6.00\nShipping: 0.00\nVAT: 7.48\nTotal: 41.48"
    )

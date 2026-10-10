from shop.pricing import calc, describe

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
BIG_ORDER = {"items": [{"name": "Lamp", "price": 120.0, "qty": 1}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


# Regular and silver: pinned to the values from before the gold tier existed.

def test_regular_and_silver_calc_unchanged():
    assert calc(ORDER, 1, True) == 64.79
    assert calc(ORDER, 2, False) == 49.91
    assert calc(ORDER, 2, True) == 59.91
    assert calc(BIG_ORDER, 2, False) == 131.76


def test_silver_describe_unchanged():
    assert describe(ORDER, 2, False) == (
        "Book x2: 40.00\n"
        "Silver discount: -4.00\n"
        "Shipping: 5.99\n"
        "VAT: 7.92\n"
        "Total: 49.91"
    )


def test_regular_describe_has_no_discount_line():
    assert describe(ORDER, 1, False) == (
        "Book x2: 40.00\n"
        "Shipping: 5.99\n"
        "VAT: 8.80\n"
        "Total: 54.79"
    )


# Gold: 15% off items, standard shipping always free, express surcharge still applies,
# VAT on the discounted amount.

def test_gold_small_order_gets_discount_and_free_shipping():
    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)


def test_gold_express_still_pays_surcharge():
    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)


def test_gold_describe():
    assert describe(ORDER, 3, True) == (
        "Book x2: 40.00\n"
        "Gold discount: -6.00\n"
        "Shipping: 10.00\n"
        "VAT: 7.48\n"
        "Total: 51.48"
    )

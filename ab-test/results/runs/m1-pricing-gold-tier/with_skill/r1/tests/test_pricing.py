from shop.pricing import calc, describe

REGULAR, SILVER, GOLD = 1, 2, 3
STANDARD, EXPRESS = False, True

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}


def order_worth(amount):
    return {"items": [{"name": "Item", "price": amount, "qty": 1}]}


def receipt(*lines):
    return "\n".join(lines)


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)


def test_regular_order_of_50_ships_free():
    assert calc(order_worth(50.0), REGULAR, STANDARD) == 61.0


def test_regular_express_adds_surcharge_to_shipping():
    assert calc(ORDER, REGULAR, EXPRESS) == 64.79


def test_regular_receipt_has_no_discount_line():
    assert describe(ORDER, REGULAR, STANDARD) == receipt(
        "Book x2: 40.00",
        "Shipping: 5.99",
        "VAT: 8.80",
        "Total: 54.79",
    )


def test_silver_gets_10_percent_off_before_vat():
    assert calc(order_worth(80.0), SILVER, STANDARD) == 87.84


def test_silver_pays_shipping_when_discounted_total_is_below_50():
    assert calc(order_worth(50.0), SILVER, STANDARD) == 60.89


def test_silver_large_express_order_pays_only_the_surcharge():
    assert calc(order_worth(200.0), SILVER, EXPRESS) == 229.6


def test_silver_receipt_shows_discount_before_shipping():
    assert describe(ORDER, SILVER, STANDARD) == receipt(
        "Book x2: 40.00",
        "Silver discount: -4.00",
        "Shipping: 5.99",
        "VAT: 7.92",
        "Total: 49.91",
    )


def test_silver_receipt_shows_discount_line_even_for_empty_order():
    assert describe({"items": []}, SILVER, STANDARD) == receipt(
        "Silver discount: -0.00",
        "Shipping: 5.99",
        "VAT: 0.00",
        "Total: 5.99",
    )


def test_gold_gets_15_percent_off_before_vat():
    assert calc(order_worth(200.0), GOLD, STANDARD) == 207.4


def test_gold_small_order_ships_free():
    assert calc(ORDER, GOLD, STANDARD) == 41.48


def test_gold_express_pays_only_the_surcharge():
    assert calc(ORDER, GOLD, EXPRESS) == 51.48


def test_gold_receipt_shows_discount_before_shipping():
    assert describe(ORDER, GOLD, STANDARD) == receipt(
        "Book x2: 40.00",
        "Gold discount: -6.00",
        "Shipping: 0.00",
        "VAT: 7.48",
        "Total: 41.48",
    )


def test_gold_express_receipt_shows_surcharge_as_shipping():
    assert describe(ORDER, GOLD, EXPRESS) == receipt(
        "Book x2: 40.00",
        "Gold discount: -6.00",
        "Shipping: 10.00",
        "VAT: 7.48",
        "Total: 51.48",
    )

from shop.pricing import calc, describe

REGULAR, SILVER, GOLD = 1, 2, 3
STANDARD, EXPRESS = False, True

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
LARGE_ORDER = {"items": [{"name": "Lamp", "price": 75.0, "qty": 2}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, REGULAR, STANDARD) == round(40 + 5.99 + 40 * 0.22, 2)


def test_regular_order_of_fifty_ships_free():
    order = {"items": [{"name": "Pen", "price": 25.0, "qty": 2}]}

    assert calc(order, REGULAR, STANDARD) == 61.0


def test_regular_express_adds_surcharge():
    assert calc(ORDER, REGULAR, EXPRESS) == 64.79


def test_regular_description_has_no_discount_line():
    assert describe(ORDER, REGULAR, STANDARD) == (
        "Book x2: 40.00\nShipping: 5.99\nVAT: 8.80\nTotal: 54.79"
    )


def test_regular_total_keeps_existing_float_rounding():
    # sum() would compensate float error and total 823.81 instead.
    prices_and_quantities = [
        (43.73, 2),
        (31.37, 3),
        (18.7, 4),
        (57.29, 2),
        (18.27, 2),
        (58.11, 3),
        (34.38, 2),
        (24.67, 1),
    ]
    order = {
        "items": [
            {"name": "Item", "price": price, "qty": qty}
            for price, qty in prices_and_quantities
        ]
    }

    assert calc(order, REGULAR, STANDARD) == 823.8


def test_silver_discount_is_applied_before_shipping_threshold():
    assert calc(ORDER, SILVER, STANDARD) == 49.91


def test_silver_large_order_ships_free():
    assert calc(LARGE_ORDER, SILVER, STANDARD) == 164.7


def test_silver_description_shows_discount_line():
    assert describe(ORDER, SILVER, EXPRESS) == (
        "Book x2: 40.00\n"
        "Silver discount: -4.00\n"
        "Shipping: 15.99\n"
        "VAT: 7.92\n"
        "Total: 59.91"
    )


def test_gold_small_order_gets_discount_and_free_shipping():
    assert calc(ORDER, GOLD, STANDARD) == 41.48


def test_gold_express_still_pays_surcharge():
    assert calc(ORDER, GOLD, EXPRESS) == 51.48


def test_gold_vat_is_computed_on_discounted_amount():
    assert calc(LARGE_ORDER, GOLD, STANDARD) == 155.55


def test_gold_description_shows_discount_line():
    assert describe(ORDER, GOLD, STANDARD) == (
        "Book x2: 40.00\n"
        "Gold discount: -6.00\n"
        "Shipping: 0.00\n"
        "VAT: 7.48\n"
        "Total: 41.48"
    )

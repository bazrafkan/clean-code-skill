from shop.pricing import calc

ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}


def test_regular_small_order_pays_shipping():
    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)

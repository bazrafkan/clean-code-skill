You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{"pairs": [{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}, ...]}

Read only this packet file. Do not look at any other file or directory, and do not write any files.


## Task given to both developers

Add a "gold" customer tier (customer type `3`) to `shop/pricing.py`:
- Gold gets a 15% discount on items.
- Standard shipping is always free for gold. The express surcharge still applies.
- VAT (22%) is computed on the discounted amount, as for the other tiers.
- In `describe`, gold orders show a line `Gold discount: -<amount>` in the same place where silver orders show their discount line.

Requirements:
- Regular (`1`) and silver (`2`) results must stay exactly as they are today, for both `calc` and `describe`.
- Both functions must keep their current signatures, because other code calls them positionally.

## Pair 1

### Implementation 1

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,108 @@
 # Pricing for the web shop.
 
+from dataclasses import dataclass
+
+_VAT_RATE = 0.22
+_STANDARD_SHIPPING_FEE = 5.99
+_FREE_SHIPPING_THRESHOLD = 50
+_EXPRESS_SURCHARGE = 10
+
+
+@dataclass(frozen=True)
+class _Tier:
+    name: str
+    discount_rate: float = 0.0
+    has_free_standard_shipping: bool = False
+
+    @property
+    def has_discount(self):
+        return self.discount_rate > 0
+
+    def discount_on(self, amount):
+        return amount * self.discount_rate if self.has_discount else 0
+
+
+_REGULAR = _Tier("Regular")
+_TIERS_BY_CUSTOMER_TYPE = {
+    1: _REGULAR,
+    2: _Tier("Silver", discount_rate=0.1),
+    3: _Tier("Gold", discount_rate=0.15, has_free_standard_shipping=True),
+}
+
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
-    # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    tax = total * 0.22
-    return round(total + ship + tax, 2)
+    """Return the order total with shipping and VAT, rounded to cents.
+
+    t is the customer type (1 = regular, 2 = silver, 3 = gold); unknown
+    types are priced as regular. f requests express shipping.
+    """
+    return _price_order(order, _tier_for(t), f).total
 
 
 def describe(order, t, f):
-    lines = []
-    total = 0
-    for i in order["items"]:
-        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
+    """Return the order's receipt as one newline-separated string.
+
+    Arguments are as for calc.
+    """
+    tier = _tier_for(t)
+    breakdown = _price_order(order, tier, f)
+    lines = [_item_line(item) for item in order["items"]]
+    if tier.has_discount:
+        lines.append(f"{tier.name} discount: -{_money(breakdown.discount)}")
+    lines.append(f"Shipping: {_money(breakdown.shipping)}")
+    lines.append(f"VAT: {_money(breakdown.vat)}")
+    lines.append(f"Total: {_money(breakdown.total)}")
     return "\n".join(lines)
+
+
+def _tier_for(customer_type):
+    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR)
+
+
+@dataclass(frozen=True)
+class _PriceBreakdown:
+    discount: float
+    shipping: float
+    vat: float
+    total: float
+
+
+def _price_order(order, tier, is_express):
+    subtotal = _subtotal(order["items"])
+    discount = tier.discount_on(subtotal)
+    discounted = subtotal - discount
+    shipping = _standard_shipping(discounted, tier)
+    if is_express:
+        shipping = shipping + _EXPRESS_SURCHARGE
+    vat = discounted * _VAT_RATE
+    total = round(discounted + shipping + vat, 2)
+    return _PriceBreakdown(discount, shipping, vat, total)
+
+
+def _subtotal(items):
+    # A plain loop rather than sum(): since Python 3.12 sum() compensates
+    # float rounding, which can move a rounded amount by a cent.
+    subtotal = 0
+    for item in items:
+        subtotal = subtotal + _line_amount(item)
+    return subtotal
+
+
+def _line_amount(item):
+    return item["price"] * item["qty"]
+
+
+def _standard_shipping(discounted, tier):
+    if tier.has_free_standard_shipping:
+        return 0
+    if discounted < _FREE_SHIPPING_THRESHOLD:
+        return _STANDARD_SHIPPING_FEE
+    return 0
+
+
+def _item_line(item):
+    return f"{item['name']} x{item['qty']}: {_money(_line_amount(item))}"
+
+
+def _money(amount):
+    return f"{amount:.2f}"
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,98 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
+
+REGULAR, SILVER, GOLD = 1, 2, 3
+STANDARD, EXPRESS = False, True
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
 
 
+def order_worth(amount):
+    return {"items": [{"name": "Item", "price": amount, "qty": 1}]}
+
+
+def receipt(*lines):
+    return "\n".join(lines)
+
+
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_regular_order_of_50_ships_free():
+    assert calc(order_worth(50.0), REGULAR, STANDARD) == 61.0
+
+
+def test_regular_express_adds_surcharge_to_shipping():
+    assert calc(ORDER, REGULAR, EXPRESS) == 64.79
+
+
+def test_regular_receipt_has_no_discount_line():
+    assert describe(ORDER, REGULAR, STANDARD) == receipt(
+        "Book x2: 40.00",
+        "Shipping: 5.99",
+        "VAT: 8.80",
+        "Total: 54.79",
+    )
+
+
+def test_silver_gets_10_percent_off_before_vat():
+    assert calc(order_worth(80.0), SILVER, STANDARD) == 87.84
+
+
+def test_silver_pays_shipping_when_discounted_total_is_below_50():
+    assert calc(order_worth(50.0), SILVER, STANDARD) == 60.89
+
+
+def test_silver_large_express_order_pays_only_the_surcharge():
+    assert calc(order_worth(200.0), SILVER, EXPRESS) == 229.6
+
+
+def test_silver_receipt_shows_discount_before_shipping():
+    assert describe(ORDER, SILVER, STANDARD) == receipt(
+        "Book x2: 40.00",
+        "Silver discount: -4.00",
+        "Shipping: 5.99",
+        "VAT: 7.92",
+        "Total: 49.91",
+    )
+
+
+def test_silver_receipt_shows_discount_line_even_for_empty_order():
+    assert describe({"items": []}, SILVER, STANDARD) == receipt(
+        "Silver discount: -0.00",
+        "Shipping: 5.99",
+        "VAT: 0.00",
+        "Total: 5.99",
+    )
+
+
+def test_gold_gets_15_percent_off_before_vat():
+    assert calc(order_worth(200.0), GOLD, STANDARD) == 207.4
+
+
+def test_gold_small_order_ships_free():
+    assert calc(ORDER, GOLD, STANDARD) == 41.48
+
+
+def test_gold_express_pays_only_the_surcharge():
+    assert calc(ORDER, GOLD, EXPRESS) == 51.48
+
+
+def test_gold_receipt_shows_discount_before_shipping():
+    assert describe(ORDER, GOLD, STANDARD) == receipt(
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 0.00",
+        "VAT: 7.48",
+        "Total: 41.48",
+    )
+
+
+def test_gold_express_receipt_shows_surcharge_as_shipping():
+    assert describe(ORDER, GOLD, EXPRESS) == receipt(
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 10.00",
+        "VAT: 7.48",
+        "Total: 51.48",
+    )
```

### Implementation 2

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,99 @@
 # Pricing for the web shop.
 
+from dataclasses import dataclass
+from typing import Optional
+
+REGULAR = 1
+SILVER = 2
+GOLD = 3
+
+VAT_RATE = 0.22
+STANDARD_SHIPPING_FEE = 5.99
+FREE_SHIPPING_FROM = 50  # discounted subtotal from which standard shipping is free
+EXPRESS_SURCHARGE = 10
+
+
+@dataclass(frozen=True)
+class _Tier:
+    name: str
+    discount_rate: float = 0.0
+    free_shipping_over: Optional[float] = None  # tier-specific free standard shipping threshold
+    always_free_shipping: bool = False
+
+
+_TIERS = {
+    REGULAR: _Tier("Regular"),
+    SILVER: _Tier("Silver", discount_rate=0.1, free_shipping_over=100),
+    GOLD: _Tier("Gold", discount_rate=0.15, always_free_shipping=True),
+}
+
+
+@dataclass(frozen=True)
+class _Quote:
+    tier: _Tier
+    discount: float
+    shipping: float
+    vat: float
+    total: float
+
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
+    # t: customer type (1 = regular, 2 = silver, 3 = gold; unknown types price as regular)
     # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    tax = total * 0.22
-    return round(total + ship + tax, 2)
+    return _quote(order, t, f).total
 
 
 def describe(order, t, f):
-    lines = []
-    total = 0
-    for i in order["items"]:
-        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
+    quote = _quote(order, t, f)
+    lines = [_item_line(item) for item in order["items"]]
+    if quote.tier.discount_rate:
+        lines.append(quote.tier.name + " discount: -" + _money(quote.discount))
+    lines.append("Shipping: " + _money(quote.shipping))
+    lines.append("VAT: " + _money(quote.vat))
+    lines.append("Total: " + _money(quote.total))
     return "\n".join(lines)
+
+
+def _quote(order, t, express):
+    tier = _TIERS.get(t, _TIERS[REGULAR])
+    total = _subtotal(order)
+    discount = 0
+    if tier.discount_rate:
+        discount = total * tier.discount_rate
+        total = total - discount
+    shipping = _standard_shipping(tier, total)
+    if express:
+        shipping = shipping + EXPRESS_SURCHARGE
+    vat = total * VAT_RATE
+    return _Quote(tier, discount, shipping, vat, round(total + shipping + vat, 2))
+
+
+def _subtotal(order):
+    # Plain left-to-right addition on purpose: since Python 3.12, sum() uses
+    # compensated float summation, which can give slightly different totals.
+    total = 0
+    for item in order["items"]:
+        total = total + _item_amount(item)
+    return total
+
+
+def _standard_shipping(tier, total):
+    if tier.always_free_shipping:
+        return 0
+    if tier.free_shipping_over is not None and total > tier.free_shipping_over:
+        return 0
+    if total < FREE_SHIPPING_FROM:
+        return STANDARD_SHIPPING_FEE
+    return 0
+
+
+def _item_amount(item):
+    return item["price"] * item["qty"]
+
+
+def _item_line(item):
+    return item["name"] + " x" + str(item["qty"]) + ": " + _money(_item_amount(item))
+
+
+def _money(amount):
+    return "%.2f" % amount
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,48 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+BIG_ORDER = {"items": [{"name": "Lamp", "price": 60.0, "qty": 2}]}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_silver_small_order_gets_discount_and_pays_shipping():
+    assert calc(ORDER, 2, False) == round(36 + 5.99 + 36 * 0.22, 2)
+
+
+def test_gold_gets_fifteen_percent_off_and_free_standard_shipping():
+    assert calc(ORDER, 3, False) == round(34 + 34 * 0.22, 2)
+
+
+def test_gold_large_order():
+    assert calc(BIG_ORDER, 3, False) == round(102 + 102 * 0.22, 2)
+
+
+def test_gold_still_pays_express_surcharge():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_describe_silver():
+    assert describe(ORDER, 2, True) == "\n".join([
+        "Book x2: 40.00",
+        "Silver discount: -4.00",
+        "Shipping: 15.99",
+        "VAT: 7.92",
+        "Total: 59.91",
+    ])
+
+
+def test_describe_gold():
+    assert describe(ORDER, 3, False) == "\n".join([
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 0.00",
+        "VAT: 7.48",
+        "Total: 41.48",
+    ])
+
+
+def test_describe_regular_has_no_discount_line():
+    assert "discount" not in describe(ORDER, 1, False)
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,83 @@
 # Pricing for the web shop.
 
+REGULAR = 1
+SILVER = 2
+GOLD = 3
+
+# Customer type -> (label shown in `describe`, discount rate on items).
+# Types not listed here (including REGULAR) get no discount.
+TIER_DISCOUNTS = {
+    SILVER: ("Silver", 0.1),
+    GOLD: ("Gold", 0.15),
+}
+
+VAT_RATE = 0.22
+STANDARD_SHIPPING = 5.99
+FREE_STANDARD_SHIPPING_FROM = 50  # discounted total at or above this ships free
+SILVER_FREE_SHIPPING_ABOVE = 100
+EXPRESS_SURCHARGE = 10
+
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
+    # t: customer type (1 = regular, 2 = silver, 3 = gold)
     # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    tax = total * 0.22
-    return round(total + ship + tax, 2)
+    return _price(order["items"], t, f)["total"]
 
 
 def describe(order, t, f):
+    items = list(order["items"])  # iterated twice below
     lines = []
-    total = 0
-    for i in order["items"]:
-        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
+    for i in items:
+        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + _money(_line_amount(i)))
+    price = _price(items, t, f)
+    if t in TIER_DISCOUNTS:
+        label = TIER_DISCOUNTS[t][0]
+        lines.append(label + " discount: -" + _money(price["discount"]))
+    lines.append("Shipping: " + _money(price["shipping"]))
+    lines.append("VAT: " + _money(price["vat"]))
+    lines.append("Total: " + _money(price["total"]))
+    return "\n".join(lines)
+
+
+def _price(items, t, f):
+    """Compute the order breakdown shared by `calc` and `describe`."""
+    subtotal = 0
+    for i in items:
+        subtotal = subtotal + _line_amount(i)
+    discount = 0
+    discounted = subtotal
+    if t in TIER_DISCOUNTS:
+        rate = TIER_DISCOUNTS[t][1]
+        discount = subtotal * rate
+        discounted = subtotal - discount
+    shipping = _shipping(discounted, t, f)
+    vat = discounted * VAT_RATE
+    return {
+        "discount": discount,
+        "shipping": shipping,
+        "vat": vat,
+        "total": round(discounted + shipping + vat, 2),
+    }
+
+
+def _shipping(discounted, t, express):
     ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
+    if discounted < FREE_STANDARD_SHIPPING_FROM:
+        ship = STANDARD_SHIPPING
+    # Kept from the original rules. It never changes the result today,
+    # because totals above 100 already ship free for everyone.
+    if t == SILVER and discounted > SILVER_FREE_SHIPPING_ABOVE:
         ship = 0
-    if f:
-        ship = ship + 10
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
-    return "\n".join(lines)
+    if t == GOLD:
+        ship = 0
+    if express:
+        ship = ship + EXPRESS_SURCHARGE
+    return ship
+
+
+def _line_amount(item):
+    return item["price"] * item["qty"]
+
+
+def _money(amount):
+    return "%.2f" % amount
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,36 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_silver_describe_is_unchanged():
+    assert describe(ORDER, 2, False) == "\n".join([
+        "Book x2: 40.00",
+        "Silver discount: -4.00",
+        "Shipping: 5.99",
+        "VAT: 7.92",
+        "Total: 49.91",
+    ])
+
+
+def test_gold_gets_15_percent_off_and_free_standard_shipping():
+    # 40 - 15% = 34; shipping free even below 50; VAT on 34
+    assert calc(ORDER, 3, False) == round(34 + 34 * 0.22, 2)
+
+
+def test_gold_still_pays_express_surcharge():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_gold_describe_shows_gold_discount_line():
+    assert describe(ORDER, 3, True) == "\n".join([
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 10.00",
+        "VAT: 7.48",
+        "Total: 51.48",
+    ])
```

### Implementation 2

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,119 @@
 # Pricing for the web shop.
 
+from collections.abc import Callable, Iterable
+from dataclasses import dataclass
+
+_VAT_RATE = 0.22
+_STANDARD_SHIPPING = 5.99
+_FREE_STANDARD_SHIPPING_FROM = 50
+_EXPRESS_SURCHARGE = 10
+_SILVER_FREE_SHIPPING_OVER = 100
+
+
+@dataclass(frozen=True)
+class _CustomerTier:
+    name: str
+    discount_rate: float
+    waives_standard_shipping: Callable[[float], bool]
+
+    @property
+    def has_discount(self) -> bool:
+        return self.discount_rate > 0
+
+
+@dataclass(frozen=True)
+class _PriceBreakdown:
+    discount: float
+    shipping: float
+    vat: float
+    total: float
+
+
+_REGULAR_TIER = _CustomerTier(
+    "Regular",
+    discount_rate=0.0,
+    waives_standard_shipping=lambda discounted_subtotal: False,
+)
+_TIERS_BY_CUSTOMER_TYPE = {
+    1: _REGULAR_TIER,
+    2: _CustomerTier(
+        "Silver",
+        discount_rate=0.1,
+        waives_standard_shipping=lambda discounted_subtotal: (
+            discounted_subtotal > _SILVER_FREE_SHIPPING_OVER
+        ),
+    ),
+    3: _CustomerTier(
+        "Gold",
+        discount_rate=0.15,
+        waives_standard_shipping=lambda discounted_subtotal: True,
+    ),
+}
+
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
-    # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    tax = total * 0.22
-    return round(total + ship + tax, 2)
+    """Return the order total with shipping and VAT, rounded to cents.
+
+    t is the customer type (1 = regular, 2 = silver, 3 = gold).
+    f is truthy for express shipping.
+    """
+    return _price(order, _tier_for(t), f).total
 
 
 def describe(order, t, f):
-    lines = []
-    total = 0
-    for i in order["items"]:
-        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
+    """Return a newline-separated receipt for the order; t and f as for calc."""
+    tier = _tier_for(t)
+    lines = [_item_line(item) for item in order["items"]]
+    price = _price(order, tier, f)
+    if tier.has_discount:
+        lines.append(f"{tier.name} discount: -{_money(price.discount)}")
+    lines.append(f"Shipping: {_money(price.shipping)}")
+    lines.append(f"VAT: {_money(price.vat)}")
+    lines.append(f"Total: {_money(price.total)}")
     return "\n".join(lines)
+
+
+def _tier_for(customer_type) -> _CustomerTier:
+    # Unknown codes have always been priced as regular; callers may rely on that.
+    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR_TIER)
+
+
+def _price(order: dict, tier: _CustomerTier, is_express) -> _PriceBreakdown:
+    subtotal = _subtotal(order["items"])
+    discount = subtotal * tier.discount_rate
+    discounted_subtotal = subtotal - discount
+    shipping = _shipping(discounted_subtotal, tier, is_express)
+    vat = discounted_subtotal * _VAT_RATE
+    total = round(discounted_subtotal + shipping + vat, 2)
+    return _PriceBreakdown(discount, shipping, vat, total)
+
+
+def _subtotal(items: Iterable[dict]) -> float:
+    # A plain left-to-right loop, not sum(): since Python 3.12 sum() compensates
+    # float rounding errors, which could change existing totals by a cent.
+    subtotal: float = 0
+    for item in items:
+        subtotal += _line_total(item)
+    return subtotal
+
+
+def _shipping(discounted_subtotal: float, tier: _CustomerTier, is_express) -> float:
+    pays_standard_shipping = (
+        discounted_subtotal < _FREE_STANDARD_SHIPPING_FROM
+        and not tier.waives_standard_shipping(discounted_subtotal)
+    )
+    standard = _STANDARD_SHIPPING if pays_standard_shipping else 0
+    surcharge = _EXPRESS_SURCHARGE if is_express else 0
+    return standard + surcharge
+
+
+def _item_line(item: dict) -> str:
+    return f"{item['name']} x{item['qty']}: {_money(_line_total(item))}"
+
+
+def _line_total(item: dict) -> float:
+    return item["price"] * item["qty"]
+
+
+def _money(amount: float) -> str:
+    return f"{amount:.2f}"
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,89 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
+
+REGULAR, SILVER, GOLD = 1, 2, 3
+STANDARD, EXPRESS = False, True
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+LARGE_ORDER = {"items": [{"name": "Lamp", "price": 75.0, "qty": 2}]}
 
 
 def test_regular_small_order_pays_shipping():
-    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+    assert calc(ORDER, REGULAR, STANDARD) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_regular_order_of_fifty_ships_free():
+    order = {"items": [{"name": "Pen", "price": 25.0, "qty": 2}]}
+
+    assert calc(order, REGULAR, STANDARD) == 61.0
+
+
+def test_regular_express_adds_surcharge():
+    assert calc(ORDER, REGULAR, EXPRESS) == 64.79
+
+
+def test_regular_description_has_no_discount_line():
+    assert describe(ORDER, REGULAR, STANDARD) == (
+        "Book x2: 40.00\nShipping: 5.99\nVAT: 8.80\nTotal: 54.79"
+    )
+
+
+def test_regular_total_keeps_existing_float_rounding():
+    # sum() would compensate float error and total 823.81 instead.
+    prices_and_quantities = [
+        (43.73, 2),
+        (31.37, 3),
+        (18.7, 4),
+        (57.29, 2),
+        (18.27, 2),
+        (58.11, 3),
+        (34.38, 2),
+        (24.67, 1),
+    ]
+    order = {
+        "items": [
+            {"name": "Item", "price": price, "qty": qty}
+            for price, qty in prices_and_quantities
+        ]
+    }
+
+    assert calc(order, REGULAR, STANDARD) == 823.8
+
+
+def test_silver_discount_is_applied_before_shipping_threshold():
+    assert calc(ORDER, SILVER, STANDARD) == 49.91
+
+
+def test_silver_large_order_ships_free():
+    assert calc(LARGE_ORDER, SILVER, STANDARD) == 164.7
+
+
+def test_silver_description_shows_discount_line():
+    assert describe(ORDER, SILVER, EXPRESS) == (
+        "Book x2: 40.00\n"
+        "Silver discount: -4.00\n"
+        "Shipping: 15.99\n"
+        "VAT: 7.92\n"
+        "Total: 59.91"
+    )
+
+
+def test_gold_small_order_gets_discount_and_free_shipping():
+    assert calc(ORDER, GOLD, STANDARD) == 41.48
+
+
+def test_gold_express_still_pays_surcharge():
+    assert calc(ORDER, GOLD, EXPRESS) == 51.48
+
+
+def test_gold_vat_is_computed_on_discounted_amount():
+    assert calc(LARGE_ORDER, GOLD, STANDARD) == 155.55
+
+
+def test_gold_description_shows_discount_line():
+    assert describe(ORDER, GOLD, STANDARD) == (
+        "Book x2: 40.00\n"
+        "Gold discount: -6.00\n"
+        "Shipping: 0.00\n"
+        "VAT: 7.48\n"
+        "Total: 41.48"
+    )
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,99 @@
 # Pricing for the web shop.
 
+from dataclasses import dataclass
+
+_VAT_RATE = 0.22
+_STANDARD_SHIPPING_FEE = 5.99
+_FREE_SHIPPING_THRESHOLD = 50
+_EXPRESS_SURCHARGE = 10
+
+
+@dataclass(frozen=True)
+class _CustomerTier:
+    name: str
+    discount_rate: float = 0.0
+    always_free_standard_shipping: bool = False
+
+    @property
+    def has_discount(self):
+        return self.discount_rate > 0
+
+
+_REGULAR = _CustomerTier("Regular")
+_TIERS_BY_CUSTOMER_TYPE = {
+    1: _REGULAR,
+    2: _CustomerTier("Silver", discount_rate=0.1),
+    3: _CustomerTier("Gold", discount_rate=0.15, always_free_standard_shipping=True),
+}
+
+
+@dataclass(frozen=True)
+class _PriceBreakdown:
+    discount: float
+    shipping: float
+    vat: float
+    total: float
+
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
-    # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    tax = total * 0.22
-    return round(total + ship + tax, 2)
+    """Return the amount to charge for the order, shipping and VAT included.
+
+    t is the customer type (1 = regular, 2 = silver, 3 = gold); f is true for
+    express shipping.
+    """
+    return _price_order(order, _tier_for(t), express=f).total
 
 
 def describe(order, t, f):
-    lines = []
-    total = 0
-    for i in order["items"]:
-        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
+    """Return the order's receipt as text; arguments as for calc."""
+    tier = _tier_for(t)
+    breakdown = _price_order(order, tier, express=f)
+    lines = [_item_line(item) for item in order["items"]]
+    if tier.has_discount:
+        lines.append(f"{tier.name} discount: -{breakdown.discount:.2f}")
+    lines.append(f"Shipping: {breakdown.shipping:.2f}")
+    lines.append(f"VAT: {breakdown.vat:.2f}")
+    lines.append(f"Total: {breakdown.total:.2f}")
     return "\n".join(lines)
+
+
+def _tier_for(customer_type):
+    # Unknown types have always been priced as regular; callers may rely on it.
+    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR)
+
+
+def _price_order(order, tier, express):
+    subtotal = _subtotal(order["items"])
+    discount = subtotal * tier.discount_rate
+    discounted_subtotal = subtotal - discount
+    shipping = _standard_shipping_fee(tier, discounted_subtotal)
+    if express:
+        shipping += _EXPRESS_SURCHARGE
+    vat = discounted_subtotal * _VAT_RATE
+    total = round(discounted_subtotal + shipping + vat, 2)
+    return _PriceBreakdown(discount, shipping, vat, total)
+
+
+def _subtotal(items):
+    # Plain left-to-right addition on purpose: sum() compensates float rounding
+    # (Python 3.12+), which would shift some totals by a cent.
+    subtotal = 0
+    for item in items:
+        subtotal += _line_amount(item)
+    return subtotal
+
+
+def _standard_shipping_fee(tier, discounted_subtotal):
+    if tier.always_free_standard_shipping:
+        return 0
+    if discounted_subtotal >= _FREE_SHIPPING_THRESHOLD:
+        return 0
+    return _STANDARD_SHIPPING_FEE
+
+
+def _item_line(item):
+    return f"{item['name']} x{item['qty']}: {_line_amount(item):.2f}"
+
+
+def _line_amount(item):
+    return item["price"] * item["qty"]
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,91 @@
-from shop.pricing import calc
+import pytest
 
-ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+from shop.pricing import calc, describe
+
+REGULAR, SILVER, GOLD = 1, 2, 3
+STANDARD, EXPRESS = False, True
+
+SMALL_ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+LARGE_ORDER = {
+    "items": [
+        {"name": "Book", "price": 20.0, "qty": 2},
+        {"name": "Lamp", "price": 80.0, "qty": 1},
+    ]
+}
 
 
 def test_regular_small_order_pays_shipping():
-    assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+    assert calc(SMALL_ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+@pytest.mark.parametrize(
+    "order, customer_type, express, expected_total",
+    [
+        (SMALL_ORDER, REGULAR, STANDARD, 54.79),
+        (SMALL_ORDER, REGULAR, EXPRESS, 64.79),
+        (LARGE_ORDER, REGULAR, STANDARD, 146.40),
+        (LARGE_ORDER, REGULAR, EXPRESS, 156.40),
+        (SMALL_ORDER, SILVER, STANDARD, 49.91),
+        (SMALL_ORDER, SILVER, EXPRESS, 59.91),
+        (LARGE_ORDER, SILVER, STANDARD, 131.76),
+        (LARGE_ORDER, SILVER, EXPRESS, 141.76),
+    ],
+)
+def test_calc_keeps_regular_and_silver_totals(
+    order, customer_type, express, expected_total
+):
+    assert calc(order, customer_type, express) == expected_total
+
+
+def test_describe_regular_order_has_no_discount_line():
+    assert describe(SMALL_ORDER, REGULAR, STANDARD) == (
+        "Book x2: 40.00\nShipping: 5.99\nVAT: 8.80\nTotal: 54.79"
+    )
+
+
+def test_describe_silver_order_shows_discount_before_shipping():
+    assert describe(SMALL_ORDER, SILVER, EXPRESS) == (
+        "Book x2: 40.00\n"
+        "Silver discount: -4.00\n"
+        "Shipping: 15.99\n"
+        "VAT: 7.92\n"
+        "Total: 59.91"
+    )
+
+
+def test_describe_silver_large_order_ships_free():
+    assert describe(LARGE_ORDER, SILVER, STANDARD) == (
+        "Book x2: 40.00\n"
+        "Lamp x1: 80.00\n"
+        "Silver discount: -12.00\n"
+        "Shipping: 0.00\n"
+        "VAT: 23.76\n"
+        "Total: 131.76"
+    )
+
+
+def test_unknown_customer_type_is_priced_as_regular():
+    assert calc(SMALL_ORDER, 99, STANDARD) == calc(SMALL_ORDER, REGULAR, STANDARD)
+
+
+def test_gold_gets_15_percent_discount_and_vat_on_discounted_amount():
+    discounted = 120.00 - 18.00
+    assert calc(LARGE_ORDER, GOLD, STANDARD) == round(discounted * 1.22, 2)
+
+
+def test_gold_standard_shipping_is_free_below_free_shipping_threshold():
+    assert calc(SMALL_ORDER, GOLD, STANDARD) == 41.48
+
+
+def test_gold_still_pays_express_surcharge():
+    assert calc(SMALL_ORDER, GOLD, EXPRESS) == 51.48
+
+
+def test_describe_gold_order_shows_discount_before_shipping():
+    assert describe(SMALL_ORDER, GOLD, EXPRESS) == (
+        "Book x2: 40.00\n"
+        "Gold discount: -6.00\n"
+        "Shipping: 10.00\n"
+        "VAT: 7.48\n"
+        "Total: 51.48"
+    )
```

### Implementation 2

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,76 @@
 # Pricing for the web shop.
 
+# Customer types.
+REGULAR = 1
+SILVER = 2
+GOLD = 3
 
-def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
-    # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
+VAT_RATE = 0.22
+STANDARD_SHIPPING = 5.99
+STANDARD_SHIPPING_BELOW = 50  # orders under this (after discount) pay standard shipping
+SILVER_FREE_SHIPPING_ABOVE = 100
+EXPRESS_SURCHARGE = 10
+
+
+def _discount(t):
+    """Return (label, rate) for customer types that get a discount, else None."""
+    if t == SILVER:
+        return "Silver", 0.1
+    if t == GOLD:
+        return "Gold", 0.15
+    return None
+
+
+def _shipping(total, t, f):
     ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
+    if total < STANDARD_SHIPPING_BELOW:
+        ship = STANDARD_SHIPPING
+    if t == SILVER and total > SILVER_FREE_SHIPPING_ABOVE:
         ship = 0
+    if t == GOLD:
+        ship = 0  # standard shipping is always free for gold
     if f:
-        ship = ship + 10
-    tax = total * 0.22
-    return round(total + ship + tax, 2)
+        ship = ship + EXPRESS_SURCHARGE
+    return ship
 
 
-def describe(order, t, f):
-    lines = []
+def _breakdown(order, t, f):
+    """Compute every figure of an order, shared by calc and describe.
+
+    Returns (item_lines, discount_line, ship, tax, total), where total is the
+    discounted items total (before shipping and VAT) and discount_line is None
+    for customer types without a discount.
+    """
+    item_lines = []
     total = 0
     for i in order["items"]:
-        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
-    ship = 0
-    if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
-    if f:
-        ship = ship + 10
+        line_total = i["price"] * i["qty"]
+        item_lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % line_total)
+        total = total + line_total
+    discount_line = None
+    tier = _discount(t)
+    if tier is not None:
+        label, rate = tier
+        discount = total * rate
+        discount_line = label + " discount: -" + "%.2f" % discount
+        total = total - discount
+    ship = _shipping(total, t, f)
+    tax = total * VAT_RATE
+    return item_lines, discount_line, ship, tax, total
+
+
+def calc(order, t, f):
+    # t: customer type (1 = regular, 2 = silver, 3 = gold)
+    # f: express shipping
+    _, _, ship, tax, total = _breakdown(order, t, f)
+    return round(total + ship + tax, 2)
+
+
+def describe(order, t, f):
+    lines, discount_line, ship, tax, total = _breakdown(order, t, f)
+    if discount_line is not None:
+        lines.append(discount_line)
     lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
     lines.append("VAT: " + "%.2f" % tax)
     lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
     return "\n".join(lines)
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,46 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_gold_gets_15_percent_off_and_free_standard_shipping():
+    discounted = 40 - 40 * 0.15
+    assert calc(ORDER, 3, False) == round(discounted + 0 + discounted * 0.22, 2)
+
+
+def test_gold_still_pays_express_surcharge():
+    discounted = 40 - 40 * 0.15
+    assert calc(ORDER, 3, True) == round(discounted + 10 + discounted * 0.22, 2)
+
+
+def test_describe_gold_shows_discount_line():
+    assert describe(ORDER, 3, False) == "\n".join([
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 0.00",
+        "VAT: 7.48",
+        "Total: 41.48",
+    ])
+
+
+def test_describe_regular_unchanged():
+    assert describe(ORDER, 1, True) == "\n".join([
+        "Book x2: 40.00",
+        "Shipping: 15.99",
+        "VAT: 8.80",
+        "Total: 64.79",
+    ])
+
+
+def test_describe_silver_unchanged():
+    assert describe(ORDER, 2, False) == "\n".join([
+        "Book x2: 40.00",
+        "Silver discount: -4.00",
+        "Shipping: 5.99",
+        "VAT: 7.92",
+        "Total: 49.91",
+    ])
```

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
@@ -1,21 +1,46 @@
 # Pricing for the web shop.
 
+# Customer types, passed as `t`. Any other value is priced as regular.
+REGULAR = 1
+SILVER = 2
+GOLD = 3
 
-def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
+
+def _discount(t):
+    # Item discount for customer type t as (label, rate), or None.
+    if t == SILVER:
+        return "Silver", 0.1
+    if t == GOLD:
+        return "Gold", 0.15
+    return None
+
+
+def _shipping(total, t, f):
+    # total: item total after discount
     # f: express shipping
-    total = 0
-    for i in order["items"]:
-        total = total + i["price"] * i["qty"]
-    if t == 2:
-        total = total - total * 0.1
     ship = 0
     if total < 50:
         ship = 5.99
-    if t == 2 and total > 100:
+    if t == SILVER and total > 100:
         ship = 0
+    if t == GOLD:
+        ship = 0  # standard shipping is always free for gold
     if f:
         ship = ship + 10
+    return ship
+
+
+def calc(order, t, f):
+    # t: customer type (1 = regular, 2 = silver, 3 = gold)
+    # f: express shipping
+    total = 0
+    for i in order["items"]:
+        total = total + i["price"] * i["qty"]
+    discount = _discount(t)
+    if discount:
+        _, rate = discount
+        total = total - total * rate
+    ship = _shipping(total, t, f)
     tax = total * 0.22
     return round(total + ship + tax, 2)
 
@@ -26,16 +51,12 @@
     for i in order["items"]:
         lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
         total = total + i["price"] * i["qty"]
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
+    discount = _discount(t)
+    if discount:
+        label, rate = discount
+        lines.append(label + " discount: -" + "%.2f" % (total * rate))
+        total = total - total * rate
+    ship = _shipping(total, t, f)
     lines.append("Shipping: " + "%.2f" % ship)
     tax = total * 0.22
     lines.append("VAT: " + "%.2f" % tax)
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,57 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+BIG_ORDER = {"items": [{"name": "Lamp", "price": 120.0, "qty": 1}]}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+# Regular and silver: pinned to the values from before the gold tier existed.
+
+def test_regular_and_silver_calc_unchanged():
+    assert calc(ORDER, 1, True) == 64.79
+    assert calc(ORDER, 2, False) == 49.91
+    assert calc(ORDER, 2, True) == 59.91
+    assert calc(BIG_ORDER, 2, False) == 131.76
+
+
+def test_silver_describe_unchanged():
+    assert describe(ORDER, 2, False) == (
+        "Book x2: 40.00\n"
+        "Silver discount: -4.00\n"
+        "Shipping: 5.99\n"
+        "VAT: 7.92\n"
+        "Total: 49.91"
+    )
+
+
+def test_regular_describe_has_no_discount_line():
+    assert describe(ORDER, 1, False) == (
+        "Book x2: 40.00\n"
+        "Shipping: 5.99\n"
+        "VAT: 8.80\n"
+        "Total: 54.79"
+    )
+
+
+# Gold: 15% off items, standard shipping always free, express surcharge still applies,
+# VAT on the discounted amount.
+
+def test_gold_small_order_gets_discount_and_free_shipping():
+    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)
+
+
+def test_gold_express_still_pays_surcharge():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_gold_describe():
+    assert describe(ORDER, 3, True) == (
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
@@ -1,43 +1,67 @@
 # Pricing for the web shop.
+from typing import NamedTuple
+
+# Customer types, passed to calc and describe as `t`.
+REGULAR = 1
+SILVER = 2
+GOLD = 3
+
+
+class _Discount(NamedTuple):
+    label: str
+    rate: float
+
+
+_DISCOUNTS = {
+    SILVER: _Discount("Silver", 0.1),
+    GOLD: _Discount("Gold", 0.15),
+}
+
+
+class _Breakdown(NamedTuple):
+    discount: float
+    shipping: float
+    vat: float
+    total: float
 
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
+    # t: customer type (REGULAR, SILVER or GOLD)
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
+    return _breakdown(order, t, f).total
 
 
 def describe(order, t, f):
     lines = []
-    total = 0
     for i in order["items"]:
         lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % (i["price"] * i["qty"]))
+    breakdown = _breakdown(order, t, f)
+    if t in _DISCOUNTS:
+        lines.append(_DISCOUNTS[t].label + " discount: -" + "%.2f" % breakdown.discount)
+    lines.append("Shipping: " + "%.2f" % breakdown.shipping)
+    lines.append("VAT: " + "%.2f" % breakdown.vat)
+    lines.append("Total: " + "%.2f" % breakdown.total)
+    return "\n".join(lines)
+
+
+def _breakdown(order, t, f):
+    # Keep the explicit loop: since Python 3.12, sum() compensates float
+    # rounding errors, which could change existing totals.
+    total = 0
+    for i in order["items"]:
         total = total + i["price"] * i["qty"]
-    if t == 2:
-        lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
-        total = total - total * 0.1
-    ship = 0
+    discount = 0
+    if t in _DISCOUNTS:
+        discount = total * _DISCOUNTS[t].rate
+        total = total - discount
+    shipping = 0
     if total < 50:
-        ship = 5.99
-    if t == 2 and total > 100:
-        ship = 0
+        shipping = 5.99
+    if t == SILVER and total > 100:
+        shipping = 0
+    if t == GOLD:
+        shipping = 0
     if f:
-        ship = ship + 10
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
-    return "\n".join(lines)
+        shipping = shipping + 10
+    vat = total * 0.22
+    return _Breakdown(discount, shipping, vat, round(total + shipping + vat, 2))
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,72 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+FIFTY_ORDER = {"items": [{"name": "Lamp", "price": 50.0, "qty": 1}]}
+LARGE_ORDER = {
+    "items": [
+        {"name": "Book", "price": 20.0, "qty": 2},
+        {"name": "Chair", "price": 110.0, "qty": 1},
+    ]
+}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_regular_order_of_fifty_ships_free():
+    assert calc(FIFTY_ORDER, 1, False) == 61.0
+
+
+def test_regular_express_adds_surcharge_to_shipping():
+    assert calc(ORDER, 1, True) == 64.79
+
+
+def test_silver_small_order_gets_discount_and_pays_shipping():
+    assert calc(ORDER, 2, False) == 49.91
+
+
+def test_silver_shipping_threshold_uses_discounted_amount():
+    assert calc(FIFTY_ORDER, 2, False) == 60.89
+
+
+def test_silver_large_express_order():
+    assert calc(LARGE_ORDER, 2, True) == 174.7
+
+
+def test_describe_regular_express_order():
+    assert describe(ORDER, 1, True) == (
+        "Book x2: 40.00\n"
+        "Shipping: 15.99\n"
+        "VAT: 8.80\n"
+        "Total: 64.79"
+    )
+
+
+def test_describe_silver_order_shows_discount_line():
+    assert describe(LARGE_ORDER, 2, False) == (
+        "Book x2: 40.00\n"
+        "Chair x1: 110.00\n"
+        "Silver discount: -15.00\n"
+        "Shipping: 0.00\n"
+        "VAT: 29.70\n"
+        "Total: 164.70"
+    )
+
+
+def test_gold_small_order_gets_discount_and_free_shipping():
+    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)
+
+
+def test_gold_express_still_pays_surcharge():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_describe_gold_order_shows_discount_line():
+    assert describe(ORDER, 3, False) == (
+        "Book x2: 40.00\n"
+        "Gold discount: -6.00\n"
+        "Shipping: 0.00\n"
+        "VAT: 7.48\n"
+        "Total: 41.48"
+    )
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,71 @@
 # Pricing for the web shop.
 
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class _Tier:
+    name: str
+    discount_rate: float
+    has_free_standard_shipping: bool
+
+
+_REGULAR = _Tier("Regular", discount_rate=0, has_free_standard_shipping=False)
+_TIERS = {
+    1: _REGULAR,
+    2: _Tier("Silver", discount_rate=0.1, has_free_standard_shipping=False),
+    3: _Tier("Gold", discount_rate=0.15, has_free_standard_shipping=True),
+}
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
+    return _price_breakdown(order, _tier(t), f).total
 
 
 def describe(order, t, f):
+    tier = _tier(t)
+    breakdown = _price_breakdown(order, tier, f)
     lines = []
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
+    for item in order["items"]:
+        lines.append(item["name"] + " x" + str(item["qty"]) + ": " + "%.2f" % (item["price"] * item["qty"]))
+    if tier.discount_rate > 0:
+        lines.append(tier.name + " discount: -" + "%.2f" % breakdown.discount)
+    lines.append("Shipping: " + "%.2f" % breakdown.shipping)
+    lines.append("VAT: " + "%.2f" % breakdown.vat)
+    lines.append("Total: " + "%.2f" % breakdown.total)
     return "\n".join(lines)
+
+
+def _tier(t):
+    # Unrecognised customer types have always been priced as regular.
+    return _TIERS.get(t, _REGULAR)
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
+def _price_breakdown(order, tier, express):
+    subtotal = 0
+    for item in order["items"]:
+        subtotal = subtotal + item["price"] * item["qty"]
+    discount = subtotal * tier.discount_rate
+    discounted = subtotal - discount
+    shipping = _shipping(discounted, tier, express)
+    vat = discounted * 0.22
+    return _PriceBreakdown(discount, shipping, vat, round(discounted + shipping + vat, 2))
+
+
+def _shipping(discounted_total, tier, express):
+    shipping = 0
+    if discounted_total < 50 and not tier.has_free_standard_shipping:
+        shipping = 5.99
+    if express:
+        shipping = shipping + 10
+    return shipping
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,68 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+FIFTY_ORDER = {"items": [{"name": "Book", "price": 25.0, "qty": 2}]}
+LARGE_ORDER = {
+    "items": [
+        {"name": "Book", "price": 20.0, "qty": 2},
+        {"name": "Lamp", "price": 80.0, "qty": 1},
+    ]
+}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_regular_order_of_exactly_50_ships_free():
+    assert calc(FIFTY_ORDER, 1, False) == round(50 + 50 * 0.22, 2)
+
+
+def test_regular_express_adds_surcharge_to_shipping():
+    assert calc(ORDER, 1, True) == round(40 + 5.99 + 10 + 40 * 0.22, 2)
+
+
+def test_silver_small_order_gets_10_percent_off_and_pays_shipping():
+    assert calc(ORDER, 2, False) == round(36 + 5.99 + 36 * 0.22, 2)
+
+
+def test_silver_large_express_order_pays_only_the_surcharge():
+    assert calc(LARGE_ORDER, 2, True) == round(108 + 10 + 108 * 0.22, 2)
+
+
+def test_gold_small_order_gets_15_percent_off_and_ships_free():
+    assert calc(ORDER, 3, False) == round(34 + 34 * 0.22, 2)
+
+
+def test_gold_express_order_pays_only_the_surcharge():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_describe_regular_order():
+    assert describe(ORDER, 1, False) == (
+        "Book x2: 40.00\n"
+        "Shipping: 5.99\n"
+        "VAT: 8.80\n"
+        "Total: 54.79"
+    )
+
+
+def test_describe_silver_order_shows_discount_before_shipping():
+    assert describe(LARGE_ORDER, 2, False) == (
+        "Book x2: 40.00\n"
+        "Lamp x1: 80.00\n"
+        "Silver discount: -12.00\n"
+        "Shipping: 0.00\n"
+        "VAT: 23.76\n"
+        "Total: 131.76"
+    )
+
+
+def test_describe_gold_order_shows_discount_before_shipping():
+    assert describe(ORDER, 3, False) == (
+        "Book x2: 40.00\n"
+        "Gold discount: -6.00\n"
+        "Shipping: 0.00\n"
+        "VAT: 7.48\n"
+        "Total: 41.48"
+    )
```

### Implementation 2

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -2,18 +2,22 @@
 
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
+    # t: customer type (1 = regular, 2 = silver, 3 = gold)
     # f: express shipping
     total = 0
     for i in order["items"]:
         total = total + i["price"] * i["qty"]
     if t == 2:
         total = total - total * 0.1
+    elif t == 3:
+        total = total - total * 0.15
     ship = 0
     if total < 50:
         ship = 5.99
     if t == 2 and total > 100:
         ship = 0
+    if t == 3:
+        ship = 0  # gold: standard shipping is always free
     if f:
         ship = ship + 10
     tax = total * 0.22
@@ -29,11 +33,16 @@
     if t == 2:
         lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
         total = total - total * 0.1
+    elif t == 3:
+        lines.append("Gold discount: -" + "%.2f" % (total * 0.15))
+        total = total - total * 0.15
     ship = 0
     if total < 50:
         ship = 5.99
     if t == 2 and total > 100:
         ship = 0
+    if t == 3:
+        ship = 0  # gold: standard shipping is always free
     if f:
         ship = ship + 10
     lines.append("Shipping: " + "%.2f" % ship)
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,35 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_gold_gets_15_percent_discount_and_free_shipping():
+    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)
+
+
+def test_gold_express_still_pays_surcharge():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_gold_describe_shows_gold_discount_line():
+    assert describe(ORDER, 3, False) == "\n".join([
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 0.00",
+        "VAT: 7.48",
+        "Total: 41.48",
+    ])
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
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -2,18 +2,22 @@
 
 
 def calc(order, t, f):
-    # t: customer type (1 = regular, 2 = silver)
+    # t: customer type (1 = regular, 2 = silver, 3 = gold)
     # f: express shipping
     total = 0
     for i in order["items"]:
         total = total + i["price"] * i["qty"]
     if t == 2:
         total = total - total * 0.1
+    elif t == 3:
+        total = total - total * 0.15
     ship = 0
     if total < 50:
         ship = 5.99
     if t == 2 and total > 100:
         ship = 0
+    if t == 3:
+        ship = 0  # gold: standard shipping is always free
     if f:
         ship = ship + 10
     tax = total * 0.22
@@ -29,11 +33,16 @@
     if t == 2:
         lines.append("Silver discount: -" + "%.2f" % (total * 0.1))
         total = total - total * 0.1
+    elif t == 3:
+        lines.append("Gold discount: -" + "%.2f" % (total * 0.15))
+        total = total - total * 0.15
     ship = 0
     if total < 50:
         ship = 5.99
     if t == 2 and total > 100:
         ship = 0
+    if t == 3:
+        ship = 0  # gold: standard shipping is always free
     if f:
         ship = ship + 10
     lines.append("Shipping: " + "%.2f" % ship)
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -5,3 +5,50 @@
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+# --- gold tier (customer type 3) ---
+
+from shop.pricing import describe
+
+BIG_ORDER = {"items": [{"name": "Lamp", "price": 80.0, "qty": 2}]}
+
+
+def test_gold_gets_15_percent_discount_and_free_standard_shipping():
+    # 40 - 15% = 34 (below the 50 threshold, but gold never pays standard shipping)
+    assert calc(ORDER, 3, False) == round(34 + 0 + 34 * 0.22, 2)
+
+
+def test_gold_express_surcharge_still_applies():
+    assert calc(ORDER, 3, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_gold_large_order():
+    # 160 - 15% = 136
+    assert calc(BIG_ORDER, 3, False) == round(136 + 136 * 0.22, 2)
+
+
+def test_gold_describe_shows_discount_line():
+    assert describe(ORDER, 3, True) == "\n".join([
+        "Book x2: 40.00",
+        "Gold discount: -6.00",
+        "Shipping: 10.00",
+        "VAT: 7.48",
+        "Total: 51.48",
+    ])
+
+
+def test_regular_and_silver_describe_unchanged():
+    assert describe(ORDER, 1, False) == "\n".join([
+        "Book x2: 40.00",
+        "Shipping: 5.99",
+        "VAT: 8.80",
+        "Total: 54.79",
+    ])
+    assert describe(BIG_ORDER, 2, False) == "\n".join([
+        "Lamp x2: 160.00",
+        "Silver discount: -16.00",
+        "Shipping: 0.00",
+        "VAT: 31.68",
+        "Total: 175.68",
+    ])
```

### Implementation 2

```diff
diff -ruN before/shop/pricing.py after/shop/pricing.py
--- before/shop/pricing.py
+++ after/shop/pricing.py
@@ -1,43 +1,70 @@
 # Pricing for the web shop.
 
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class _Tier:
+    name: str
+    discount_rate: float
+    has_free_standard_shipping: bool
+
+
+_REGULAR = _Tier("Regular", 0, False)
+
+_TIERS_BY_CUSTOMER_TYPE = {
+    1: _REGULAR,
+    2: _Tier("Silver", 0.1, False),
+    3: _Tier("Gold", 0.15, True),
+}
+
+
+@dataclass(frozen=True)
+class _PriceBreakdown:
+    discount: float
+    shipping: float
+    tax: float
+    total: float
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
+    return _price_order(order, _tier_for(t), f).total
 
 
 def describe(order, t, f):
+    tier = _tier_for(t)
+    breakdown = _price_order(order, tier, f)
     lines = []
-    total = 0
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
-    lines.append("Shipping: " + "%.2f" % ship)
-    tax = total * 0.22
-    lines.append("VAT: " + "%.2f" % tax)
-    lines.append("Total: " + "%.2f" % round(total + ship + tax, 2))
+        lines.append(i["name"] + " x" + str(i["qty"]) + ": " + "%.2f" % _line_amount(i))
+    if tier.discount_rate:
+        lines.append(tier.name + " discount: -" + "%.2f" % breakdown.discount)
+    lines.append("Shipping: " + "%.2f" % breakdown.shipping)
+    lines.append("VAT: " + "%.2f" % breakdown.tax)
+    lines.append("Total: " + "%.2f" % breakdown.total)
     return "\n".join(lines)
+
+
+def _tier_for(customer_type):
+    return _TIERS_BY_CUSTOMER_TYPE.get(customer_type, _REGULAR)
+
+
+def _price_order(order, tier, express):
+    subtotal = 0
+    for i in order["items"]:
+        subtotal = subtotal + _line_amount(i)
+    discount = subtotal * tier.discount_rate
+    discounted_subtotal = subtotal - discount
+    shipping = 0
+    if discounted_subtotal < 50 and not tier.has_free_standard_shipping:
+        shipping = 5.99
+    if express:
+        shipping = shipping + 10
+    tax = discounted_subtotal * 0.22
+    return _PriceBreakdown(discount, shipping, tax, round(discounted_subtotal + shipping + tax, 2))
+
+
+def _line_amount(item):
+    return item["price"] * item["qty"]
diff -ruN before/tests/test_pricing.py after/tests/test_pricing.py
--- before/tests/test_pricing.py
+++ after/tests/test_pricing.py
@@ -1,7 +1,71 @@
-from shop.pricing import calc
+from shop.pricing import calc, describe
+
+REGULAR = 1
+SILVER = 2
+GOLD = 3
 
 ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 2}]}
+LARGE_ORDER = {"items": [{"name": "Book", "price": 20.0, "qty": 6}]}
+# 55.00 before the silver discount, 49.50 after it: crosses the free-shipping threshold.
+MIXED_ORDER = {"items": [{"name": "Pen", "price": 1.5, "qty": 4}, {"name": "Lamp", "price": 49.0, "qty": 1}]}
+EMPTY_ORDER = {"items": []}
 
 
 def test_regular_small_order_pays_shipping():
     assert calc(ORDER, 1, False) == round(40 + 5.99 + 40 * 0.22, 2)
+
+
+def test_regular_order_over_50_ships_free():
+    assert calc(MIXED_ORDER, REGULAR, False) == 67.1
+
+
+def test_regular_express_adds_surcharge_to_shipping():
+    assert calc(ORDER, REGULAR, True) == 64.79
+
+
+def test_silver_discount_can_bring_order_under_free_shipping_threshold():
+    assert calc(MIXED_ORDER, SILVER, False) == 66.38
+
+
+def test_silver_large_order():
+    assert calc(LARGE_ORDER, SILVER, False) == 131.76
+
+
+def test_silver_express_adds_surcharge():
+    assert calc(LARGE_ORDER, SILVER, True) == 141.76
+
+
+def test_describe_regular_order():
+    assert describe(MIXED_ORDER, REGULAR, True) == (
+        "Pen x4: 6.00\nLamp x1: 49.00\nShipping: 10.00\nVAT: 12.10\nTotal: 77.10"
+    )
+
+
+def test_describe_silver_order_shows_discount_line():
+    assert describe(MIXED_ORDER, SILVER, False) == (
+        "Pen x4: 6.00\nLamp x1: 49.00\nSilver discount: -5.50\nShipping: 5.99\nVAT: 10.89\nTotal: 66.38"
+    )
+
+
+def test_describe_silver_empty_order_still_shows_discount_line():
+    assert describe(EMPTY_ORDER, SILVER, False) == (
+        "Silver discount: -0.00\nShipping: 5.99\nVAT: 0.00\nTotal: 5.99"
+    )
+
+
+def test_gold_gets_15_percent_discount_with_vat_on_discounted_amount():
+    assert calc(LARGE_ORDER, GOLD, False) == round(102 + 102 * 0.22, 2)
+
+
+def test_gold_small_order_ships_free():
+    assert calc(ORDER, GOLD, False) == round(34 + 34 * 0.22, 2)
+
+
+def test_gold_express_still_pays_surcharge():
+    assert calc(ORDER, GOLD, True) == round(34 + 10 + 34 * 0.22, 2)
+
+
+def test_describe_gold_order_shows_discount_line():
+    assert describe(ORDER, GOLD, False) == (
+        "Book x2: 40.00\nGold discount: -6.00\nShipping: 0.00\nVAT: 7.48\nTotal: 41.48"
+    )
```

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

Users report two bugs in `pager/pagination.py`: page 1 skips the first items, and the last, partially filled page is never counted. Fix them.

Expected behavior:
- `page` is 1-based: `paginate(items, 1, per_page)` returns the first `per_page` items.
- A page past the end returns an empty list.
- `total_pages(item_count, per_page)` counts a partially filled last page. `total_pages(0, per_page)` is 0.
- Invalid input raises `ValueError`: `page < 1` or `per_page < 1` in `paginate`; `per_page < 1` or a negative `item_count` in `total_pages`.

## Pair 1

### Implementation 1

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,22 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page, or [] past the end."""
+    if page < 1:
+        raise ValueError(f"page must be at least 1, got {page}")
+    _require_valid_per_page(per_page)
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
     """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    if item_count < 0:
+        raise ValueError(f"item_count must not be negative, got {item_count}")
+    _require_valid_per_page(per_page)
+    full_pages, leftover_items = divmod(item_count, per_page)
+    return full_pages + 1 if leftover_items else full_pages
+
+
+def _require_valid_per_page(per_page):
+    if per_page < 1:
+        raise ValueError(f"per_page must be at least 1, got {per_page}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,60 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+ITEMS = list(range(1, 26))
+
+
+def test_paginate_first_page_starts_at_first_item():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_second_page_follows_first():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_last_page_is_partially_filled():
+    assert paginate(ITEMS, 3, per_page=10) == list(range(21, 26))
+
+
+def test_paginate_page_past_the_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_page_below_one(page):
+    with pytest.raises(ValueError, match="page"):
+        paginate(ITEMS, page, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_paginate_rejects_per_page_below_one(per_page):
+    with pytest.raises(ValueError, match="per_page"):
+        paginate(ITEMS, 1, per_page=per_page)
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partially_filled_last_page():
+    assert total_pages(25, per_page=10) == 3
+
+
+def test_total_pages_fewer_items_than_one_page():
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_no_items_is_zero():
+    assert total_pages(0, per_page=10) == 0
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_total_pages_rejects_per_page_below_one(per_page):
+    with pytest.raises(ValueError, match="per_page"):
+        total_pages(20, per_page=per_page)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError, match="item_count"):
+        total_pages(-1, per_page=10)
```

### Implementation 2

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,26 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page.
+
+    A page past the end returns an empty list.
+    Raises ValueError if page or per_page is less than 1.
+    """
+    if page < 1:
+        raise ValueError(f"page must be >= 1, got {page}")
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page; 0 items need 0 pages.
+    Raises ValueError if per_page is less than 1 or item_count is negative.
+    """
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
+    if item_count < 0:
+        raise ValueError(f"item_count must be >= 0, got {item_count}")
+    return -(-item_count // per_page)
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,64 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+
+ITEMS = list(range(1, 26))  # 25 items: 1..25
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partial_last_page():
+    assert total_pages(25, per_page=10) == 3
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_zero_items():
+    assert total_pages(0, per_page=10) == 0
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_total_pages_rejects_invalid_per_page(per_page):
+    with pytest.raises(ValueError):
+        total_pages(10, per_page=per_page)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError):
+        total_pages(-1, per_page=10)
+
+
+def test_paginate_first_page_starts_at_first_item():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_partial_last_page():
+    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]
+
+
+def test_paginate_page_past_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_pages_cover_all_items_exactly_once():
+    pages = total_pages(len(ITEMS), per_page=10)
+    collected = [x for p in range(1, pages + 1) for x in paginate(ITEMS, p, per_page=10)]
+    assert collected == ITEMS
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_invalid_page(page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, page, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_paginate_rejects_invalid_per_page(per_page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 1, per_page=per_page)
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,26 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page.
+
+    A page past the end returns an empty list.
+    Raises ValueError if page < 1 or per_page < 1.
+    """
+    if page < 1:
+        raise ValueError(f"page must be >= 1, got {page}")
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page; 0 items need 0 pages.
+    Raises ValueError if item_count < 0 or per_page < 1.
+    """
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
+    if item_count < 0:
+        raise ValueError(f"item_count must be >= 0, got {item_count}")
+    return (item_count + per_page - 1) // per_page  # ceiling division
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,64 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+
+ITEMS = list(range(1, 26))  # 25 items: 1..25
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partial_last_page():
+    assert total_pages(21, per_page=10) == 3
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_zero_items():
+    assert total_pages(0, per_page=10) == 0
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_total_pages_rejects_invalid_per_page(per_page):
+    with pytest.raises(ValueError):
+        total_pages(10, per_page=per_page)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError):
+        total_pages(-1, per_page=10)
+
+
+def test_paginate_first_page_starts_at_first_item():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_partial_last_page():
+    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]
+
+
+def test_paginate_past_the_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_every_item_appears_on_exactly_one_page():
+    pages = total_pages(len(ITEMS), per_page=10)
+    collected = [x for p in range(1, pages + 1) for x in paginate(ITEMS, p, 10)]
+    assert collected == ITEMS
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_invalid_page(page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, page, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_paginate_rejects_invalid_per_page(per_page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 1, per_page=per_page)
```

### Implementation 2

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,22 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page; a page past the end is empty."""
+    if page < 1:
+        raise ValueError(f"page must be at least 1, got {page}")
+    _validate_per_page(per_page)
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
     """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    if item_count < 0:
+        raise ValueError(f"item_count must not be negative, got {item_count}")
+    _validate_per_page(per_page)
+    full_pages, leftover_items = divmod(item_count, per_page)
+    return full_pages + 1 if leftover_items else full_pages
+
+
+def _validate_per_page(per_page):
+    if per_page < 1:
+        raise ValueError(f"per_page must be at least 1, got {per_page}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,54 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+
+ITEMS = list(range(1, 26))
+
+
+def test_paginate_first_page_starts_with_first_item():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_second_page_continues_after_first():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_last_page_holds_remaining_items():
+    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]
+
+
+def test_paginate_page_past_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_rejects_page_below_one():
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 0, per_page=10)
+
+
+def test_paginate_rejects_per_page_below_one():
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 1, per_page=0)
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partially_filled_last_page():
+    assert total_pages(21, per_page=10) == 3
+
+
+def test_total_pages_of_no_items_is_zero():
+    assert total_pages(0, per_page=10) == 0
+
+
+def test_total_pages_rejects_per_page_below_one():
+    with pytest.raises(ValueError):
+        total_pages(20, per_page=0)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError):
+        total_pages(-1, per_page=10)
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,22 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page; empty past the last page."""
+    if page < 1:
+        raise ValueError(f"page must be at least 1, got {page}")
+    _check_per_page(per_page)
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
     """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    if item_count < 0:
+        raise ValueError(f"item_count must not be negative, got {item_count}")
+    _check_per_page(per_page)
+    full_pages, leftover_items = divmod(item_count, per_page)
+    return full_pages + 1 if leftover_items else full_pages
+
+
+def _check_per_page(per_page):
+    if per_page < 1:
+        raise ValueError(f"per_page must be at least 1, got {per_page}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,57 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+ITEMS = list(range(1, 26))
+
+
+def test_paginate_first_page_returns_first_items():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_second_page_returns_next_items():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_last_page_returns_remaining_items():
+    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]
+
+
+def test_paginate_page_past_end_returns_empty_list():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_rejects_page_below_one():
+    with pytest.raises(ValueError, match="page"):
+        paginate(ITEMS, 0, per_page=10)
+
+
+def test_paginate_rejects_per_page_below_one():
+    with pytest.raises(ValueError, match="per_page"):
+        paginate(ITEMS, 1, per_page=0)
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partially_filled_last_page():
+    assert total_pages(21, per_page=10) == 3
+
+
+def test_total_pages_fewer_items_than_one_page():
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_no_items_is_zero():
+    assert total_pages(0, per_page=10) == 0
+
+
+def test_total_pages_rejects_per_page_below_one():
+    with pytest.raises(ValueError, match="per_page"):
+        total_pages(20, per_page=0)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError, match="item_count"):
+        total_pages(-1, per_page=10)
```

### Implementation 2

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,26 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page.
+
+    A page past the end returns an empty list.
+    Raises ValueError if page < 1 or per_page < 1.
+    """
+    if page < 1:
+        raise ValueError(f"page must be >= 1, got {page}")
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page; 0 items need 0 pages.
+    Raises ValueError if item_count < 0 or per_page < 1.
+    """
+    if item_count < 0:
+        raise ValueError(f"item_count must be >= 0, got {item_count}")
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
+    return (item_count + per_page - 1) // per_page
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,72 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+
+ITEMS = list(range(25))
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partial_last_page():
+    assert total_pages(25, per_page=10) == 3
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_zero_items():
+    assert total_pages(0, per_page=10) == 0
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_total_pages_rejects_invalid_per_page(per_page):
+    with pytest.raises(ValueError):
+        total_pages(10, per_page=per_page)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError):
+        total_pages(-1, per_page=10)
+
+
+def test_paginate_first_page_starts_at_first_item():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(10))
+
+
+def test_paginate_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(10, 20))
+
+
+def test_paginate_partial_last_page():
+    assert paginate(ITEMS, 3, per_page=10) == list(range(20, 25))
+
+
+def test_paginate_past_the_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_empty_items():
+    assert paginate([], 1, per_page=10) == []
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_invalid_page(page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, page, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_paginate_rejects_invalid_per_page(per_page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 1, per_page=per_page)
+
+
+def test_every_page_up_to_total_is_non_empty_and_covers_all_items():
+    pages = total_pages(len(ITEMS), per_page=10)
+    collected = []
+    for page in range(1, pages + 1):
+        chunk = paginate(ITEMS, page, per_page=10)
+        assert chunk
+        collected.extend(chunk)
+    assert collected == ITEMS
```

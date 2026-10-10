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
@@ -1,10 +1,29 @@
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
+    _require_positive_per_page(per_page)
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page; zero items need zero pages.
+    Raises ValueError if item_count < 0 or per_page < 1.
+    """
+    if item_count < 0:
+        raise ValueError(f"item_count must be >= 0, got {item_count}")
+    _require_positive_per_page(per_page)
+    return -(-item_count // per_page)
+
+
+def _require_positive_per_page(per_page):
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,71 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+ITEMS = list(range(25))
+
+
+def test_first_page_returns_first_items():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(10))
+
+
+def test_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(10, 20))
+
+
+def test_partial_last_page():
+    assert paginate(ITEMS, 3, per_page=10) == [20, 21, 22, 23, 24]
+
+
+def test_page_past_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_empty_items():
+    assert paginate([], 1, per_page=10) == []
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_page_below_one(page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, page, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -5])
+def test_paginate_rejects_per_page_below_one(per_page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 1, per_page=per_page)
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partial_last_page():
+    assert total_pages(25, per_page=10) == 3
+
+
+def test_total_pages_fewer_items_than_one_page():
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_zero_items():
+    assert total_pages(0, per_page=10) == 0
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError):
+        total_pages(-1, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -5])
+def test_total_pages_rejects_per_page_below_one(per_page):
+    with pytest.raises(ValueError):
+        total_pages(10, per_page=per_page)
+
+
+def test_every_item_appears_on_exactly_one_page():
+    per_page = 7
+    pages = range(1, total_pages(len(ITEMS), per_page) + 1)
+    shown = [item for page in pages for item in paginate(ITEMS, page, per_page)]
+    assert shown == ITEMS
```

### Implementation 2

```diff
diff -ruN before/.mypy_cache/.gitignore after/.mypy_cache/.gitignore
--- before/.mypy_cache/.gitignore
+++ after/.mypy_cache/.gitignore
@@ -0,0 +1,2 @@
+# Automatically created by mypy
+*
Binary files before/.mypy_cache/3.13/cache.0.db and after/.mypy_cache/3.13/cache.0.db differ
Binary files before/.mypy_cache/3.13/cache.1.db and after/.mypy_cache/3.13/cache.1.db differ
Binary files before/.mypy_cache/3.13/cache.10.db and after/.mypy_cache/3.13/cache.10.db differ
Binary files before/.mypy_cache/3.13/cache.11.db and after/.mypy_cache/3.13/cache.11.db differ
Binary files before/.mypy_cache/3.13/cache.12.db and after/.mypy_cache/3.13/cache.12.db differ
Binary files before/.mypy_cache/3.13/cache.13.db and after/.mypy_cache/3.13/cache.13.db differ
Binary files before/.mypy_cache/3.13/cache.14.db and after/.mypy_cache/3.13/cache.14.db differ
Binary files before/.mypy_cache/3.13/cache.15.db and after/.mypy_cache/3.13/cache.15.db differ
Binary files before/.mypy_cache/3.13/cache.2.db and after/.mypy_cache/3.13/cache.2.db differ
Binary files before/.mypy_cache/3.13/cache.3.db and after/.mypy_cache/3.13/cache.3.db differ
Binary files before/.mypy_cache/3.13/cache.4.db and after/.mypy_cache/3.13/cache.4.db differ
Binary files before/.mypy_cache/3.13/cache.5.db and after/.mypy_cache/3.13/cache.5.db differ
Binary files before/.mypy_cache/3.13/cache.6.db and after/.mypy_cache/3.13/cache.6.db differ
Binary files before/.mypy_cache/3.13/cache.7.db and after/.mypy_cache/3.13/cache.7.db differ
Binary files before/.mypy_cache/3.13/cache.8.db and after/.mypy_cache/3.13/cache.8.db differ
Binary files before/.mypy_cache/3.13/cache.9.db and after/.mypy_cache/3.13/cache.9.db differ
diff -ruN before/.mypy_cache/CACHEDIR.TAG after/.mypy_cache/CACHEDIR.TAG
--- before/.mypy_cache/CACHEDIR.TAG
+++ after/.mypy_cache/CACHEDIR.TAG
@@ -0,0 +1,3 @@
+Signature: 8a477f597d28d172789f06886806bc55
+# This file is a cache directory tag automatically created by mypy.
+# For information about cache directory tags see https://bford.info/cachedir/
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,36 @@
-def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+DEFAULT_PER_PAGE = 10
+
+
+def paginate(items, page, per_page=DEFAULT_PER_PAGE):
+    """Return the items shown on the given 1-based page.
+
+    A page past the end returns an empty list.
+    Raises ValueError if page or per_page is less than 1.
+    """
+    if page < 1:
+        raise ValueError(f"page must be at least 1, got {page}")
+    _validate_per_page(per_page)
+
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
-def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+def total_pages(item_count, per_page=DEFAULT_PER_PAGE):
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page; zero items need zero pages.
+    Raises ValueError if item_count is negative or per_page is less than 1.
+    """
+    if item_count < 0:
+        raise ValueError(f"item_count must not be negative, got {item_count}")
+    _validate_per_page(per_page)
+
+    full_pages, leftover_items = divmod(item_count, per_page)
+    has_partial_page = leftover_items > 0
+    return full_pages + 1 if has_partial_page else full_pages
+
+
+def _validate_per_page(per_page):
+    if per_page < 1:
+        raise ValueError(f"per_page must be at least 1, got {per_page}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,75 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+ITEMS = list(range(1, 26))  # 25 items: pages of 10, 10 and 5
+
+
+def test_paginate_first_page_returns_first_items():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_middle_page_returns_following_items():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_last_partial_page_returns_remaining_items():
+    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]
+
+
+def test_paginate_page_past_the_end_returns_empty_list():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_empty_items_returns_empty_list():
+    assert paginate([], 1, per_page=10) == []
+
+
+def test_paginate_uses_default_page_size():
+    assert paginate(ITEMS, 1) == list(range(1, 11))
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
+def test_total_pages_single_item_needs_one_page():
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_no_items_needs_no_pages():
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
+
+
+def test_total_pages_matches_number_of_non_empty_pages():
+    page_count = total_pages(len(ITEMS), per_page=10)
+
+    assert paginate(ITEMS, page_count, per_page=10) != []
+    assert paginate(ITEMS, page_count + 1, per_page=10) == []
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,32 @@
-def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
-    end = start + per_page
-    return items[start:end]
+DEFAULT_PER_PAGE = 10
 
 
-def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+def paginate(items, page, per_page=DEFAULT_PER_PAGE):
+    """Return the items shown on the given 1-based page.
+
+    A page past the end returns an empty list.
+    Raises ValueError if page or per_page is less than 1.
+    """
+    if page < 1:
+        raise ValueError(f"page must be at least 1, got {page}")
+    _validate_per_page(per_page)
+    start = (page - 1) * per_page
+    return items[start : start + per_page]
+
+
+def total_pages(item_count, per_page=DEFAULT_PER_PAGE):
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page.
+    Raises ValueError if item_count is negative or per_page is less than 1.
+    """
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
@@ -1,5 +1,64 @@
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
+def test_paginate_middle_page_returns_following_items():
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
+def test_paginate_empty_items_returns_empty_list():
+    assert paginate([], 1, per_page=10) == []
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_page_below_one(page):
+    with pytest.raises(ValueError, match=r"^page\b"):
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
+def test_total_pages_single_item_needs_one_page():
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_no_items_needs_no_pages():
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
+    return (item_count + per_page - 1) // per_page
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,74 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+ITEMS = list(range(1, 26))  # 25 items: 1..25
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partial_last_page():
+    assert total_pages(25, per_page=10) == 3
+
+
+def test_total_pages_fewer_items_than_one_page():
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
+def test_paginate_first_page_returns_first_items():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(1, 11))
+
+
+def test_paginate_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_partial_last_page():
+    assert paginate(ITEMS, 3, per_page=10) == list(range(21, 26))
+
+
+def test_paginate_page_past_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_empty_items():
+    assert paginate([], 1, per_page=10) == []
+
+
+def test_every_counted_page_is_non_empty():
+    pages = total_pages(len(ITEMS), per_page=10)
+    collected = []
+    for page in range(1, pages + 1):
+        chunk = paginate(ITEMS, page, per_page=10)
+        assert chunk
+        collected.extend(chunk)
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

## Pair 3

### Implementation 1

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,29 @@
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
+    _require_positive_per_page(per_page)
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page.
+    Raises ValueError if item_count is negative or per_page is less than 1.
+    """
+    if item_count < 0:
+        raise ValueError(f"item_count must be >= 0, got {item_count}")
+    _require_positive_per_page(per_page)
+    return -(-item_count // per_page)
+
+
+def _require_positive_per_page(per_page):
+    if per_page < 1:
+        raise ValueError(f"per_page must be >= 1, got {per_page}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,72 @@
-from pager.pagination import total_pages
+import pytest
+
+from pager.pagination import paginate, total_pages
+
+ITEMS = list(range(25))
+
+
+def test_first_page_starts_at_first_item():
+    assert paginate(ITEMS, 1, per_page=10) == list(range(10))
+
+
+def test_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(10, 20))
+
+
+def test_partial_last_page():
+    assert paginate(ITEMS, 3, per_page=10) == list(range(20, 25))
+
+
+def test_page_past_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_empty_items_first_page_is_empty():
+    assert paginate([], 1, per_page=10) == []
+
+
+@pytest.mark.parametrize("page", [0, -1])
+def test_paginate_rejects_page_below_one(page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, page, per_page=10)
+
+
+@pytest.mark.parametrize("per_page", [0, -5])
+def test_paginate_rejects_per_page_below_one(per_page):
+    with pytest.raises(ValueError):
+        paginate(ITEMS, 1, per_page=per_page)
 
 
 def test_total_pages_exact_multiple():
     assert total_pages(20, per_page=10) == 2
+
+
+def test_total_pages_counts_partial_last_page():
+    assert total_pages(25, per_page=10) == 3
+
+
+def test_total_pages_fewer_items_than_one_page():
+    assert total_pages(1, per_page=10) == 1
+
+
+def test_total_pages_zero_items():
+    assert total_pages(0, per_page=10) == 0
+
+
+@pytest.mark.parametrize("per_page", [0, -1])
+def test_total_pages_rejects_per_page_below_one(per_page):
+    with pytest.raises(ValueError):
+        total_pages(10, per_page=per_page)
+
+
+def test_total_pages_rejects_negative_item_count():
+    with pytest.raises(ValueError):
+        total_pages(-1, per_page=10)
+
+
+@pytest.mark.parametrize("count", [0, 1, 9, 10, 11, 25, 100])
+def test_total_pages_agrees_with_paginate(count):
+    items = list(range(count))
+    pages = total_pages(count, per_page=10)
+    assert sum(len(paginate(items, p, per_page=10)) for p in range(1, pages + 1)) == count
+    assert paginate(items, pages + 1, per_page=10) == []
```

### Implementation 2

```diff
diff -ruN before/pager/pagination.py after/pager/pagination.py
--- before/pager/pagination.py
+++ after/pager/pagination.py
@@ -1,10 +1,29 @@
 def paginate(items, page, per_page=10):
-    """Return the items shown on the given page."""
-    start = page * per_page
+    """Return the items shown on the given 1-based page.
+
+    A page past the end returns an empty list.
+    Raises ValueError if page or per_page is less than 1.
+    """
+    _require_at_least_one("page", page)
+    _require_at_least_one("per_page", per_page)
+    start = (page - 1) * per_page
     end = start + per_page
     return items[start:end]
 
 
 def total_pages(item_count, per_page=10):
-    """Return how many pages are needed to show item_count items."""
-    return item_count // per_page
+    """Return how many pages are needed to show item_count items.
+
+    A partially filled last page counts as a page.
+    Raises ValueError if per_page is less than 1 or item_count is negative.
+    """
+    _require_at_least_one("per_page", per_page)
+    if item_count < 0:
+        raise ValueError(f"item_count must not be negative, got {item_count}")
+    full_pages, leftover_items = divmod(item_count, per_page)
+    return full_pages + (1 if leftover_items else 0)
+
+
+def _require_at_least_one(name, value):
+    if value < 1:
+        raise ValueError(f"{name} must be at least 1, got {value}")
diff -ruN before/tests/test_pagination.py after/tests/test_pagination.py
--- before/tests/test_pagination.py
+++ after/tests/test_pagination.py
@@ -1,5 +1,64 @@
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
+def test_paginate_middle_page():
+    assert paginate(ITEMS, 2, per_page=10) == list(range(11, 21))
+
+
+def test_paginate_last_page_is_partially_filled():
+    assert paginate(ITEMS, 3, per_page=10) == [21, 22, 23, 24, 25]
+
+
+def test_paginate_page_past_end_is_empty():
+    assert paginate(ITEMS, 4, per_page=10) == []
+
+
+def test_paginate_empty_items_is_empty():
+    assert paginate([], 1, per_page=10) == []
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
+def test_total_pages_single_item_needs_one_page():
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

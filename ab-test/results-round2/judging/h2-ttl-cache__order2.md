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

Create `cache/store.py` with an in-memory cache that has a size limit, optional expiry, hit statistics and a memoizing decorator.

`Cache(max_size, ttl_seconds=None, clock=time.monotonic)`
- `max_size` is the maximum number of entries. It must be an integer greater than 0.
- `ttl_seconds` is how long an entry lives after it was last set. `None` means entries never expire. Otherwise it must be a number greater than 0.
- `clock` is a zero-argument callable that returns the current time in seconds.
- Invalid arguments raise `ValueError`.
- An entry is expired once `ttl_seconds` or more have passed since it was last set. Expired entries behave as if they were absent.

Methods:
- `set(key, value)` stores the value, replacing any previous one, restarts its expiry, and makes it the most recently used entry. When a new key is added to a full cache, expired entries are removed first. If the cache is still full, the least recently used entry is evicted.
- `get(key, default=None)` returns the value and makes the entry the most recently used, counting a hit. If the key is absent or expired, it returns `default` and counts a miss.
- `delete(key)` removes the key. It returns `True` if a live entry was removed, otherwise `False`.
- `clear()` removes all entries. It does not reset the statistics.
- `len(cache)` is the number of live entries, and `key in cache` tells whether a key has a live entry. Neither counts as a hit or a miss, nor changes which entry is least recently used.
- `stats()` returns an object with integer attributes `hits`, `misses` and `evictions`. `evictions` counts only entries removed to make room, not expired or deleted ones.

`memoize(cache)` is a decorator factory. `@memoize(cache)` caches a function's results by its positional and keyword arguments, which you can assume are hashable.
- It uses the cache's normal lookup, so hits and misses are counted.
- Results are cached even when they are `None`.
- Several functions can share one cache without their entries colliding.

## Pair 1

### Implementation 1

```diff
diff -ruN before/cache/store.py after/cache/store.py
--- before/cache/store.py
+++ after/cache/store.py
@@ -0,0 +1,144 @@
+"""An in-memory cache with a size limit, optional expiry, hit statistics and memoization."""
+
+import functools
+import numbers
+import time
+from collections import OrderedDict
+from collections.abc import Callable, Hashable
+from dataclasses import dataclass
+from typing import Any
+
+_MISSING = object()
+
+
+@dataclass(frozen=True)
+class CacheStats:
+    hits: int
+    misses: int
+    evictions: int
+
+
+@dataclass(frozen=True, slots=True)
+class _Entry:
+    value: Any
+    set_at: float
+
+
+class Cache:
+    """A least-recently-used cache whose entries optionally expire ``ttl_seconds`` after they were last set.
+
+    Expired entries behave as if they were absent.
+    """
+
+    def __init__(
+        self,
+        max_size: int,
+        ttl_seconds: float | None = None,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not _is_positive_integer(max_size):
+            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
+        if ttl_seconds is not None and not _is_positive_number(ttl_seconds):
+            raise ValueError(f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}")
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+        self._max_size = max_size
+        self._ttl_seconds = ttl_seconds
+        self._clock = clock
+        self._entries: OrderedDict[Hashable, _Entry] = OrderedDict()
+        self._hits = 0
+        self._misses = 0
+        self._evictions = 0
+
+    def set(self, key: Hashable, value: Any) -> None:
+        """Store ``value`` as the most recently used entry and restart its expiry.
+
+        Adding a new key to a full cache first removes expired entries, then evicts the least recently used one.
+        """
+        now = self._clock()
+        if key not in self._entries and self._is_full():
+            self._make_room(now)
+        self._entries[key] = _Entry(value, set_at=now)
+        self._entries.move_to_end(key)
+
+    def get(self, key: Hashable, default: Any = None) -> Any:
+        """Return the live value for ``key`` and mark it most recently used, or ``default`` if there is none."""
+        entry = self._live_entry(key, self._clock())
+        if entry is None:
+            self._misses += 1
+            return default
+        self._entries.move_to_end(key)
+        self._hits += 1
+        return entry.value
+
+    def delete(self, key: Hashable) -> bool:
+        """Remove ``key`` and return whether it had a live entry."""
+        entry = self._entries.pop(key, None)
+        return entry is not None and not self._is_expired(entry, self._clock())
+
+    def clear(self) -> None:
+        """Remove all entries, keeping the statistics."""
+        self._entries.clear()
+
+    def stats(self) -> CacheStats:
+        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)
+
+    def __len__(self) -> int:
+        now = self._clock()
+        return sum(1 for entry in self._entries.values() if not self._is_expired(entry, now))
+
+    def __contains__(self, key: object) -> bool:
+        return self._live_entry(key, self._clock()) is not None
+
+    def _is_full(self) -> bool:
+        return len(self._entries) >= self._max_size
+
+    def _make_room(self, now: float) -> None:
+        self._remove_expired(now)
+        if self._is_full():
+            self._entries.popitem(last=False)
+            self._evictions += 1
+
+    def _remove_expired(self, now: float) -> None:
+        expired_keys = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
+        for key in expired_keys:
+            del self._entries[key]
+
+    def _live_entry(self, key: object, now: float) -> _Entry | None:
+        entry = self._entries.get(key)
+        if entry is None or self._is_expired(entry, now):
+            return None
+        return entry
+
+    def _is_expired(self, entry: _Entry, now: float) -> bool:
+        return self._ttl_seconds is not None and now - entry.set_at >= self._ttl_seconds
+
+
+def memoize(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
+    """Cache a function's results in ``cache``, keyed by its positional and keyword arguments.
+
+    The arguments must be hashable. Several functions can share one cache.
+    """
+
+    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
+        @functools.wraps(func)
+        def wrapper(*args: Any, **kwargs: Any) -> Any:
+            # The function is part of the key so that functions sharing a cache never collide.
+            call_key = (func, args, frozenset(kwargs.items()))
+            result = cache.get(call_key, _MISSING)
+            if result is _MISSING:
+                result = func(*args, **kwargs)
+                cache.set(call_key, result)
+            return result
+
+        return wrapper
+
+    return decorate
+
+
+def _is_positive_integer(value: object) -> bool:
+    return isinstance(value, numbers.Integral) and not isinstance(value, bool) and value > 0
+
+
+def _is_positive_number(value: object) -> bool:
+    return isinstance(value, numbers.Real) and not isinstance(value, bool) and value > 0
diff -ruN before/tests/test_store.py after/tests/test_store.py
--- before/tests/test_store.py
+++ after/tests/test_store.py
@@ -0,0 +1,329 @@
+import pytest
+
+from cache.store import Cache, memoize
+
+
+class FakeClock:
+    def __init__(self) -> None:
+        self.now = 0.0
+
+    def __call__(self) -> float:
+        return self.now
+
+    def advance(self, seconds: float) -> None:
+        self.now += seconds
+
+
+@pytest.fixture
+def clock() -> FakeClock:
+    return FakeClock()
+
+
+# Construction
+
+
+@pytest.mark.parametrize("max_size", [0, -1, 1.5, 2.0, "3", None, True])
+def test_rejects_invalid_max_size(max_size):
+    with pytest.raises(ValueError, match="max_size"):
+        Cache(max_size)
+
+
+@pytest.mark.parametrize("ttl_seconds", [0, -1, "1", float("nan"), True])
+def test_rejects_invalid_ttl(ttl_seconds):
+    with pytest.raises(ValueError, match="ttl_seconds"):
+        Cache(1, ttl_seconds=ttl_seconds)
+
+
+def test_rejects_non_callable_clock():
+    with pytest.raises(ValueError, match="clock"):
+        Cache(1, clock=5)
+
+
+def test_accepts_fractional_ttl(clock):
+    cache = Cache(1, ttl_seconds=0.5, clock=clock)
+    cache.set("a", 1)
+    clock.advance(0.4)
+
+    assert cache.get("a") == 1
+
+
+# get and set
+
+
+def test_get_returns_stored_value_and_counts_hit():
+    cache = Cache(2)
+    cache.set("a", 1)
+
+    assert cache.get("a") == 1
+    assert cache.stats().hits == 1
+    assert cache.stats().misses == 0
+
+
+def test_get_missing_key_returns_default_and_counts_miss():
+    cache = Cache(2)
+
+    assert cache.get("a") is None
+    assert cache.get("a", "fallback") == "fallback"
+    assert cache.stats().misses == 2
+    assert cache.stats().hits == 0
+
+
+def test_set_replaces_previous_value():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("a", 2)
+
+    assert cache.get("a") == 2
+    assert len(cache) == 1
+
+
+def test_stored_none_is_a_hit():
+    cache = Cache(1)
+    cache.set("a", None)
+
+    assert cache.get("a", "fallback") is None
+    assert cache.stats().hits == 1
+
+
+# Size limit and least-recently-used eviction
+
+
+def test_adding_to_full_cache_evicts_least_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("c", 3)
+
+    assert "a" not in cache
+    assert "b" in cache and "c" in cache
+    assert cache.stats().evictions == 1
+
+
+def test_get_makes_entry_most_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.get("a")
+    cache.set("c", 3)
+
+    assert "a" in cache
+    assert "b" not in cache
+
+
+def test_replacing_existing_key_in_full_cache_does_not_evict():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("a", 10)
+
+    assert len(cache) == 2
+    assert cache.stats().evictions == 0
+
+
+def test_replacing_key_makes_it_most_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("a", 10)
+    cache.set("c", 3)
+
+    assert "a" in cache
+    assert "b" not in cache
+
+
+def test_contains_and_len_do_not_change_recency_or_stats():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+
+    assert "a" in cache
+    assert "missing" not in cache
+    assert len(cache) == 2
+    cache.set("c", 3)
+
+    assert "a" not in cache
+    assert cache.stats().hits == 0
+    assert cache.stats().misses == 0
+
+
+# Expiry
+
+
+def test_entry_expires_exactly_when_ttl_has_passed(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+
+    clock.advance(9.5)
+    assert cache.get("a") == 1
+
+    clock.advance(0.5)
+    assert cache.get("a") is None
+    assert cache.stats().hits == 1
+    assert cache.stats().misses == 1
+
+
+def test_expired_entries_are_absent_from_len_and_contains(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(5)
+    cache.set("b", 2)
+    clock.advance(5)
+
+    assert "a" not in cache
+    assert "b" in cache
+    assert len(cache) == 1
+
+
+def test_get_does_not_restart_expiry(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(5)
+    cache.get("a")
+    clock.advance(5)
+
+    assert "a" not in cache
+
+
+def test_set_restarts_expiry(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(8)
+    cache.set("a", 2)
+    clock.advance(8)
+
+    assert cache.get("a") == 2
+
+
+def test_entries_never_expire_without_ttl(clock):
+    cache = Cache(1, clock=clock)
+    cache.set("a", 1)
+    clock.advance(1e9)
+
+    assert cache.get("a") == 1
+
+
+def test_full_cache_removes_expired_entries_before_evicting(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("old", 1)
+    clock.advance(5)
+    cache.set("recent", 2)
+    cache.get("old")
+    clock.advance(5)
+    cache.set("new", 3)
+
+    assert "recent" in cache
+    assert "new" in cache
+    assert cache.stats().evictions == 0
+
+
+def test_resetting_expired_key_in_full_cache_does_not_evict(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    clock.advance(10)
+    cache.set("a", 3)
+
+    assert cache.get("a") == 3
+    assert cache.stats().evictions == 0
+
+
+# delete and clear
+
+
+def test_delete_removes_live_entry():
+    cache = Cache(2)
+    cache.set("a", 1)
+
+    assert cache.delete("a") is True
+    assert "a" not in cache
+    assert cache.stats().evictions == 0
+
+
+def test_delete_missing_key_returns_false():
+    cache = Cache(2)
+
+    assert cache.delete("a") is False
+
+
+def test_delete_expired_key_returns_false(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(10)
+
+    assert cache.delete("a") is False
+
+
+def test_clear_removes_entries_but_keeps_stats():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.get("a")
+    cache.get("missing")
+    cache.clear()
+
+    assert len(cache) == 0
+    assert "a" not in cache
+    assert (cache.stats().hits, cache.stats().misses) == (1, 1)
+
+
+# memoize
+
+
+def test_memoize_calls_function_once_per_arguments():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def square(x):
+        calls.append(x)
+        return x * x
+
+    assert square(3) == 9
+    assert square(3) == 9
+    assert square(4) == 16
+    assert calls == [3, 4]
+    assert (cache.stats().hits, cache.stats().misses) == (1, 2)
+
+
+def test_memoize_caches_none_results():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def record(x):
+        calls.append(x)
+
+    record(1)
+    record(1)
+
+    assert calls == [1]
+
+
+def test_memoize_keys_on_keyword_arguments():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def describe(a, b=0):
+        calls.append((a, b))
+        return a + b
+
+    assert describe(1, b=2) == 3
+    assert describe(1, b=2) == 3
+    assert describe(1, b=5) == 6
+    assert calls == [(1, 2), (1, 5)]
+
+
+def test_memoized_functions_sharing_a_cache_do_not_collide():
+    cache = Cache(10)
+
+    @memoize(cache)
+    def double(x):
+        return x * 2
+
+    @memoize(cache)
+    def triple(x):
+        return x * 3
+
+    assert double(5) == 10
+    assert triple(5) == 15
+    assert double(5) == 10
```

### Implementation 2

```diff
diff -ruN before/cache/store.py after/cache/store.py
--- before/cache/store.py
+++ after/cache/store.py
@@ -0,0 +1,163 @@
+"""In-memory cache with a size limit, optional expiry, hit statistics and memoization."""
+
+from __future__ import annotations
+
+import functools
+import numbers
+import time
+from collections import OrderedDict
+from collections.abc import Callable, Hashable
+from dataclasses import dataclass
+from typing import Any, TypeVar
+
+__all__ = ["Cache", "CacheStats", "memoize"]
+
+_MISSING = object()
+
+F = TypeVar("F", bound=Callable[..., Any])
+
+
+@dataclass(frozen=True)
+class CacheStats:
+    """A snapshot of a cache's counters at the moment ``Cache.stats()`` was called."""
+
+    hits: int
+    misses: int
+    evictions: int
+
+
+class Cache:
+    """A least-recently-used cache whose entries can optionally expire.
+
+    Entries are kept in recency order: the first entry is the least recently used.
+    Expired entries behave as if they were absent and are dropped lazily, whenever
+    an operation comes across them.
+    """
+
+    def __init__(
+        self,
+        max_size: int,
+        ttl_seconds: float | None = None,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size <= 0:
+            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
+        if ttl_seconds is not None and not _is_positive_number(ttl_seconds):
+            raise ValueError(
+                f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}"
+            )
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+
+        self._max_size = max_size
+        self._ttl_seconds = ttl_seconds
+        self._clock = clock
+        # key -> (value, time the entry was last set)
+        self._entries: OrderedDict[Hashable, tuple[Any, float]] = OrderedDict()
+        self._hits = 0
+        self._misses = 0
+        self._evictions = 0
+
+    def set(self, key: Hashable, value: Any) -> None:
+        """Store ``value`` under ``key`` as the most recently used entry, restarting its expiry."""
+        now = self._clock()
+        if key not in self._entries:
+            self._make_room(now)
+        self._entries[key] = (value, now)
+        self._entries.move_to_end(key)
+
+    def get(self, key: Hashable, default: Any = None) -> Any:
+        """Return the live value for ``key`` (a hit), or ``default`` if there is none (a miss)."""
+        entry = self._live_entry(key)
+        if entry is None:
+            self._misses += 1
+            return default
+        self._entries.move_to_end(key)
+        self._hits += 1
+        return entry[0]
+
+    def delete(self, key: Hashable) -> bool:
+        """Remove ``key``. Return ``True`` only if it had a live entry."""
+        entry = self._entries.pop(key, None)
+        return entry is not None and not self._is_expired(entry, self._clock())
+
+    def clear(self) -> None:
+        """Remove every entry. The statistics are kept."""
+        self._entries.clear()
+
+    def stats(self) -> CacheStats:
+        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)
+
+    def __len__(self) -> int:
+        self._remove_expired(self._clock())
+        return len(self._entries)
+
+    def __contains__(self, key: Hashable) -> bool:
+        return self._live_entry(key) is not None
+
+    def _is_expired(self, entry: tuple[Any, float], now: float) -> bool:
+        return self._ttl_seconds is not None and now - entry[1] >= self._ttl_seconds
+
+    def _live_entry(self, key: Hashable) -> tuple[Any, float] | None:
+        """Return the entry for ``key`` if it is live, dropping it if it has expired.
+
+        Does not change recency order or statistics.
+        """
+        entry = self._entries.get(key)
+        if entry is None:
+            return None
+        if self._is_expired(entry, self._clock()):
+            del self._entries[key]
+            return None
+        return entry
+
+    def _remove_expired(self, now: float) -> None:
+        if self._ttl_seconds is None:
+            return
+        expired_keys = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
+        for key in expired_keys:
+            del self._entries[key]
+
+    def _make_room(self, now: float) -> None:
+        """Free a slot for a new key: drop expired entries first, then evict the LRU entry."""
+        if len(self._entries) < self._max_size:
+            return
+        self._remove_expired(now)
+        if len(self._entries) >= self._max_size:
+            self._entries.popitem(last=False)
+            self._evictions += 1
+
+
+def memoize(cache: Cache) -> Callable[[F], F]:
+    """Cache a function's results in ``cache``, keyed by its positional and keyword arguments.
+
+    Lookups go through ``cache.get``, so they count as hits and misses. ``f(1)`` and
+    ``f(x=1)`` are cached separately, as with ``functools.lru_cache``.
+    """
+
+    def decorator(func: F) -> F:
+        # A private token per decorated function keeps its keys apart from those of other
+        # functions, and from any keys set directly on the shared cache.
+        namespace = object()
+
+        @functools.wraps(func)
+        def wrapper(*args: Any, **kwargs: Any) -> Any:
+            key = (namespace, args, frozenset(kwargs.items()))
+            result = cache.get(key, _MISSING)
+            if result is _MISSING:
+                result = func(*args, **kwargs)
+                cache.set(key, result)
+            return result
+
+        return wrapper  # type: ignore[return-value]
+
+    return decorator
+
+
+def _is_positive_number(value: object) -> bool:
+    # bool is a subclass of int but is not a meaningful duration; `value > 0` is False for NaN.
+    return (
+        not isinstance(value, bool)
+        and isinstance(value, numbers.Real)
+        and value > 0
+    )
diff -ruN before/tests/test_store.py after/tests/test_store.py
--- before/tests/test_store.py
+++ after/tests/test_store.py
@@ -0,0 +1,305 @@
+import math
+
+import pytest
+
+from cache.store import Cache, memoize
+
+
+class FakeClock:
+    def __init__(self, now=0.0):
+        self.now = now
+
+    def __call__(self):
+        return self.now
+
+    def advance(self, seconds):
+        self.now += seconds
+
+
+@pytest.fixture
+def clock():
+    return FakeClock()
+
+
+# --- construction -----------------------------------------------------------------------
+
+
+@pytest.mark.parametrize("max_size", [0, -1, 1.5, 2.0, True, "3", None])
+def test_invalid_max_size_raises(max_size):
+    with pytest.raises(ValueError):
+        Cache(max_size)
+
+
+@pytest.mark.parametrize("ttl", [0, -1, -0.5, math.nan, True, "1"])
+def test_invalid_ttl_raises(ttl):
+    with pytest.raises(ValueError):
+        Cache(1, ttl_seconds=ttl)
+
+
+def test_non_callable_clock_raises():
+    with pytest.raises(ValueError):
+        Cache(1, clock=5)
+
+
+@pytest.mark.parametrize("ttl", [None, 1, 0.25])
+def test_valid_ttl_accepted(ttl):
+    Cache(1, ttl_seconds=ttl)
+
+
+def test_default_clock_works():
+    cache = Cache(2, ttl_seconds=60)
+    cache.set("a", 1)
+    assert cache.get("a") == 1
+
+
+# --- get / set / delete / clear ----------------------------------------------------------
+
+
+def test_get_returns_value_or_default():
+    cache = Cache(2)
+    cache.set("a", 1)
+    assert cache.get("a") == 1
+    assert cache.get("missing") is None
+    assert cache.get("missing", "dflt") == "dflt"
+
+
+def test_set_replaces_value():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("a", 2)
+    assert cache.get("a") == 2
+    assert len(cache) == 1
+
+
+def test_evicts_least_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("c", 3)
+    assert "a" not in cache
+    assert "b" in cache and "c" in cache
+    assert cache.stats().evictions == 1
+
+
+def test_get_makes_entry_most_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.get("a")
+    cache.set("c", 3)
+    assert "a" in cache
+    assert "b" not in cache
+
+
+def test_set_of_existing_key_makes_it_most_recently_used_without_evicting():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("a", 10)
+    assert cache.stats().evictions == 0
+    cache.set("c", 3)
+    assert cache.get("a") == 10
+    assert "b" not in cache
+
+
+def test_len_and_contains_do_not_affect_stats_or_recency():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    assert "a" in cache
+    assert "zzz" not in cache
+    assert len(cache) == 2
+    cache.set("c", 3)
+    assert "a" not in cache  # still the least recently used despite the `in` check
+    stats = cache.stats()
+    assert (stats.hits, stats.misses) == (0, 0)
+
+
+def test_delete():
+    cache = Cache(2)
+    cache.set("a", 1)
+    assert cache.delete("a") is True
+    assert cache.delete("a") is False
+    assert cache.delete("never") is False
+    assert "a" not in cache
+    assert cache.stats().evictions == 0
+
+
+def test_clear_keeps_stats():
+    cache = Cache(3)
+    cache.set("a", 1)
+    cache.get("a")
+    cache.get("x")
+    cache.clear()
+    assert len(cache) == 0
+    assert "a" not in cache
+    stats = cache.stats()
+    assert (stats.hits, stats.misses) == (1, 1)
+
+
+def test_stats_counts_hits_and_misses_as_ints():
+    cache = Cache(2)
+    cache.set("a", None)
+    assert cache.get("a", "dflt") is None  # stored None is a hit, not the default
+    cache.get("b")
+    cache.get("b")
+    stats = cache.stats()
+    assert (stats.hits, stats.misses, stats.evictions) == (1, 2, 0)
+    assert all(type(n) is int for n in (stats.hits, stats.misses, stats.evictions))
+
+
+# --- expiry ------------------------------------------------------------------------------
+
+
+def test_entry_expires_once_ttl_has_passed(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(9.999)
+    assert "a" in cache
+    clock.advance(0.001)  # exactly ttl -> expired
+    assert "a" not in cache
+    assert len(cache) == 0
+    assert cache.get("a", "gone") == "gone"
+    assert cache.stats().misses == 1
+
+
+def test_set_restarts_expiry_but_get_does_not(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(6)
+    cache.set("a", 2)
+    clock.advance(6)
+    assert cache.get("a") == 2
+    clock.advance(4)
+    assert cache.get("a") is None
+
+
+def test_delete_of_expired_entry_returns_false(clock):
+    cache = Cache(2, ttl_seconds=1, clock=clock)
+    cache.set("a", 1)
+    clock.advance(1)
+    assert cache.delete("a") is False
+
+
+def test_expired_entries_are_removed_before_evicting(clock):
+    cache = Cache(3, ttl_seconds=10, clock=clock)
+    cache.set("old", 1)
+    clock.advance(5)
+    cache.set("b", 2)
+    cache.set("c", 3)
+    clock.advance(5)  # "old" has expired; "b" and "c" are live
+    cache.set("d", 4)
+    assert cache.stats().evictions == 0
+    assert all(k in cache for k in ("b", "c", "d"))
+
+
+def test_evicts_lru_when_nothing_has_expired(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("c", 3)
+    assert "a" not in cache
+    assert cache.stats().evictions == 1
+
+
+def test_setting_an_expired_key_does_not_evict_others(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(5)
+    cache.set("b", 2)
+    clock.advance(5)  # "a" expired
+    cache.set("a", 3)
+    assert cache.stats().evictions == 0
+    assert cache.get("a") == 3 and cache.get("b") == 2
+
+
+# --- memoize -----------------------------------------------------------------------------
+
+
+def test_memoize_caches_results_and_counts_hits_and_misses():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def square(x):
+        calls.append(x)
+        return x * x
+
+    assert square(3) == 9
+    assert square(3) == 9
+    assert square(4) == 16
+    assert calls == [3, 4]
+    stats = cache.stats()
+    assert (stats.hits, stats.misses) == (1, 2)
+
+
+def test_memoize_caches_none():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def nothing(x):
+        calls.append(x)
+        return None
+
+    assert nothing(1) is None
+    assert nothing(1) is None
+    assert calls == [1]
+    assert cache.stats().hits == 1
+
+
+def test_memoize_uses_keyword_arguments():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def f(a, b=0, *, c=0):
+        calls.append((a, b, c))
+        return a + b + c
+
+    assert f(1, b=2, c=3) == 6
+    assert f(1, c=3, b=2) == 6  # keyword order does not matter
+    assert f(1, b=2, c=4) == 7
+    assert len(calls) == 2
+
+
+def test_functions_sharing_a_cache_do_not_collide():
+    cache = Cache(10)
+
+    @memoize(cache)
+    def double(x):
+        return x * 2
+
+    @memoize(cache)
+    def triple(x):
+        return x * 3
+
+    cache.set((5,), "direct")
+    assert double(5) == 10
+    assert triple(5) == 15
+    assert double(5) == 10
+    assert cache.get((5,)) == "direct"
+
+
+def test_memoize_preserves_function_metadata():
+    @memoize(Cache(1))
+    def documented():
+        """Docstring."""
+
+    assert documented.__name__ == "documented"
+    assert documented.__doc__ == "Docstring."
+
+
+def test_memoize_respects_expiry(clock):
+    cache = Cache(10, ttl_seconds=5, clock=clock)
+    calls = []
+
+    @memoize(cache)
+    def f(x):
+        calls.append(x)
+        return x
+
+    f(1)
+    clock.advance(5)
+    f(1)
+    assert calls == [1, 1]
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/cache/store.py after/cache/store.py
--- before/cache/store.py
+++ after/cache/store.py
@@ -0,0 +1,162 @@
+"""In-memory LRU cache with optional expiry, hit statistics and a memoizing decorator."""
+
+import functools
+import numbers
+import time
+from collections import OrderedDict
+from collections.abc import Callable, Hashable
+from dataclasses import dataclass
+from typing import Any, NamedTuple, Optional
+
+__all__ = ["Cache", "CacheStats", "memoize"]
+
+# Lets memoize tell "not cached" apart from a cached None.
+_MISSING = object()
+
+
+@dataclass(frozen=True)
+class CacheStats:
+    """Counters of a cache, captured when ``Cache.stats()`` was called."""
+
+    hits: int
+    misses: int
+    evictions: int
+
+
+class _Entry(NamedTuple):
+    value: Any
+    set_at: float
+
+
+class Cache:
+    """Size-limited cache that evicts the least recently used entry.
+
+    With ``ttl_seconds`` set, an entry expires once that many seconds have
+    passed since it was last set; expired entries behave as if absent.
+    """
+
+    def __init__(
+        self,
+        max_size: int,
+        ttl_seconds: Optional[float] = None,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if (
+            isinstance(max_size, bool)
+            or not isinstance(max_size, numbers.Integral)
+            or max_size <= 0
+        ):
+            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
+        # `not ttl_seconds > 0` (rather than `<= 0`) also rejects NaN.
+        if ttl_seconds is not None and (
+            isinstance(ttl_seconds, bool)
+            or not isinstance(ttl_seconds, numbers.Real)
+            or not ttl_seconds > 0
+        ):
+            raise ValueError(
+                f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}"
+            )
+        if not callable(clock):
+            raise ValueError(f"clock must be a callable, got {clock!r}")
+
+        self._max_size = max_size
+        self._ttl = ttl_seconds
+        self._clock = clock
+        # Ordered from least to most recently used.
+        self._entries: "OrderedDict[Hashable, _Entry]" = OrderedDict()
+        self._hits = 0
+        self._misses = 0
+        self._evictions = 0
+
+    def set(self, key: Hashable, value: Any) -> None:
+        now = self._clock()
+        if key in self._entries:
+            self._entries.move_to_end(key)
+        elif len(self._entries) >= self._max_size:
+            self._make_room(now)
+        self._entries[key] = _Entry(value, now)
+
+    def get(self, key: Hashable, default: Any = None) -> Any:
+        entry = self._live_entry(key, self._clock())
+        if entry is None:
+            self._misses += 1
+            return default
+        self._entries.move_to_end(key)
+        self._hits += 1
+        return entry.value
+
+    def delete(self, key: Hashable) -> bool:
+        if self._live_entry(key, self._clock()) is None:
+            return False
+        del self._entries[key]
+        return True
+
+    def clear(self) -> None:
+        self._entries.clear()
+
+    def stats(self) -> CacheStats:
+        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)
+
+    def __len__(self) -> int:
+        self._remove_expired(self._clock())
+        return len(self._entries)
+
+    def __contains__(self, key: Hashable) -> bool:
+        return self._live_entry(key, self._clock()) is not None
+
+    def _live_entry(self, key: Hashable, now: float) -> Optional[_Entry]:
+        """Return the entry for ``key`` if it is live, discarding it if expired."""
+        entry = self._entries.get(key)
+        if entry is None:
+            return None
+        if self._is_expired(entry, now):
+            del self._entries[key]
+            return None
+        return entry
+
+    def _is_expired(self, entry: _Entry, now: float) -> bool:
+        return self._ttl is not None and now - entry.set_at >= self._ttl
+
+    def _remove_expired(self, now: float) -> None:
+        # Recency order is not expiry order (get refreshes recency, not expiry),
+        # so every entry has to be checked.
+        if self._ttl is None:
+            return
+        expired = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
+        for key in expired:
+            del self._entries[key]
+
+    def _make_room(self, now: float) -> None:
+        """Free one slot: drop expired entries, else evict the least recently used one."""
+        self._remove_expired(now)
+        if len(self._entries) >= self._max_size:
+            self._entries.popitem(last=False)
+            self._evictions += 1
+
+
+def memoize(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
+    """Cache a function's results in ``cache``, keyed by its arguments.
+
+    Use as ``@memoize(cache)``. Arguments must be hashable. Several functions
+    may share one cache; their entries never collide with each other or with
+    keys set directly on the cache.
+    """
+    if not isinstance(cache, Cache):
+        raise TypeError(f"memoize() expects a Cache, got {cache!r}; use @memoize(cache)")
+
+    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
+        # A private object no caller can construct, so keys are unique to this function.
+        namespace = object()
+
+        @functools.wraps(func)
+        def wrapper(*args: Any, **kwargs: Any) -> Any:
+            key = (namespace, args, frozenset(kwargs.items()))
+            result = cache.get(key, _MISSING)
+            if result is _MISSING:
+                result = func(*args, **kwargs)
+                cache.set(key, result)
+            return result
+
+        return wrapper
+
+    return decorator
diff -ruN before/tests/test_store.py after/tests/test_store.py
--- before/tests/test_store.py
+++ after/tests/test_store.py
@@ -0,0 +1,371 @@
+import math
+
+import pytest
+
+from cache.store import Cache, memoize
+
+
+class FakeClock:
+    def __init__(self, now=0.0):
+        self.now = now
+
+    def __call__(self):
+        return self.now
+
+    def advance(self, seconds):
+        self.now += seconds
+
+
+def stats_tuple(cache):
+    s = cache.stats()
+    return (s.hits, s.misses, s.evictions)
+
+
+# --- construction -----------------------------------------------------------
+
+
+@pytest.mark.parametrize("max_size", [0, -1, 1.5, 2.0, "3", None, True])
+def test_invalid_max_size(max_size):
+    with pytest.raises(ValueError):
+        Cache(max_size)
+
+
+@pytest.mark.parametrize("ttl", [0, -1, -0.5, "1", True, math.nan, [1]])
+def test_invalid_ttl(ttl):
+    with pytest.raises(ValueError):
+        Cache(1, ttl_seconds=ttl)
+
+
+def test_invalid_clock():
+    with pytest.raises(ValueError):
+        Cache(1, clock=42)
+
+
+@pytest.mark.parametrize("ttl", [None, 1, 0.25, math.inf])
+def test_valid_arguments(ttl):
+    Cache(1, ttl_seconds=ttl, clock=FakeClock())
+
+
+def test_works_with_default_clock():
+    cache = Cache(2, ttl_seconds=60)
+    cache.set("a", 1)
+    assert cache.get("a") == 1
+
+
+# --- basic operations -------------------------------------------------------
+
+
+def test_get_returns_value_or_default():
+    cache = Cache(2)
+    cache.set("a", 1)
+    assert cache.get("a") == 1
+    assert cache.get("missing") is None
+    assert cache.get("missing", "dflt") == "dflt"
+
+
+def test_set_replaces_value():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("a", 2)
+    assert cache.get("a") == 2
+    assert len(cache) == 1
+
+
+def test_stores_none_values():
+    cache = Cache(2)
+    cache.set("a", None)
+    assert "a" in cache
+    assert cache.get("a", "dflt") is None
+    assert stats_tuple(cache) == (1, 0, 0)
+
+
+def test_delete():
+    cache = Cache(2)
+    cache.set("a", 1)
+    assert cache.delete("a") is True
+    assert cache.delete("a") is False
+    assert "a" not in cache
+    assert cache.delete("never") is False
+
+
+def test_clear_keeps_stats():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.get("a")
+    cache.get("b")
+    cache.clear()
+    assert len(cache) == 0
+    assert "a" not in cache
+    assert stats_tuple(cache) == (1, 1, 0)
+
+
+# --- LRU eviction -----------------------------------------------------------
+
+
+def test_evicts_least_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("c", 3)
+    assert "a" not in cache
+    assert cache.get("b") == 2 and cache.get("c") == 3
+    assert cache.stats().evictions == 1
+
+
+def test_get_refreshes_recency():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.get("a")
+    cache.set("c", 3)
+    assert "a" in cache and "b" not in cache
+
+
+def test_set_existing_refreshes_recency_without_eviction():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("a", 10)
+    assert cache.stats().evictions == 0
+    cache.set("c", 3)
+    assert "a" in cache and "b" not in cache
+
+
+def test_missed_get_does_not_refresh_anything():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.get("zzz")
+    cache.set("c", 3)
+    assert "a" not in cache
+
+
+def test_len_and_contains_do_not_touch_recency_or_stats():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    assert "a" in cache
+    assert "zzz" not in cache
+    assert len(cache) == 2
+    cache.set("c", 3)
+    assert "a" not in cache  # "a" stayed least recently used
+    assert stats_tuple(cache) == (0, 0, 1)
+
+
+def test_delete_and_clear_are_not_evictions():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.delete("a")
+    cache.set("b", 2)
+    cache.clear()
+    assert cache.stats().evictions == 0
+
+
+# --- expiry -----------------------------------------------------------------
+
+
+def test_entry_expires_exactly_at_ttl():
+    clock = FakeClock()
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(9.999)
+    assert cache.get("a") == 1
+    clock.advance(0.001)
+    assert cache.get("a", "gone") == "gone"
+    assert stats_tuple(cache) == (1, 1, 0)
+
+
+def test_expired_entry_behaves_as_absent():
+    clock = FakeClock()
+    cache = Cache(2, ttl_seconds=5, clock=clock)
+    cache.set("a", 1)
+    clock.advance(5)
+    assert "a" not in cache
+    assert len(cache) == 0
+    assert cache.delete("a") is False
+    assert stats_tuple(cache) == (0, 0, 0)
+
+
+def test_set_restarts_expiry_but_get_does_not():
+    clock = FakeClock()
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    clock.advance(6)
+    cache.set("a", 10)
+    cache.get("b")
+    clock.advance(6)
+    assert cache.get("a") == 10
+    assert "b" not in cache
+
+
+def test_set_on_full_cache_removes_expired_before_evicting():
+    clock = FakeClock()
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("old", 1)
+    clock.advance(5)
+    cache.set("fresh", 2)
+    cache.get("old")  # "old" is now most recently used, but expires first
+    clock.advance(5)
+    cache.set("new", 3)
+    assert "fresh" in cache and "new" in cache
+    assert cache.stats().evictions == 0
+
+
+def test_set_on_full_cache_evicts_when_nothing_expired():
+    clock = FakeClock()
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    clock.advance(9)
+    cache.set("c", 3)
+    assert "a" not in cache and "b" in cache and "c" in cache
+    assert cache.stats().evictions == 1
+
+
+def test_resetting_expired_key_in_full_cache_does_not_evict():
+    clock = FakeClock()
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(10)
+    cache.set("b", 2)
+    cache.set("a", 3)
+    assert cache.get("a") == 3 and cache.get("b") == 2
+    assert cache.stats().evictions == 0
+
+
+def test_stats_are_integers_and_snapshots():
+    cache = Cache(1)
+    cache.set("a", 1)
+    cache.get("a")
+    cache.get("b")
+    cache.set("b", 2)
+    snapshot = cache.stats()
+    assert (snapshot.hits, snapshot.misses, snapshot.evictions) == (1, 1, 1)
+    assert all(type(v) is int for v in (snapshot.hits, snapshot.misses, snapshot.evictions))
+    cache.get("b")
+    assert snapshot.hits == 1
+
+
+# --- memoize ----------------------------------------------------------------
+
+
+def test_memoize_caches_and_counts():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def square(x):
+        calls.append(x)
+        return x * x
+
+    assert square(3) == 9
+    assert square(3) == 9
+    assert calls == [3]
+    assert stats_tuple(cache) == (1, 1, 0)
+
+
+def test_memoize_caches_none():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def nothing(x):
+        calls.append(x)
+        return None
+
+    assert nothing(1) is None
+    assert nothing(1) is None
+    assert calls == [1]
+    assert stats_tuple(cache) == (1, 1, 0)
+
+
+def test_memoize_shared_cache_does_not_collide():
+    cache = Cache(10)
+
+    @memoize(cache)
+    def double(x):
+        return x * 2
+
+    @memoize(cache)
+    def triple(x):
+        return x * 3
+
+    cache.set((5,), "user value")
+    assert double(5) == 10
+    assert triple(5) == 15
+    assert double(5) == 10
+    assert cache.get((5,)) == "user value"
+
+
+def test_memoize_keyword_arguments():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def f(a, b=0, *, c=0):
+        calls.append((a, b, c))
+        return a + 10 * b + 100 * c
+
+    assert f(1, b=2, c=3) == 321
+    assert f(1, c=3, b=2) == 321  # keyword order does not matter
+    assert f(1, 2, c=3) == 321  # different call shape, separate entry
+    assert f(1) == 1
+    assert calls == [(1, 2, 3), (1, 2, 3), (1, 0, 0)]
+
+
+def test_memoize_does_not_cache_exceptions():
+    cache = Cache(10)
+    attempts = []
+
+    @memoize(cache)
+    def flaky(x):
+        attempts.append(x)
+        if len(attempts) == 1:
+            raise RuntimeError("boom")
+        return x
+
+    with pytest.raises(RuntimeError):
+        flaky(1)
+    assert flaky(1) == 1
+    assert flaky(1) == 1
+    assert attempts == [1, 1]
+
+
+def test_memoize_respects_eviction_and_expiry():
+    clock = FakeClock()
+    cache = Cache(1, ttl_seconds=10, clock=clock)
+    calls = []
+
+    @memoize(cache)
+    def ident(x):
+        calls.append(x)
+        return x
+
+    ident(1)
+    ident(2)  # evicts 1
+    ident(1)
+    clock.advance(10)
+    ident(1)  # expired
+    assert calls == [1, 2, 1, 1]
+
+
+def test_memoize_preserves_metadata_and_recursion():
+    cache = Cache(100)
+
+    @memoize(cache)
+    def fib(n):
+        """Fibonacci."""
+        return n if n < 2 else fib(n - 1) + fib(n - 2)
+
+    assert fib(60) == 1548008755920
+    assert fib.__name__ == "fib"
+    assert fib.__doc__ == "Fibonacci."
+
+
+def test_memoize_without_cache_argument_fails_clearly():
+    with pytest.raises(TypeError):
+
+        @memoize
+        def f(x):
+            return x
```

### Implementation 2

```diff
diff -ruN before/cache/store.py after/cache/store.py
--- before/cache/store.py
+++ after/cache/store.py
@@ -0,0 +1,157 @@
+"""In-memory LRU cache with optional expiry, hit statistics and memoization."""
+
+import functools
+import time
+from collections import OrderedDict
+from collections.abc import Callable, Hashable
+from dataclasses import dataclass
+from numbers import Integral, Real
+from typing import Any
+
+
+@dataclass(frozen=True)
+class CacheStats:
+    hits: int
+    misses: int
+    evictions: int
+
+
+@dataclass(frozen=True)
+class _Entry:
+    value: Any
+    set_at: float
+
+
+class Cache:
+    """A least-recently-used cache whose entries can expire.
+
+    An entry expires once ``ttl_seconds`` or more have passed since it was last set.
+    Expired entries behave as if they were absent.
+    """
+
+    def __init__(
+        self,
+        max_size: int,
+        ttl_seconds: float | None = None,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not _is_positive_number(max_size, Integral):
+            raise ValueError(
+                f"max_size must be an integer greater than 0, got {max_size!r}"
+            )
+        if ttl_seconds is not None and not _is_positive_number(ttl_seconds, Real):
+            raise ValueError(
+                "ttl_seconds must be None or a number greater than 0, "
+                f"got {ttl_seconds!r}"
+            )
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+        self._max_size = max_size
+        self._ttl_seconds = ttl_seconds
+        self._clock = clock
+        self._entries: OrderedDict[Hashable, _Entry] = OrderedDict()  # LRU first
+        self._hits = 0
+        self._misses = 0
+        self._evictions = 0
+
+    def set(self, key: Hashable, value: Any) -> None:
+        """Store ``value``, restart its expiry and make it the most recently used.
+
+        Adding a new key to a full cache first removes expired entries, then evicts
+        the least recently used entry if there is still no room.
+        """
+        now = self._clock()
+        if key not in self._entries and self._is_full():
+            self._make_room(now)
+        self._entries[key] = _Entry(value, set_at=now)
+        self._entries.move_to_end(key)
+
+    def get(self, key: Hashable, default: Any = None) -> Any:
+        """Return the live value for ``key`` and make it the most recently used.
+
+        Returns ``default`` if the key is absent or expired.
+        """
+        if key not in self:
+            self._misses += 1
+            return default
+        self._hits += 1
+        self._entries.move_to_end(key)
+        return self._entries[key].value
+
+    def delete(self, key: Hashable) -> bool:
+        """Remove ``key`` and return whether a live entry was removed."""
+        was_live = key in self
+        self._entries.pop(key, None)
+        return was_live
+
+    def clear(self) -> None:
+        """Remove all entries. The statistics are kept."""
+        self._entries.clear()
+
+    def stats(self) -> CacheStats:
+        return CacheStats(
+            hits=self._hits, misses=self._misses, evictions=self._evictions
+        )
+
+    def __len__(self) -> int:
+        now = self._clock()
+        return sum(
+            1 for entry in self._entries.values() if not self._is_expired(entry, now)
+        )
+
+    def __contains__(self, key: Hashable) -> bool:
+        entry = self._entries.get(key)
+        return entry is not None and not self._is_expired(entry, self._clock())
+
+    def _is_full(self) -> bool:
+        return len(self._entries) >= self._max_size
+
+    def _make_room(self, now: float) -> None:
+        self._remove_expired(now)
+        if self._is_full():
+            self._entries.popitem(last=False)
+            self._evictions += 1
+
+    def _remove_expired(self, now: float) -> None:
+        expired_keys = [
+            key for key, entry in self._entries.items() if self._is_expired(entry, now)
+        ]
+        for key in expired_keys:
+            del self._entries[key]
+
+    def _is_expired(self, entry: _Entry, now: float) -> bool:
+        if self._ttl_seconds is None:
+            return False
+        return now - entry.set_at >= self._ttl_seconds
+
+
+_MISSING = object()
+
+
+def memoize(
+    cache: Cache,
+) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
+    """Cache a function's results in ``cache``, keyed by the function and its arguments.
+
+    Including the function in the key lets several functions share one cache.
+    """
+
+    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
+        @functools.wraps(func)
+        def wrapper(*args: Any, **kwargs: Any) -> Any:
+            key = (func, args, frozenset(kwargs.items()))
+            result = cache.get(key, _MISSING)
+            if result is _MISSING:
+                result = func(*args, **kwargs)
+                cache.set(key, result)
+            return result
+
+        return wrapper
+
+    return decorator
+
+
+def _is_positive_number(value: object, number_type: type) -> bool:
+    # bool is a subclass of int, but True is not a meaningful size or duration.
+    is_number = isinstance(value, number_type) and not isinstance(value, bool)
+    return is_number and value > 0
diff -ruN before/tests/test_store.py after/tests/test_store.py
--- before/tests/test_store.py
+++ after/tests/test_store.py
@@ -0,0 +1,300 @@
+import pytest
+
+from cache.store import Cache, CacheStats, memoize
+
+TTL = 10
+
+
+class FakeClock:
+    """A controllable stand-in for time.monotonic."""
+
+    def __init__(self):
+        self.now = 0.0
+
+    def __call__(self):
+        return self.now
+
+    def advance(self, seconds):
+        self.now += seconds
+
+
+@pytest.fixture
+def clock():
+    return FakeClock()
+
+
+@pytest.fixture
+def cache():
+    return Cache(max_size=2)
+
+
+@pytest.fixture
+def expiring_cache(clock):
+    return Cache(max_size=2, ttl_seconds=TTL, clock=clock)
+
+
+class TestConstruction:
+    @pytest.mark.parametrize("max_size", [0, -1, 1.5, "3", None, True])
+    def test_rejects_invalid_max_size(self, max_size):
+        with pytest.raises(ValueError, match="max_size"):
+            Cache(max_size)
+
+    @pytest.mark.parametrize("ttl_seconds", [0, -1, float("nan"), "10", True])
+    def test_rejects_invalid_ttl(self, ttl_seconds):
+        with pytest.raises(ValueError, match="ttl_seconds"):
+            Cache(1, ttl_seconds=ttl_seconds)
+
+    def test_rejects_non_callable_clock(self):
+        with pytest.raises(ValueError, match="clock"):
+            Cache(1, clock=0)
+
+    @pytest.mark.parametrize("ttl_seconds", [None, 1, 0.5])
+    def test_accepts_valid_ttl(self, ttl_seconds):
+        cache = Cache(1, ttl_seconds=ttl_seconds)
+        cache.set("a", 1)
+        assert cache.get("a") == 1
+
+
+class TestGetAndSet:
+    def test_get_returns_stored_value(self, cache):
+        cache.set("a", 1)
+        assert cache.get("a") == 1
+
+    def test_get_returns_default_for_missing_key(self, cache):
+        assert cache.get("missing") is None
+        assert cache.get("missing", "fallback") == "fallback"
+
+    def test_set_replaces_previous_value(self, cache):
+        cache.set("a", 1)
+        cache.set("a", 2)
+        assert cache.get("a") == 2
+        assert len(cache) == 1
+
+    def test_stores_none_as_a_value(self, cache):
+        cache.set("a", None)
+        assert cache.get("a", "fallback") is None
+
+
+class TestEviction:
+    def test_evicts_least_recently_used_entry_when_full(self, cache):
+        cache.set("a", 1)
+        cache.set("b", 2)
+        cache.set("c", 3)
+        assert "a" not in cache
+        assert "b" in cache
+        assert "c" in cache
+
+    def test_get_makes_entry_most_recently_used(self, cache):
+        cache.set("a", 1)
+        cache.set("b", 2)
+        cache.get("a")
+        cache.set("c", 3)
+        assert "a" in cache
+        assert "b" not in cache
+
+    def test_set_makes_existing_entry_most_recently_used(self, cache):
+        cache.set("a", 1)
+        cache.set("b", 2)
+        cache.set("a", 10)
+        cache.set("c", 3)
+        assert "a" in cache
+        assert "b" not in cache
+
+    def test_replacing_a_key_in_a_full_cache_evicts_nothing(self, cache):
+        cache.set("a", 1)
+        cache.set("b", 2)
+        cache.set("a", 10)
+        assert len(cache) == 2
+        assert cache.stats().evictions == 0
+
+    def test_contains_and_len_do_not_change_recency(self, cache):
+        cache.set("a", 1)
+        cache.set("b", 2)
+        assert "a" in cache
+        assert len(cache) == 2
+        cache.set("c", 3)
+        assert "a" not in cache
+
+
+class TestExpiry:
+    def test_entry_is_live_until_ttl_has_passed(self, expiring_cache, clock):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL - 0.001)
+        assert expiring_cache.get("a") == 1
+
+    def test_entry_expires_once_ttl_has_passed(self, expiring_cache, clock):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL)
+        assert expiring_cache.get("a", "fallback") == "fallback"
+
+    def test_set_restarts_expiry(self, expiring_cache, clock):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL - 1)
+        expiring_cache.set("a", 2)
+        clock.advance(TTL - 1)
+        assert expiring_cache.get("a") == 2
+
+    def test_get_does_not_restart_expiry(self, expiring_cache, clock):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL - 1)
+        expiring_cache.get("a")
+        clock.advance(1)
+        assert "a" not in expiring_cache
+
+    def test_entries_never_expire_without_ttl(self, clock):
+        cache = Cache(max_size=2, clock=clock)
+        cache.set("a", 1)
+        clock.advance(10**9)
+        assert cache.get("a") == 1
+
+    def test_expired_entry_is_neither_contained_nor_counted(
+        self, expiring_cache, clock
+    ):
+        expiring_cache.set("a", 1)
+        clock.advance(1)
+        expiring_cache.set("b", 2)
+        clock.advance(TTL - 1)
+        assert "a" not in expiring_cache
+        assert len(expiring_cache) == 1
+
+    def test_full_cache_removes_expired_entries_before_evicting(
+        self, expiring_cache, clock
+    ):
+        expiring_cache.set("expired", 1)
+        clock.advance(TTL / 2)
+        expiring_cache.set("live", 2)
+        expiring_cache.get("expired")  # "live" is now the least recently used
+        clock.advance(TTL / 2)
+        expiring_cache.set("new", 3)
+        assert "live" in expiring_cache
+        assert "new" in expiring_cache
+        assert expiring_cache.stats().evictions == 0
+
+    def test_setting_an_expired_key_in_a_full_cache_evicts_nothing(
+        self, expiring_cache, clock
+    ):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL / 2)
+        expiring_cache.set("b", 2)
+        clock.advance(TTL / 2)
+        expiring_cache.set("a", 10)
+        assert expiring_cache.get("a") == 10
+        assert "b" in expiring_cache
+        assert expiring_cache.stats().evictions == 0
+
+
+class TestDeleteAndClear:
+    def test_delete_removes_live_entry(self, cache):
+        cache.set("a", 1)
+        assert cache.delete("a") is True
+        assert "a" not in cache
+
+    def test_delete_missing_key_returns_false(self, cache):
+        assert cache.delete("missing") is False
+
+    def test_delete_expired_entry_returns_false(self, expiring_cache, clock):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL)
+        assert expiring_cache.delete("a") is False
+
+    def test_clear_removes_all_entries_but_keeps_stats(self, cache):
+        cache.set("a", 1)
+        cache.get("a")
+        cache.get("missing")
+        cache.clear()
+        assert len(cache) == 0
+        assert cache.stats() == CacheStats(hits=1, misses=1, evictions=0)
+
+
+class TestStats:
+    def test_get_counts_hits_and_misses(self, cache):
+        cache.set("a", 1)
+        cache.get("a")
+        cache.get("a")
+        cache.get("missing")
+        assert cache.stats() == CacheStats(hits=2, misses=1, evictions=0)
+
+    def test_get_of_expired_entry_counts_a_miss(self, expiring_cache, clock):
+        expiring_cache.set("a", 1)
+        clock.advance(TTL)
+        expiring_cache.get("a")
+        assert expiring_cache.stats() == CacheStats(hits=0, misses=1, evictions=0)
+
+    def test_contains_and_len_count_neither_hits_nor_misses(self, cache):
+        cache.set("a", 1)
+        assert "a" in cache
+        assert "missing" not in cache
+        assert len(cache) == 1
+        assert cache.stats() == CacheStats(hits=0, misses=0, evictions=0)
+
+    def test_evictions_count_only_entries_removed_to_make_room(
+        self, expiring_cache, clock
+    ):
+        expiring_cache.set("a", 1)
+        expiring_cache.set("b", 2)
+        expiring_cache.set("c", 3)  # evicts "a"
+        expiring_cache.delete("b")
+        clock.advance(TTL)
+        expiring_cache.set("d", 4)
+        expiring_cache.set("e", 5)  # removes expired "c"
+        assert expiring_cache.stats().evictions == 1
+
+
+class TestMemoize:
+    def test_returns_cached_result_for_same_arguments(self, cache):
+        calls = []
+
+        @memoize(cache)
+        def square(x):
+            calls.append(x)
+            return x * x
+
+        assert square(3) == 9
+        assert square(3) == 9
+        assert calls == [3]
+
+    def test_counts_hits_and_misses(self, cache):
+        @memoize(cache)
+        def square(x):
+            return x * x
+
+        square(3)
+        square(3)
+        square(4)
+        assert cache.stats() == CacheStats(hits=1, misses=2, evictions=0)
+
+    def test_caches_none_results(self, cache):
+        calls = []
+
+        @memoize(cache)
+        def find(x):
+            calls.append(x)
+
+        assert find(1) is None
+        assert find(1) is None
+        assert calls == [1]
+
+    def test_keys_by_keyword_arguments_regardless_of_order(self, cache):
+        calls = []
+
+        @memoize(cache)
+        def power(base, exponent):
+            calls.append((base, exponent))
+            return base**exponent
+
+        assert power(base=2, exponent=3) == 8
+        assert power(exponent=3, base=2) == 8
+        assert power(base=3, exponent=2) == 9
+        assert calls == [(2, 3), (3, 2)]
+
+    def test_functions_sharing_a_cache_do_not_collide(self, cache):
+        @memoize(cache)
+        def double(x):
+            return 2 * x
+
+        @memoize(cache)
+        def triple(x):
+            return 3 * x
+
+        assert double(5) == 10
+        assert triple(5) == 15
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/cache/store.py after/cache/store.py
--- before/cache/store.py
+++ after/cache/store.py
@@ -0,0 +1,193 @@
+"""In-memory cache with a size limit, optional expiry and hit statistics.
+
+When the cache is full, the least recently used entry is evicted to make room.
+Entries can optionally expire a fixed time after they were last set; an
+expired entry behaves exactly as if it were absent.
+"""
+
+from __future__ import annotations
+
+import functools
+import numbers
+import time
+from collections import OrderedDict
+from collections.abc import Callable, Hashable
+from dataclasses import dataclass
+from typing import Any, TypeVar
+
+__all__ = ["Cache", "CacheStats", "memoize"]
+
+F = TypeVar("F", bound=Callable[..., Any])
+
+# Marks "no cached value", so that a cached None is still recognised as a hit.
+_MISSING = object()
+
+
+@dataclass(frozen=True)
+class CacheStats:
+    """Counters of a cache, as they were when ``Cache.stats()`` was called."""
+
+    hits: int
+    misses: int
+    evictions: int
+
+
+class Cache:
+    """A size-limited, least-recently-used cache with optional expiry.
+
+    Args:
+        max_size: Maximum number of entries; an integer greater than 0.
+        ttl_seconds: How long an entry lives after it was last set, or None
+            for entries that never expire. Must be a number greater than 0.
+        clock: Zero-argument callable returning the current time in seconds.
+
+    Raises:
+        ValueError: If any argument is invalid.
+    """
+
+    def __init__(
+        self,
+        max_size: int,
+        ttl_seconds: float | None = None,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        _require_positive_int("max_size", max_size)
+        if ttl_seconds is not None:
+            _require_positive_number("ttl_seconds", ttl_seconds)
+        if not callable(clock):
+            raise ValueError(f"clock must be callable, got {clock!r}")
+
+        self._max_size = max_size
+        self._ttl = ttl_seconds
+        self._clock = clock
+        # key -> (value, time it was last set), ordered least to most recently used.
+        # May still hold expired entries; they are dropped lazily.
+        self._entries: OrderedDict[Hashable, tuple[Any, float]] = OrderedDict()
+        self._hits = 0
+        self._misses = 0
+        self._evictions = 0
+
+    def set(self, key: Hashable, value: Any) -> None:
+        """Store ``value`` under ``key`` as the most recently used entry.
+
+        Replaces any previous value and restarts the entry's expiry. Adding a
+        new key to a full cache first drops expired entries and, if that frees
+        no room, evicts the least recently used entry.
+        """
+        now = self._clock()
+        if key in self._entries:
+            self._entries.move_to_end(key)
+        elif len(self._entries) >= self._max_size:
+            self._make_room(now)
+        self._entries[key] = (value, now)
+
+    def get(self, key: Hashable, default: Any = None) -> Any:
+        """Return the live value for ``key``, or ``default`` if there is none.
+
+        A live entry becomes the most recently used and counts as a hit;
+        otherwise a miss is counted.
+        """
+        entry = self._entries.get(key)
+        if entry is not None:
+            value, set_at = entry
+            if not self._is_expired(set_at, self._clock()):
+                self._entries.move_to_end(key)
+                self._hits += 1
+                return value
+            del self._entries[key]
+        self._misses += 1
+        return default
+
+    def delete(self, key: Hashable) -> bool:
+        """Remove ``key``. Return True only if a live entry was removed."""
+        entry = self._entries.pop(key, None)
+        if entry is None:
+            return False
+        return not self._is_expired(entry[1], self._clock())
+
+    def clear(self) -> None:
+        """Remove all entries. Statistics are kept."""
+        self._entries.clear()
+
+    def stats(self) -> CacheStats:
+        """Return a snapshot of the hit, miss and eviction counters."""
+        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)
+
+    def __len__(self) -> int:
+        """Number of live entries. Does not affect statistics or recency."""
+        if self._ttl is None:
+            return len(self._entries)
+        now = self._clock()
+        return sum(1 for _, set_at in self._entries.values() if not self._is_expired(set_at, now))
+
+    def __contains__(self, key: object) -> bool:
+        """Whether ``key`` has a live entry. Does not affect statistics or recency."""
+        entry = self._entries.get(key)
+        return entry is not None and not self._is_expired(entry[1], self._clock())
+
+    def _is_expired(self, set_at: float, now: float) -> bool:
+        return self._ttl is not None and now - set_at >= self._ttl
+
+    def _make_room(self, now: float) -> None:
+        self._remove_expired(now)
+        if len(self._entries) >= self._max_size:
+            self._entries.popitem(last=False)
+            self._evictions += 1
+
+    def _remove_expired(self, now: float) -> None:
+        if self._ttl is None:
+            return
+        expired = [key for key, (_, set_at) in self._entries.items() if self._is_expired(set_at, now)]
+        for key in expired:
+            del self._entries[key]
+
+
+def memoize(cache: Cache) -> Callable[[F], F]:
+    """Decorator factory caching a function's results in ``cache``.
+
+    Results are keyed by the call's positional and keyword arguments, which
+    must be hashable. Lookups go through ``cache.get``, so they count as hits
+    and misses. ``None`` results are cached too. Exceptions are not cached.
+    Each decorated function gets its own key space, so several functions can
+    share one cache without their entries colliding.
+
+    Usage::
+
+        @memoize(cache)
+        def load(user_id): ...
+    """
+    if not isinstance(cache, Cache):
+        raise TypeError(
+            f"memoize() expects a Cache instance, got {type(cache).__name__}; "
+            "use it as @memoize(cache)"
+        )
+
+    def decorator(func: F) -> F:
+        # A token only this function's keys contain, so its entries cannot
+        # collide with another function's or with keys set on the cache directly.
+        namespace = object()
+
+        @functools.wraps(func)
+        def wrapper(*args: Any, **kwargs: Any) -> Any:
+            key = (namespace, args, tuple(sorted(kwargs.items())))
+            result = cache.get(key, _MISSING)
+            if result is _MISSING:
+                result = func(*args, **kwargs)
+                cache.set(key, result)
+            return result
+
+        return wrapper  # type: ignore[return-value]
+
+    return decorator
+
+
+def _require_positive_int(name: str, value: object) -> None:
+    # bool is a subclass of int, but True/False as a size is almost certainly a mistake.
+    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
+        raise ValueError(f"{name} must be an integer greater than 0, got {value!r}")
+
+
+def _require_positive_number(name: str, value: object) -> None:
+    # `not value > 0` also rejects NaN, which compares false with everything.
+    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not value > 0:
+        raise ValueError(f"{name} must be None or a number greater than 0, got {value!r}")
```

### Implementation 2

```diff
diff -ruN before/cache/store.py after/cache/store.py
--- before/cache/store.py
+++ after/cache/store.py
@@ -0,0 +1,137 @@
+"""In-memory cache with a size limit, optional expiry, hit statistics and memoization."""
+
+import functools
+import numbers
+import time
+from collections import OrderedDict
+from collections.abc import Callable, Hashable
+from dataclasses import dataclass
+from typing import Any
+
+
+@dataclass(frozen=True)
+class CacheStats:
+    hits: int
+    misses: int
+    evictions: int
+
+
+@dataclass(frozen=True, slots=True)
+class _Entry:
+    value: Any
+    set_at: float
+
+
+class Cache:
+    """Least-recently-used cache holding at most `max_size` entries.
+
+    With `ttl_seconds`, an entry expires once that many seconds have passed
+    since it was last set; expired entries behave as if they were absent.
+    """
+
+    def __init__(
+        self,
+        max_size: int,
+        ttl_seconds: float | None = None,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not _is_positive_integer(max_size):
+            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
+        if ttl_seconds is not None and not _is_positive_number(ttl_seconds):
+            raise ValueError(
+                f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}"
+            )
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+        self._max_size = max_size
+        self._ttl_seconds = ttl_seconds
+        self._clock = clock
+        self._entries: OrderedDict[Hashable, _Entry] = OrderedDict()
+        self._hits = 0
+        self._misses = 0
+        self._evictions = 0
+
+    def set(self, key: Hashable, value: Any) -> None:
+        now = self._clock()
+        if key not in self._entries and len(self._entries) >= self._max_size:
+            self._make_room(now)
+        self._entries[key] = _Entry(value, set_at=now)
+        self._entries.move_to_end(key)
+
+    def get(self, key: Hashable, default: Any = None) -> Any:
+        entry = self._find_live_entry(key, self._clock())
+        if entry is None:
+            self._misses += 1
+            return default
+        self._hits += 1
+        self._entries.move_to_end(key)
+        return entry.value
+
+    def delete(self, key: Hashable) -> bool:
+        """Remove `key`; return True only if it had a live entry."""
+        entry = self._entries.pop(key, None)
+        return entry is not None and not self._is_expired(entry, self._clock())
+
+    def clear(self) -> None:
+        self._entries.clear()
+
+    def stats(self) -> CacheStats:
+        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)
+
+    def __len__(self) -> int:
+        now = self._clock()
+        return sum(1 for entry in self._entries.values() if not self._is_expired(entry, now))
+
+    def __contains__(self, key: Hashable) -> bool:
+        return self._find_live_entry(key, self._clock()) is not None
+
+    def _make_room(self, now: float) -> None:
+        self._remove_expired(now)
+        if len(self._entries) >= self._max_size:
+            self._entries.popitem(last=False)
+            self._evictions += 1
+
+    def _remove_expired(self, now: float) -> None:
+        expired_keys = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
+        for key in expired_keys:
+            del self._entries[key]
+
+    def _find_live_entry(self, key: Hashable, now: float) -> _Entry | None:
+        entry = self._entries.get(key)
+        if entry is None or self._is_expired(entry, now):
+            return None
+        return entry
+
+    def _is_expired(self, entry: _Entry, now: float) -> bool:
+        return self._ttl_seconds is not None and now - entry.set_at >= self._ttl_seconds
+
+
+# Distinguishes "not cached" from a cached result of None.
+_MISSING = object()
+
+
+def memoize(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
+    """Cache a function's results in `cache`, keyed by the function and its arguments."""
+
+    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
+        @functools.wraps(func)
+        def wrapper(*args: Hashable, **kwargs: Hashable) -> Any:
+            key = (func, args, frozenset(kwargs.items()))
+            result = cache.get(key, _MISSING)
+            if result is _MISSING:
+                result = func(*args, **kwargs)
+                cache.set(key, result)
+            return result
+
+        return wrapper
+
+    return decorator
+
+
+def _is_positive_integer(value: object) -> bool:
+    return isinstance(value, numbers.Integral) and not isinstance(value, bool) and value > 0
+
+
+def _is_positive_number(value: object) -> bool:
+    # `value > 0` is False for NaN, so NaN is rejected too.
+    return isinstance(value, numbers.Real) and not isinstance(value, bool) and value > 0
diff -ruN before/tests/test_cache_store.py after/tests/test_cache_store.py
--- before/tests/test_cache_store.py
+++ after/tests/test_cache_store.py
@@ -0,0 +1,305 @@
+import math
+
+import pytest
+
+from cache.store import Cache, memoize
+
+
+class FakeClock:
+    def __init__(self) -> None:
+        self.now = 0.0
+
+    def __call__(self) -> float:
+        return self.now
+
+    def advance(self, seconds: float) -> None:
+        self.now += seconds
+
+
+@pytest.fixture
+def clock() -> FakeClock:
+    return FakeClock()
+
+
+@pytest.mark.parametrize("max_size", [0, -1, 1.5, "3", None, True])
+def test_rejects_invalid_max_size(max_size):
+    with pytest.raises(ValueError):
+        Cache(max_size)
+
+
+@pytest.mark.parametrize("ttl_seconds", [0, -1, "5", True, math.nan])
+def test_rejects_invalid_ttl(ttl_seconds):
+    with pytest.raises(ValueError):
+        Cache(1, ttl_seconds=ttl_seconds)
+
+
+def test_rejects_non_callable_clock():
+    with pytest.raises(ValueError):
+        Cache(1, clock=0.0)
+
+
+def test_accepts_fractional_ttl(clock):
+    cache = Cache(1, ttl_seconds=0.5, clock=clock)
+    cache.set("a", 1)
+
+    assert cache.get("a") == 1
+
+
+def test_get_returns_stored_value_and_counts_hit():
+    cache = Cache(2)
+    cache.set("a", 1)
+
+    assert cache.get("a") == 1
+    assert cache.stats().hits == 1
+    assert cache.stats().misses == 0
+
+
+def test_get_of_absent_key_returns_default_and_counts_miss():
+    cache = Cache(2)
+
+    assert cache.get("missing") is None
+    assert cache.get("missing", "fallback") == "fallback"
+    assert cache.stats().misses == 2
+    assert cache.stats().hits == 0
+
+
+def test_set_replaces_previous_value():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("a", 2)
+
+    assert cache.get("a") == 2
+    assert len(cache) == 1
+
+
+def test_adding_to_full_cache_evicts_least_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("c", 3)
+
+    assert "a" not in cache
+    assert "b" in cache and "c" in cache
+    assert cache.stats().evictions == 1
+
+
+def test_get_makes_entry_most_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.get("a")
+    cache.set("c", 3)
+
+    assert "a" in cache
+    assert "b" not in cache
+
+
+def test_set_of_existing_key_makes_it_most_recently_used():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("a", 10)
+    cache.set("c", 3)
+
+    assert cache.get("a") == 10
+    assert "b" not in cache
+
+
+def test_replacing_key_in_full_cache_evicts_nothing():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+    cache.set("b", 20)
+
+    assert len(cache) == 2
+    assert cache.stats().evictions == 0
+
+
+def test_len_and_contains_do_not_affect_recency_or_stats():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.set("b", 2)
+
+    assert "a" in cache
+    assert "missing" not in cache
+    assert len(cache) == 2
+    cache.set("c", 3)
+
+    assert "a" not in cache
+    stats = cache.stats()
+    assert (stats.hits, stats.misses) == (0, 0)
+
+
+def test_entry_is_live_just_before_ttl(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(9.999)
+
+    assert cache.get("a") == 1
+
+
+def test_entry_expires_once_ttl_has_passed(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(10)
+
+    assert cache.get("a", "gone") == "gone"
+    assert "a" not in cache
+    assert len(cache) == 0
+    assert cache.stats().misses == 1
+
+
+def test_entries_never_expire_without_ttl(clock):
+    cache = Cache(2, clock=clock)
+    cache.set("a", 1)
+    clock.advance(1e9)
+
+    assert cache.get("a") == 1
+
+
+def test_set_restarts_expiry(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(8)
+    cache.set("a", 2)
+    clock.advance(8)
+
+    assert cache.get("a") == 2
+
+
+def test_get_does_not_restart_expiry(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(8)
+    cache.get("a")
+    clock.advance(2)
+
+    assert "a" not in cache
+
+
+def test_expired_entries_are_removed_before_evicting(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("expiring", 1)
+    clock.advance(5)
+    cache.set("least_recent", 2)
+    cache.get("expiring")
+    clock.advance(5)
+    cache.set("new", 3)
+
+    assert "least_recent" in cache and "new" in cache
+    assert cache.stats().evictions == 0
+
+
+def test_len_counts_only_live_entries(clock):
+    cache = Cache(3, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(5)
+    cache.set("b", 2)
+    clock.advance(5)
+
+    assert len(cache) == 1
+
+
+def test_delete_of_live_entry_returns_true_and_removes_it():
+    cache = Cache(2)
+    cache.set("a", 1)
+
+    assert cache.delete("a") is True
+    assert "a" not in cache
+
+
+def test_delete_of_absent_key_returns_false():
+    cache = Cache(2)
+
+    assert cache.delete("missing") is False
+
+
+def test_delete_of_expired_entry_returns_false(clock):
+    cache = Cache(2, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    clock.advance(10)
+
+    assert cache.delete("a") is False
+
+
+def test_deleted_and_expired_entries_are_not_counted_as_evictions(clock):
+    cache = Cache(1, ttl_seconds=10, clock=clock)
+    cache.set("a", 1)
+    cache.delete("a")
+    cache.set("b", 2)
+    clock.advance(10)
+    cache.set("c", 3)
+
+    assert cache.stats().evictions == 0
+
+
+def test_clear_removes_entries_but_keeps_stats():
+    cache = Cache(2)
+    cache.set("a", 1)
+    cache.get("a")
+    cache.get("missing")
+    cache.clear()
+
+    assert len(cache) == 0
+    assert "a" not in cache
+    stats = cache.stats()
+    assert (stats.hits, stats.misses) == (1, 1)
+
+
+def test_memoize_calls_function_once_per_arguments():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def square(x):
+        calls.append(x)
+        return x * x
+
+    assert square(3) == 9
+    assert square(3) == 9
+    assert square(4) == 16
+    assert calls == [3, 4]
+    stats = cache.stats()
+    assert (stats.hits, stats.misses) == (1, 2)
+
+
+def test_memoize_distinguishes_keyword_arguments():
+    cache = Cache(10)
+
+    @memoize(cache)
+    def describe(name, greeting="hi"):
+        return f"{greeting} {name}"
+
+    assert describe("ann", greeting="hi") == "hi ann"
+    assert describe("ann", greeting="yo") == "yo ann"
+
+
+def test_memoize_caches_none_results():
+    cache = Cache(10)
+    calls = []
+
+    @memoize(cache)
+    def nothing(x):
+        calls.append(x)
+
+    nothing(1)
+    nothing(1)
+
+    assert calls == [1]
+    assert cache.stats().hits == 1
+
+
+def test_memoized_functions_sharing_a_cache_do_not_collide():
+    cache = Cache(10)
+
+    @memoize(cache)
+    def double(x):
+        return x * 2
+
+    @memoize(cache)
+    def triple(x):
+        return x * 3
+
+    assert double(5) == 10
+    assert triple(5) == 15
+    assert double(5) == 10
```

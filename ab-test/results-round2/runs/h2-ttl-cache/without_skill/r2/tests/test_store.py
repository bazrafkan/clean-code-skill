import math

import pytest

from cache.store import Cache, memoize


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def stats_tuple(cache):
    s = cache.stats()
    return (s.hits, s.misses, s.evictions)


# --- construction -----------------------------------------------------------


@pytest.mark.parametrize("max_size", [0, -1, 1.5, 2.0, "3", None, True])
def test_invalid_max_size(max_size):
    with pytest.raises(ValueError):
        Cache(max_size)


@pytest.mark.parametrize("ttl", [0, -1, -0.5, "1", True, math.nan, [1]])
def test_invalid_ttl(ttl):
    with pytest.raises(ValueError):
        Cache(1, ttl_seconds=ttl)


def test_invalid_clock():
    with pytest.raises(ValueError):
        Cache(1, clock=42)


@pytest.mark.parametrize("ttl", [None, 1, 0.25, math.inf])
def test_valid_arguments(ttl):
    Cache(1, ttl_seconds=ttl, clock=FakeClock())


def test_works_with_default_clock():
    cache = Cache(2, ttl_seconds=60)
    cache.set("a", 1)
    assert cache.get("a") == 1


# --- basic operations -------------------------------------------------------


def test_get_returns_value_or_default():
    cache = Cache(2)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("missing") is None
    assert cache.get("missing", "dflt") == "dflt"


def test_set_replaces_value():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("a", 2)
    assert cache.get("a") == 2
    assert len(cache) == 1


def test_stores_none_values():
    cache = Cache(2)
    cache.set("a", None)
    assert "a" in cache
    assert cache.get("a", "dflt") is None
    assert stats_tuple(cache) == (1, 0, 0)


def test_delete():
    cache = Cache(2)
    cache.set("a", 1)
    assert cache.delete("a") is True
    assert cache.delete("a") is False
    assert "a" not in cache
    assert cache.delete("never") is False


def test_clear_keeps_stats():
    cache = Cache(2)
    cache.set("a", 1)
    cache.get("a")
    cache.get("b")
    cache.clear()
    assert len(cache) == 0
    assert "a" not in cache
    assert stats_tuple(cache) == (1, 1, 0)


# --- LRU eviction -----------------------------------------------------------


def test_evicts_least_recently_used():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert "a" not in cache
    assert cache.get("b") == 2 and cache.get("c") == 3
    assert cache.stats().evictions == 1


def test_get_refreshes_recency():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)
    assert "a" in cache and "b" not in cache


def test_set_existing_refreshes_recency_without_eviction():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)
    assert cache.stats().evictions == 0
    cache.set("c", 3)
    assert "a" in cache and "b" not in cache


def test_missed_get_does_not_refresh_anything():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("zzz")
    cache.set("c", 3)
    assert "a" not in cache


def test_len_and_contains_do_not_touch_recency_or_stats():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert "a" in cache
    assert "zzz" not in cache
    assert len(cache) == 2
    cache.set("c", 3)
    assert "a" not in cache  # "a" stayed least recently used
    assert stats_tuple(cache) == (0, 0, 1)


def test_delete_and_clear_are_not_evictions():
    cache = Cache(2)
    cache.set("a", 1)
    cache.delete("a")
    cache.set("b", 2)
    cache.clear()
    assert cache.stats().evictions == 0


# --- expiry -----------------------------------------------------------------


def test_entry_expires_exactly_at_ttl():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(9.999)
    assert cache.get("a") == 1
    clock.advance(0.001)
    assert cache.get("a", "gone") == "gone"
    assert stats_tuple(cache) == (1, 1, 0)


def test_expired_entry_behaves_as_absent():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=5, clock=clock)
    cache.set("a", 1)
    clock.advance(5)
    assert "a" not in cache
    assert len(cache) == 0
    assert cache.delete("a") is False
    assert stats_tuple(cache) == (0, 0, 0)


def test_set_restarts_expiry_but_get_does_not():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    clock.advance(6)
    cache.set("a", 10)
    cache.get("b")
    clock.advance(6)
    assert cache.get("a") == 10
    assert "b" not in cache


def test_set_on_full_cache_removes_expired_before_evicting():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("old", 1)
    clock.advance(5)
    cache.set("fresh", 2)
    cache.get("old")  # "old" is now most recently used, but expires first
    clock.advance(5)
    cache.set("new", 3)
    assert "fresh" in cache and "new" in cache
    assert cache.stats().evictions == 0


def test_set_on_full_cache_evicts_when_nothing_expired():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    clock.advance(9)
    cache.set("c", 3)
    assert "a" not in cache and "b" in cache and "c" in cache
    assert cache.stats().evictions == 1


def test_resetting_expired_key_in_full_cache_does_not_evict():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(10)
    cache.set("b", 2)
    cache.set("a", 3)
    assert cache.get("a") == 3 and cache.get("b") == 2
    assert cache.stats().evictions == 0


def test_stats_are_integers_and_snapshots():
    cache = Cache(1)
    cache.set("a", 1)
    cache.get("a")
    cache.get("b")
    cache.set("b", 2)
    snapshot = cache.stats()
    assert (snapshot.hits, snapshot.misses, snapshot.evictions) == (1, 1, 1)
    assert all(type(v) is int for v in (snapshot.hits, snapshot.misses, snapshot.evictions))
    cache.get("b")
    assert snapshot.hits == 1


# --- memoize ----------------------------------------------------------------


def test_memoize_caches_and_counts():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def square(x):
        calls.append(x)
        return x * x

    assert square(3) == 9
    assert square(3) == 9
    assert calls == [3]
    assert stats_tuple(cache) == (1, 1, 0)


def test_memoize_caches_none():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def nothing(x):
        calls.append(x)
        return None

    assert nothing(1) is None
    assert nothing(1) is None
    assert calls == [1]
    assert stats_tuple(cache) == (1, 1, 0)


def test_memoize_shared_cache_does_not_collide():
    cache = Cache(10)

    @memoize(cache)
    def double(x):
        return x * 2

    @memoize(cache)
    def triple(x):
        return x * 3

    cache.set((5,), "user value")
    assert double(5) == 10
    assert triple(5) == 15
    assert double(5) == 10
    assert cache.get((5,)) == "user value"


def test_memoize_keyword_arguments():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def f(a, b=0, *, c=0):
        calls.append((a, b, c))
        return a + 10 * b + 100 * c

    assert f(1, b=2, c=3) == 321
    assert f(1, c=3, b=2) == 321  # keyword order does not matter
    assert f(1, 2, c=3) == 321  # different call shape, separate entry
    assert f(1) == 1
    assert calls == [(1, 2, 3), (1, 2, 3), (1, 0, 0)]


def test_memoize_does_not_cache_exceptions():
    cache = Cache(10)
    attempts = []

    @memoize(cache)
    def flaky(x):
        attempts.append(x)
        if len(attempts) == 1:
            raise RuntimeError("boom")
        return x

    with pytest.raises(RuntimeError):
        flaky(1)
    assert flaky(1) == 1
    assert flaky(1) == 1
    assert attempts == [1, 1]


def test_memoize_respects_eviction_and_expiry():
    clock = FakeClock()
    cache = Cache(1, ttl_seconds=10, clock=clock)
    calls = []

    @memoize(cache)
    def ident(x):
        calls.append(x)
        return x

    ident(1)
    ident(2)  # evicts 1
    ident(1)
    clock.advance(10)
    ident(1)  # expired
    assert calls == [1, 2, 1, 1]


def test_memoize_preserves_metadata_and_recursion():
    cache = Cache(100)

    @memoize(cache)
    def fib(n):
        """Fibonacci."""
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    assert fib(60) == 1548008755920
    assert fib.__name__ == "fib"
    assert fib.__doc__ == "Fibonacci."


def test_memoize_without_cache_argument_fails_clearly():
    with pytest.raises(TypeError):

        @memoize
        def f(x):
            return x

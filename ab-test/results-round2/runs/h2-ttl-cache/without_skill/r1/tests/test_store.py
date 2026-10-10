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


@pytest.fixture
def clock():
    return FakeClock()


# --- construction -----------------------------------------------------------------------


@pytest.mark.parametrize("max_size", [0, -1, 1.5, 2.0, True, "3", None])
def test_invalid_max_size_raises(max_size):
    with pytest.raises(ValueError):
        Cache(max_size)


@pytest.mark.parametrize("ttl", [0, -1, -0.5, math.nan, True, "1"])
def test_invalid_ttl_raises(ttl):
    with pytest.raises(ValueError):
        Cache(1, ttl_seconds=ttl)


def test_non_callable_clock_raises():
    with pytest.raises(ValueError):
        Cache(1, clock=5)


@pytest.mark.parametrize("ttl", [None, 1, 0.25])
def test_valid_ttl_accepted(ttl):
    Cache(1, ttl_seconds=ttl)


def test_default_clock_works():
    cache = Cache(2, ttl_seconds=60)
    cache.set("a", 1)
    assert cache.get("a") == 1


# --- get / set / delete / clear ----------------------------------------------------------


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


def test_evicts_least_recently_used():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert "a" not in cache
    assert "b" in cache and "c" in cache
    assert cache.stats().evictions == 1


def test_get_makes_entry_most_recently_used():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)
    assert "a" in cache
    assert "b" not in cache


def test_set_of_existing_key_makes_it_most_recently_used_without_evicting():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)
    assert cache.stats().evictions == 0
    cache.set("c", 3)
    assert cache.get("a") == 10
    assert "b" not in cache


def test_len_and_contains_do_not_affect_stats_or_recency():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert "a" in cache
    assert "zzz" not in cache
    assert len(cache) == 2
    cache.set("c", 3)
    assert "a" not in cache  # still the least recently used despite the `in` check
    stats = cache.stats()
    assert (stats.hits, stats.misses) == (0, 0)


def test_delete():
    cache = Cache(2)
    cache.set("a", 1)
    assert cache.delete("a") is True
    assert cache.delete("a") is False
    assert cache.delete("never") is False
    assert "a" not in cache
    assert cache.stats().evictions == 0


def test_clear_keeps_stats():
    cache = Cache(3)
    cache.set("a", 1)
    cache.get("a")
    cache.get("x")
    cache.clear()
    assert len(cache) == 0
    assert "a" not in cache
    stats = cache.stats()
    assert (stats.hits, stats.misses) == (1, 1)


def test_stats_counts_hits_and_misses_as_ints():
    cache = Cache(2)
    cache.set("a", None)
    assert cache.get("a", "dflt") is None  # stored None is a hit, not the default
    cache.get("b")
    cache.get("b")
    stats = cache.stats()
    assert (stats.hits, stats.misses, stats.evictions) == (1, 2, 0)
    assert all(type(n) is int for n in (stats.hits, stats.misses, stats.evictions))


# --- expiry ------------------------------------------------------------------------------


def test_entry_expires_once_ttl_has_passed(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(9.999)
    assert "a" in cache
    clock.advance(0.001)  # exactly ttl -> expired
    assert "a" not in cache
    assert len(cache) == 0
    assert cache.get("a", "gone") == "gone"
    assert cache.stats().misses == 1


def test_set_restarts_expiry_but_get_does_not(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(6)
    cache.set("a", 2)
    clock.advance(6)
    assert cache.get("a") == 2
    clock.advance(4)
    assert cache.get("a") is None


def test_delete_of_expired_entry_returns_false(clock):
    cache = Cache(2, ttl_seconds=1, clock=clock)
    cache.set("a", 1)
    clock.advance(1)
    assert cache.delete("a") is False


def test_expired_entries_are_removed_before_evicting(clock):
    cache = Cache(3, ttl_seconds=10, clock=clock)
    cache.set("old", 1)
    clock.advance(5)
    cache.set("b", 2)
    cache.set("c", 3)
    clock.advance(5)  # "old" has expired; "b" and "c" are live
    cache.set("d", 4)
    assert cache.stats().evictions == 0
    assert all(k in cache for k in ("b", "c", "d"))


def test_evicts_lru_when_nothing_has_expired(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert "a" not in cache
    assert cache.stats().evictions == 1


def test_setting_an_expired_key_does_not_evict_others(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(5)
    cache.set("b", 2)
    clock.advance(5)  # "a" expired
    cache.set("a", 3)
    assert cache.stats().evictions == 0
    assert cache.get("a") == 3 and cache.get("b") == 2


# --- memoize -----------------------------------------------------------------------------


def test_memoize_caches_results_and_counts_hits_and_misses():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def square(x):
        calls.append(x)
        return x * x

    assert square(3) == 9
    assert square(3) == 9
    assert square(4) == 16
    assert calls == [3, 4]
    stats = cache.stats()
    assert (stats.hits, stats.misses) == (1, 2)


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
    assert cache.stats().hits == 1


def test_memoize_uses_keyword_arguments():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def f(a, b=0, *, c=0):
        calls.append((a, b, c))
        return a + b + c

    assert f(1, b=2, c=3) == 6
    assert f(1, c=3, b=2) == 6  # keyword order does not matter
    assert f(1, b=2, c=4) == 7
    assert len(calls) == 2


def test_functions_sharing_a_cache_do_not_collide():
    cache = Cache(10)

    @memoize(cache)
    def double(x):
        return x * 2

    @memoize(cache)
    def triple(x):
        return x * 3

    cache.set((5,), "direct")
    assert double(5) == 10
    assert triple(5) == 15
    assert double(5) == 10
    assert cache.get((5,)) == "direct"


def test_memoize_preserves_function_metadata():
    @memoize(Cache(1))
    def documented():
        """Docstring."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docstring."


def test_memoize_respects_expiry(clock):
    cache = Cache(10, ttl_seconds=5, clock=clock)
    calls = []

    @memoize(cache)
    def f(x):
        calls.append(x)
        return x

    f(1)
    clock.advance(5)
    f(1)
    assert calls == [1, 1]

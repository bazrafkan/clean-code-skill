import pytest

from cache.store import Cache, memoize


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


# Construction


@pytest.mark.parametrize("max_size", [0, -1, 1.5, 2.0, "3", None, True])
def test_rejects_invalid_max_size(max_size):
    with pytest.raises(ValueError, match="max_size"):
        Cache(max_size)


@pytest.mark.parametrize("ttl_seconds", [0, -1, "1", float("nan"), True])
def test_rejects_invalid_ttl(ttl_seconds):
    with pytest.raises(ValueError, match="ttl_seconds"):
        Cache(1, ttl_seconds=ttl_seconds)


def test_rejects_non_callable_clock():
    with pytest.raises(ValueError, match="clock"):
        Cache(1, clock=5)


def test_accepts_fractional_ttl(clock):
    cache = Cache(1, ttl_seconds=0.5, clock=clock)
    cache.set("a", 1)
    clock.advance(0.4)

    assert cache.get("a") == 1


# get and set


def test_get_returns_stored_value_and_counts_hit():
    cache = Cache(2)
    cache.set("a", 1)

    assert cache.get("a") == 1
    assert cache.stats().hits == 1
    assert cache.stats().misses == 0


def test_get_missing_key_returns_default_and_counts_miss():
    cache = Cache(2)

    assert cache.get("a") is None
    assert cache.get("a", "fallback") == "fallback"
    assert cache.stats().misses == 2
    assert cache.stats().hits == 0


def test_set_replaces_previous_value():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("a", 2)

    assert cache.get("a") == 2
    assert len(cache) == 1


def test_stored_none_is_a_hit():
    cache = Cache(1)
    cache.set("a", None)

    assert cache.get("a", "fallback") is None
    assert cache.stats().hits == 1


# Size limit and least-recently-used eviction


def test_adding_to_full_cache_evicts_least_recently_used():
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


def test_replacing_existing_key_in_full_cache_does_not_evict():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)

    assert len(cache) == 2
    assert cache.stats().evictions == 0


def test_replacing_key_makes_it_most_recently_used():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)
    cache.set("c", 3)

    assert "a" in cache
    assert "b" not in cache


def test_contains_and_len_do_not_change_recency_or_stats():
    cache = Cache(2)
    cache.set("a", 1)
    cache.set("b", 2)

    assert "a" in cache
    assert "missing" not in cache
    assert len(cache) == 2
    cache.set("c", 3)

    assert "a" not in cache
    assert cache.stats().hits == 0
    assert cache.stats().misses == 0


# Expiry


def test_entry_expires_exactly_when_ttl_has_passed(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)

    clock.advance(9.5)
    assert cache.get("a") == 1

    clock.advance(0.5)
    assert cache.get("a") is None
    assert cache.stats().hits == 1
    assert cache.stats().misses == 1


def test_expired_entries_are_absent_from_len_and_contains(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(5)
    cache.set("b", 2)
    clock.advance(5)

    assert "a" not in cache
    assert "b" in cache
    assert len(cache) == 1


def test_get_does_not_restart_expiry(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(5)
    cache.get("a")
    clock.advance(5)

    assert "a" not in cache


def test_set_restarts_expiry(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(8)
    cache.set("a", 2)
    clock.advance(8)

    assert cache.get("a") == 2


def test_entries_never_expire_without_ttl(clock):
    cache = Cache(1, clock=clock)
    cache.set("a", 1)
    clock.advance(1e9)

    assert cache.get("a") == 1


def test_full_cache_removes_expired_entries_before_evicting(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("old", 1)
    clock.advance(5)
    cache.set("recent", 2)
    cache.get("old")
    clock.advance(5)
    cache.set("new", 3)

    assert "recent" in cache
    assert "new" in cache
    assert cache.stats().evictions == 0


def test_resetting_expired_key_in_full_cache_does_not_evict(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    clock.advance(10)
    cache.set("a", 3)

    assert cache.get("a") == 3
    assert cache.stats().evictions == 0


# delete and clear


def test_delete_removes_live_entry():
    cache = Cache(2)
    cache.set("a", 1)

    assert cache.delete("a") is True
    assert "a" not in cache
    assert cache.stats().evictions == 0


def test_delete_missing_key_returns_false():
    cache = Cache(2)

    assert cache.delete("a") is False


def test_delete_expired_key_returns_false(clock):
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.advance(10)

    assert cache.delete("a") is False


def test_clear_removes_entries_but_keeps_stats():
    cache = Cache(2)
    cache.set("a", 1)
    cache.get("a")
    cache.get("missing")
    cache.clear()

    assert len(cache) == 0
    assert "a" not in cache
    assert (cache.stats().hits, cache.stats().misses) == (1, 1)


# memoize


def test_memoize_calls_function_once_per_arguments():
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
    assert (cache.stats().hits, cache.stats().misses) == (1, 2)


def test_memoize_caches_none_results():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def record(x):
        calls.append(x)

    record(1)
    record(1)

    assert calls == [1]


def test_memoize_keys_on_keyword_arguments():
    cache = Cache(10)
    calls = []

    @memoize(cache)
    def describe(a, b=0):
        calls.append((a, b))
        return a + b

    assert describe(1, b=2) == 3
    assert describe(1, b=2) == 3
    assert describe(1, b=5) == 6
    assert calls == [(1, 2), (1, 5)]


def test_memoized_functions_sharing_a_cache_do_not_collide():
    cache = Cache(10)

    @memoize(cache)
    def double(x):
        return x * 2

    @memoize(cache)
    def triple(x):
        return x * 3

    assert double(5) == 10
    assert triple(5) == 15
    assert double(5) == 10

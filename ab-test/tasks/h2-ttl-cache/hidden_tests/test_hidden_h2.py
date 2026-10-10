import pytest

from cache.store import Cache, memoize


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def _stats(cache):
    s = cache.stats()
    return (s.hits, s.misses, s.evictions)


@pytest.mark.parametrize("max_size", [0, -1, 1.5, "3", None])
def test_invalid_max_size(max_size):
    with pytest.raises(ValueError):
        Cache(max_size)


@pytest.mark.parametrize("ttl", [0, -1, -0.5])
def test_invalid_ttl(ttl):
    with pytest.raises(ValueError):
        Cache(3, ttl_seconds=ttl)


def test_valid_arguments_and_default_clock():
    Cache(1, ttl_seconds=0.5)
    cache = Cache(2)
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_get_returns_value_or_default():
    cache = Cache(3, clock=FakeClock())
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("b") is None
    assert cache.get("b", "fallback") == "fallback"


def test_set_replaces_value():
    cache = Cache(3, clock=FakeClock())
    cache.set("a", 1)
    cache.set("a", 2)
    assert cache.get("a") == 2
    assert len(cache) == 1


def test_least_recently_used_is_evicted():
    cache = Cache(2, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)
    assert "b" not in cache
    assert cache.get("a") == 1 and cache.get("c") == 3
    assert cache.stats().evictions == 1


def test_updating_a_key_in_a_full_cache_does_not_evict_and_refreshes_recency():
    cache = Cache(2, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("a", 10)
    assert cache.stats().evictions == 0
    cache.set("c", 3)
    assert "b" not in cache
    assert "a" in cache and "c" in cache


def test_several_evictions_are_counted():
    cache = Cache(1, clock=FakeClock())
    for i in range(5):
        cache.set(i, i)
    assert len(cache) == 1
    assert 4 in cache
    assert cache.stats().evictions == 4


def test_entry_expires_after_ttl():
    clock = FakeClock()
    cache = Cache(3, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.now = 9.99
    assert cache.get("a") == 1
    clock.now = 10
    assert cache.get("a") is None
    assert "a" not in cache


def test_set_restarts_expiry_but_get_does_not():
    clock = FakeClock()
    cache = Cache(3, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    clock.now = 5
    cache.set("a", 1)
    cache.get("b")
    clock.now = 12
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_no_ttl_never_expires():
    clock = FakeClock()
    cache = Cache(3, clock=clock)
    cache.set("a", 1)
    clock.now = 10**9
    assert cache.get("a") == 1


def test_expired_entries_are_removed_before_evicting_live_ones():
    clock = FakeClock()
    cache = Cache(2, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.now = 5
    cache.set("b", 2)
    clock.now = 6
    cache.get("a")
    clock.now = 11
    cache.set("c", 3)
    assert "b" in cache and "c" in cache
    assert "a" not in cache
    assert cache.stats().evictions == 0


def test_len_counts_only_live_entries():
    clock = FakeClock()
    cache = Cache(5, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    clock.now = 4
    cache.set("b", 2)
    cache.set("c", 3)
    assert len(cache) == 3
    clock.now = 10
    assert len(cache) == 2
    clock.now = 14
    assert len(cache) == 0


def test_contains_and_len_do_not_touch_stats_or_recency():
    cache = Cache(2, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    assert "a" in cache
    assert "zzz" not in cache
    assert len(cache) == 2
    assert _stats(cache) == (0, 0, 0)
    cache.set("c", 3)
    assert "a" not in cache
    assert "b" in cache


def test_hits_and_misses_are_counted():
    clock = FakeClock()
    cache = Cache(3, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.get("a")
    cache.get("a")
    cache.get("missing")
    clock.now = 10
    cache.get("a")
    assert _stats(cache) == (2, 2, 0)


def test_stats_are_integers():
    stats = Cache(1).stats()
    assert all(isinstance(v, int) for v in (stats.hits, stats.misses, stats.evictions))


def test_delete():
    clock = FakeClock()
    cache = Cache(3, ttl_seconds=10, clock=clock)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.delete("a") is True
    assert "a" not in cache
    assert cache.delete("a") is False
    assert cache.delete("never") is False
    clock.now = 10
    assert cache.delete("b") is False
    assert _stats(cache) == (0, 0, 0)


def test_clear_keeps_statistics():
    cache = Cache(3, clock=FakeClock())
    cache.set("a", 1)
    cache.get("a")
    cache.get("x")
    cache.clear()
    assert len(cache) == 0
    assert "a" not in cache
    assert _stats(cache) == (1, 1, 0)


def test_falsy_values_are_stored():
    cache = Cache(3, clock=FakeClock())
    cache.set("zero", 0)
    cache.set("none", None)
    assert cache.get("zero", "default") == 0
    assert cache.get("none", "default") is None
    assert _stats(cache) == (2, 0, 0)


def test_memoize_caches_by_arguments():
    calls = []
    cache = Cache(10, clock=FakeClock())

    @memoize(cache)
    def add(a, b=0):
        calls.append((a, b))
        return a + b

    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert add(1, b=2) == 3
    assert add(1, b=2) == 3
    assert add(2) == 2
    assert add(2) == 2
    # add(1, b=2) may or may not share the entry of add(1, 2): the task leaves that open.
    assert len(calls) in (2, 3)


def test_memoize_calls_function_once_per_argument_set():
    calls = []
    cache = Cache(10, clock=FakeClock())

    @memoize(cache)
    def square(x):
        calls.append(x)
        return x * x

    assert [square(3), square(3), square(4), square(3)] == [9, 9, 16, 9]
    assert calls == [3, 4]
    assert _stats(cache) == (2, 2, 0)


def test_memoize_distinguishes_keyword_arguments():
    cache = Cache(10, clock=FakeClock())

    @memoize(cache)
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}"

    assert greet("Ada") == "Hello, Ada"
    assert greet("Ada", greeting="Hi") == "Hi, Ada"
    assert greet("Ada", greeting="Hey") == "Hey, Ada"


def test_memoize_caches_none():
    calls = []
    cache = Cache(10, clock=FakeClock())

    @memoize(cache)
    def lookup(key):
        calls.append(key)
        return None

    assert lookup("x") is None
    assert lookup("x") is None
    assert calls == ["x"]


def test_memoized_functions_sharing_a_cache_do_not_collide():
    cache = Cache(10, clock=FakeClock())

    @memoize(cache)
    def double(x):
        return x * 2

    @memoize(cache)
    def triple(x):
        return x * 3

    assert double(5) == 10
    assert triple(5) == 15
    assert double(5) == 10


def test_memoize_recomputes_after_expiry():
    calls = []
    clock = FakeClock()
    cache = Cache(10, ttl_seconds=10, clock=clock)

    @memoize(cache)
    def value(x):
        calls.append(x)
        return x

    value(1)
    clock.now = 5
    value(1)
    clock.now = 10
    value(1)
    assert calls == [1, 1]


def test_memoize_keeps_function_name():
    cache = Cache(10, clock=FakeClock())

    @memoize(cache)
    def compute(x):
        return x

    assert compute.__name__ == "compute"

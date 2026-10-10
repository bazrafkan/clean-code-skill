import pytest

from cache.store import Cache, CacheStats, memoize

TTL = 10


class FakeClock:
    """A controllable stand-in for time.monotonic."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def cache():
    return Cache(max_size=2)


@pytest.fixture
def expiring_cache(clock):
    return Cache(max_size=2, ttl_seconds=TTL, clock=clock)


class TestConstruction:
    @pytest.mark.parametrize("max_size", [0, -1, 1.5, "3", None, True])
    def test_rejects_invalid_max_size(self, max_size):
        with pytest.raises(ValueError, match="max_size"):
            Cache(max_size)

    @pytest.mark.parametrize("ttl_seconds", [0, -1, float("nan"), "10", True])
    def test_rejects_invalid_ttl(self, ttl_seconds):
        with pytest.raises(ValueError, match="ttl_seconds"):
            Cache(1, ttl_seconds=ttl_seconds)

    def test_rejects_non_callable_clock(self):
        with pytest.raises(ValueError, match="clock"):
            Cache(1, clock=0)

    @pytest.mark.parametrize("ttl_seconds", [None, 1, 0.5])
    def test_accepts_valid_ttl(self, ttl_seconds):
        cache = Cache(1, ttl_seconds=ttl_seconds)
        cache.set("a", 1)
        assert cache.get("a") == 1


class TestGetAndSet:
    def test_get_returns_stored_value(self, cache):
        cache.set("a", 1)
        assert cache.get("a") == 1

    def test_get_returns_default_for_missing_key(self, cache):
        assert cache.get("missing") is None
        assert cache.get("missing", "fallback") == "fallback"

    def test_set_replaces_previous_value(self, cache):
        cache.set("a", 1)
        cache.set("a", 2)
        assert cache.get("a") == 2
        assert len(cache) == 1

    def test_stores_none_as_a_value(self, cache):
        cache.set("a", None)
        assert cache.get("a", "fallback") is None


class TestEviction:
    def test_evicts_least_recently_used_entry_when_full(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert "a" not in cache
        assert "b" in cache
        assert "c" in cache

    def test_get_makes_entry_most_recently_used(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)
        assert "a" in cache
        assert "b" not in cache

    def test_set_makes_existing_entry_most_recently_used(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", 10)
        cache.set("c", 3)
        assert "a" in cache
        assert "b" not in cache

    def test_replacing_a_key_in_a_full_cache_evicts_nothing(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", 10)
        assert len(cache) == 2
        assert cache.stats().evictions == 0

    def test_contains_and_len_do_not_change_recency(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        assert "a" in cache
        assert len(cache) == 2
        cache.set("c", 3)
        assert "a" not in cache


class TestExpiry:
    def test_entry_is_live_until_ttl_has_passed(self, expiring_cache, clock):
        expiring_cache.set("a", 1)
        clock.advance(TTL - 0.001)
        assert expiring_cache.get("a") == 1

    def test_entry_expires_once_ttl_has_passed(self, expiring_cache, clock):
        expiring_cache.set("a", 1)
        clock.advance(TTL)
        assert expiring_cache.get("a", "fallback") == "fallback"

    def test_set_restarts_expiry(self, expiring_cache, clock):
        expiring_cache.set("a", 1)
        clock.advance(TTL - 1)
        expiring_cache.set("a", 2)
        clock.advance(TTL - 1)
        assert expiring_cache.get("a") == 2

    def test_get_does_not_restart_expiry(self, expiring_cache, clock):
        expiring_cache.set("a", 1)
        clock.advance(TTL - 1)
        expiring_cache.get("a")
        clock.advance(1)
        assert "a" not in expiring_cache

    def test_entries_never_expire_without_ttl(self, clock):
        cache = Cache(max_size=2, clock=clock)
        cache.set("a", 1)
        clock.advance(10**9)
        assert cache.get("a") == 1

    def test_expired_entry_is_neither_contained_nor_counted(
        self, expiring_cache, clock
    ):
        expiring_cache.set("a", 1)
        clock.advance(1)
        expiring_cache.set("b", 2)
        clock.advance(TTL - 1)
        assert "a" not in expiring_cache
        assert len(expiring_cache) == 1

    def test_full_cache_removes_expired_entries_before_evicting(
        self, expiring_cache, clock
    ):
        expiring_cache.set("expired", 1)
        clock.advance(TTL / 2)
        expiring_cache.set("live", 2)
        expiring_cache.get("expired")  # "live" is now the least recently used
        clock.advance(TTL / 2)
        expiring_cache.set("new", 3)
        assert "live" in expiring_cache
        assert "new" in expiring_cache
        assert expiring_cache.stats().evictions == 0

    def test_setting_an_expired_key_in_a_full_cache_evicts_nothing(
        self, expiring_cache, clock
    ):
        expiring_cache.set("a", 1)
        clock.advance(TTL / 2)
        expiring_cache.set("b", 2)
        clock.advance(TTL / 2)
        expiring_cache.set("a", 10)
        assert expiring_cache.get("a") == 10
        assert "b" in expiring_cache
        assert expiring_cache.stats().evictions == 0


class TestDeleteAndClear:
    def test_delete_removes_live_entry(self, cache):
        cache.set("a", 1)
        assert cache.delete("a") is True
        assert "a" not in cache

    def test_delete_missing_key_returns_false(self, cache):
        assert cache.delete("missing") is False

    def test_delete_expired_entry_returns_false(self, expiring_cache, clock):
        expiring_cache.set("a", 1)
        clock.advance(TTL)
        assert expiring_cache.delete("a") is False

    def test_clear_removes_all_entries_but_keeps_stats(self, cache):
        cache.set("a", 1)
        cache.get("a")
        cache.get("missing")
        cache.clear()
        assert len(cache) == 0
        assert cache.stats() == CacheStats(hits=1, misses=1, evictions=0)


class TestStats:
    def test_get_counts_hits_and_misses(self, cache):
        cache.set("a", 1)
        cache.get("a")
        cache.get("a")
        cache.get("missing")
        assert cache.stats() == CacheStats(hits=2, misses=1, evictions=0)

    def test_get_of_expired_entry_counts_a_miss(self, expiring_cache, clock):
        expiring_cache.set("a", 1)
        clock.advance(TTL)
        expiring_cache.get("a")
        assert expiring_cache.stats() == CacheStats(hits=0, misses=1, evictions=0)

    def test_contains_and_len_count_neither_hits_nor_misses(self, cache):
        cache.set("a", 1)
        assert "a" in cache
        assert "missing" not in cache
        assert len(cache) == 1
        assert cache.stats() == CacheStats(hits=0, misses=0, evictions=0)

    def test_evictions_count_only_entries_removed_to_make_room(
        self, expiring_cache, clock
    ):
        expiring_cache.set("a", 1)
        expiring_cache.set("b", 2)
        expiring_cache.set("c", 3)  # evicts "a"
        expiring_cache.delete("b")
        clock.advance(TTL)
        expiring_cache.set("d", 4)
        expiring_cache.set("e", 5)  # removes expired "c"
        assert expiring_cache.stats().evictions == 1


class TestMemoize:
    def test_returns_cached_result_for_same_arguments(self, cache):
        calls = []

        @memoize(cache)
        def square(x):
            calls.append(x)
            return x * x

        assert square(3) == 9
        assert square(3) == 9
        assert calls == [3]

    def test_counts_hits_and_misses(self, cache):
        @memoize(cache)
        def square(x):
            return x * x

        square(3)
        square(3)
        square(4)
        assert cache.stats() == CacheStats(hits=1, misses=2, evictions=0)

    def test_caches_none_results(self, cache):
        calls = []

        @memoize(cache)
        def find(x):
            calls.append(x)

        assert find(1) is None
        assert find(1) is None
        assert calls == [1]

    def test_keys_by_keyword_arguments_regardless_of_order(self, cache):
        calls = []

        @memoize(cache)
        def power(base, exponent):
            calls.append((base, exponent))
            return base**exponent

        assert power(base=2, exponent=3) == 8
        assert power(exponent=3, base=2) == 8
        assert power(base=3, exponent=2) == 9
        assert calls == [(2, 3), (3, 2)]

    def test_functions_sharing_a_cache_do_not_collide(self, cache):
        @memoize(cache)
        def double(x):
            return 2 * x

        @memoize(cache)
        def triple(x):
            return 3 * x

        assert double(5) == 10
        assert triple(5) == 15

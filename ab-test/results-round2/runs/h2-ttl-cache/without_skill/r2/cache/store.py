"""In-memory LRU cache with optional expiry, hit statistics and a memoizing decorator."""

import functools
import numbers
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any, NamedTuple, Optional

__all__ = ["Cache", "CacheStats", "memoize"]

# Lets memoize tell "not cached" apart from a cached None.
_MISSING = object()


@dataclass(frozen=True)
class CacheStats:
    """Counters of a cache, captured when ``Cache.stats()`` was called."""

    hits: int
    misses: int
    evictions: int


class _Entry(NamedTuple):
    value: Any
    set_at: float


class Cache:
    """Size-limited cache that evicts the least recently used entry.

    With ``ttl_seconds`` set, an entry expires once that many seconds have
    passed since it was last set; expired entries behave as if absent.
    """

    def __init__(
        self,
        max_size: int,
        ttl_seconds: Optional[float] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(max_size, bool)
            or not isinstance(max_size, numbers.Integral)
            or max_size <= 0
        ):
            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
        # `not ttl_seconds > 0` (rather than `<= 0`) also rejects NaN.
        if ttl_seconds is not None and (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, numbers.Real)
            or not ttl_seconds > 0
        ):
            raise ValueError(
                f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}"
            )
        if not callable(clock):
            raise ValueError(f"clock must be a callable, got {clock!r}")

        self._max_size = max_size
        self._ttl = ttl_seconds
        self._clock = clock
        # Ordered from least to most recently used.
        self._entries: "OrderedDict[Hashable, _Entry]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def set(self, key: Hashable, value: Any) -> None:
        now = self._clock()
        if key in self._entries:
            self._entries.move_to_end(key)
        elif len(self._entries) >= self._max_size:
            self._make_room(now)
        self._entries[key] = _Entry(value, now)

    def get(self, key: Hashable, default: Any = None) -> Any:
        entry = self._live_entry(key, self._clock())
        if entry is None:
            self._misses += 1
            return default
        self._entries.move_to_end(key)
        self._hits += 1
        return entry.value

    def delete(self, key: Hashable) -> bool:
        if self._live_entry(key, self._clock()) is None:
            return False
        del self._entries[key]
        return True

    def clear(self) -> None:
        self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)

    def __len__(self) -> int:
        self._remove_expired(self._clock())
        return len(self._entries)

    def __contains__(self, key: Hashable) -> bool:
        return self._live_entry(key, self._clock()) is not None

    def _live_entry(self, key: Hashable, now: float) -> Optional[_Entry]:
        """Return the entry for ``key`` if it is live, discarding it if expired."""
        entry = self._entries.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, now):
            del self._entries[key]
            return None
        return entry

    def _is_expired(self, entry: _Entry, now: float) -> bool:
        return self._ttl is not None and now - entry.set_at >= self._ttl

    def _remove_expired(self, now: float) -> None:
        # Recency order is not expiry order (get refreshes recency, not expiry),
        # so every entry has to be checked.
        if self._ttl is None:
            return
        expired = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
        for key in expired:
            del self._entries[key]

    def _make_room(self, now: float) -> None:
        """Free one slot: drop expired entries, else evict the least recently used one."""
        self._remove_expired(now)
        if len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
            self._evictions += 1


def memoize(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache a function's results in ``cache``, keyed by its arguments.

    Use as ``@memoize(cache)``. Arguments must be hashable. Several functions
    may share one cache; their entries never collide with each other or with
    keys set directly on the cache.
    """
    if not isinstance(cache, Cache):
        raise TypeError(f"memoize() expects a Cache, got {cache!r}; use @memoize(cache)")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # A private object no caller can construct, so keys are unique to this function.
        namespace = object()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (namespace, args, frozenset(kwargs.items()))
            result = cache.get(key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        return wrapper

    return decorator

"""In-memory cache with a size limit, optional expiry and hit statistics.

When the cache is full, the least recently used entry is evicted to make room.
Entries can optionally expire a fixed time after they were last set; an
expired entry behaves exactly as if it were absent.
"""

from __future__ import annotations

import functools
import numbers
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any, TypeVar

__all__ = ["Cache", "CacheStats", "memoize"]

F = TypeVar("F", bound=Callable[..., Any])

# Marks "no cached value", so that a cached None is still recognised as a hit.
_MISSING = object()


@dataclass(frozen=True)
class CacheStats:
    """Counters of a cache, as they were when ``Cache.stats()`` was called."""

    hits: int
    misses: int
    evictions: int


class Cache:
    """A size-limited, least-recently-used cache with optional expiry.

    Args:
        max_size: Maximum number of entries; an integer greater than 0.
        ttl_seconds: How long an entry lives after it was last set, or None
            for entries that never expire. Must be a number greater than 0.
        clock: Zero-argument callable returning the current time in seconds.

    Raises:
        ValueError: If any argument is invalid.
    """

    def __init__(
        self,
        max_size: int,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        _require_positive_int("max_size", max_size)
        if ttl_seconds is not None:
            _require_positive_number("ttl_seconds", ttl_seconds)
        if not callable(clock):
            raise ValueError(f"clock must be callable, got {clock!r}")

        self._max_size = max_size
        self._ttl = ttl_seconds
        self._clock = clock
        # key -> (value, time it was last set), ordered least to most recently used.
        # May still hold expired entries; they are dropped lazily.
        self._entries: OrderedDict[Hashable, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def set(self, key: Hashable, value: Any) -> None:
        """Store ``value`` under ``key`` as the most recently used entry.

        Replaces any previous value and restarts the entry's expiry. Adding a
        new key to a full cache first drops expired entries and, if that frees
        no room, evicts the least recently used entry.
        """
        now = self._clock()
        if key in self._entries:
            self._entries.move_to_end(key)
        elif len(self._entries) >= self._max_size:
            self._make_room(now)
        self._entries[key] = (value, now)

    def get(self, key: Hashable, default: Any = None) -> Any:
        """Return the live value for ``key``, or ``default`` if there is none.

        A live entry becomes the most recently used and counts as a hit;
        otherwise a miss is counted.
        """
        entry = self._entries.get(key)
        if entry is not None:
            value, set_at = entry
            if not self._is_expired(set_at, self._clock()):
                self._entries.move_to_end(key)
                self._hits += 1
                return value
            del self._entries[key]
        self._misses += 1
        return default

    def delete(self, key: Hashable) -> bool:
        """Remove ``key``. Return True only if a live entry was removed."""
        entry = self._entries.pop(key, None)
        if entry is None:
            return False
        return not self._is_expired(entry[1], self._clock())

    def clear(self) -> None:
        """Remove all entries. Statistics are kept."""
        self._entries.clear()

    def stats(self) -> CacheStats:
        """Return a snapshot of the hit, miss and eviction counters."""
        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)

    def __len__(self) -> int:
        """Number of live entries. Does not affect statistics or recency."""
        if self._ttl is None:
            return len(self._entries)
        now = self._clock()
        return sum(1 for _, set_at in self._entries.values() if not self._is_expired(set_at, now))

    def __contains__(self, key: object) -> bool:
        """Whether ``key`` has a live entry. Does not affect statistics or recency."""
        entry = self._entries.get(key)
        return entry is not None and not self._is_expired(entry[1], self._clock())

    def _is_expired(self, set_at: float, now: float) -> bool:
        return self._ttl is not None and now - set_at >= self._ttl

    def _make_room(self, now: float) -> None:
        self._remove_expired(now)
        if len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
            self._evictions += 1

    def _remove_expired(self, now: float) -> None:
        if self._ttl is None:
            return
        expired = [key for key, (_, set_at) in self._entries.items() if self._is_expired(set_at, now)]
        for key in expired:
            del self._entries[key]


def memoize(cache: Cache) -> Callable[[F], F]:
    """Decorator factory caching a function's results in ``cache``.

    Results are keyed by the call's positional and keyword arguments, which
    must be hashable. Lookups go through ``cache.get``, so they count as hits
    and misses. ``None`` results are cached too. Exceptions are not cached.
    Each decorated function gets its own key space, so several functions can
    share one cache without their entries colliding.

    Usage::

        @memoize(cache)
        def load(user_id): ...
    """
    if not isinstance(cache, Cache):
        raise TypeError(
            f"memoize() expects a Cache instance, got {type(cache).__name__}; "
            "use it as @memoize(cache)"
        )

    def decorator(func: F) -> F:
        # A token only this function's keys contain, so its entries cannot
        # collide with another function's or with keys set on the cache directly.
        namespace = object()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (namespace, args, tuple(sorted(kwargs.items())))
            result = cache.get(key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def _require_positive_int(name: str, value: object) -> None:
    # bool is a subclass of int, but True/False as a size is almost certainly a mistake.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be an integer greater than 0, got {value!r}")


def _require_positive_number(name: str, value: object) -> None:
    # `not value > 0` also rejects NaN, which compares false with everything.
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not value > 0:
        raise ValueError(f"{name} must be None or a number greater than 0, got {value!r}")

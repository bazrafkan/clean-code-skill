"""In-memory cache with a size limit, optional expiry, hit statistics and memoization."""

from __future__ import annotations

import functools
import numbers
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any, TypeVar

__all__ = ["Cache", "CacheStats", "memoize"]

_MISSING = object()

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class CacheStats:
    """A snapshot of a cache's counters at the moment ``Cache.stats()`` was called."""

    hits: int
    misses: int
    evictions: int


class Cache:
    """A least-recently-used cache whose entries can optionally expire.

    Entries are kept in recency order: the first entry is the least recently used.
    Expired entries behave as if they were absent and are dropped lazily, whenever
    an operation comes across them.
    """

    def __init__(
        self,
        max_size: int,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size <= 0:
            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
        if ttl_seconds is not None and not _is_positive_number(ttl_seconds):
            raise ValueError(
                f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}"
            )
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")

        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        # key -> (value, time the entry was last set)
        self._entries: OrderedDict[Hashable, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def set(self, key: Hashable, value: Any) -> None:
        """Store ``value`` under ``key`` as the most recently used entry, restarting its expiry."""
        now = self._clock()
        if key not in self._entries:
            self._make_room(now)
        self._entries[key] = (value, now)
        self._entries.move_to_end(key)

    def get(self, key: Hashable, default: Any = None) -> Any:
        """Return the live value for ``key`` (a hit), or ``default`` if there is none (a miss)."""
        entry = self._live_entry(key)
        if entry is None:
            self._misses += 1
            return default
        self._entries.move_to_end(key)
        self._hits += 1
        return entry[0]

    def delete(self, key: Hashable) -> bool:
        """Remove ``key``. Return ``True`` only if it had a live entry."""
        entry = self._entries.pop(key, None)
        return entry is not None and not self._is_expired(entry, self._clock())

    def clear(self) -> None:
        """Remove every entry. The statistics are kept."""
        self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)

    def __len__(self) -> int:
        self._remove_expired(self._clock())
        return len(self._entries)

    def __contains__(self, key: Hashable) -> bool:
        return self._live_entry(key) is not None

    def _is_expired(self, entry: tuple[Any, float], now: float) -> bool:
        return self._ttl_seconds is not None and now - entry[1] >= self._ttl_seconds

    def _live_entry(self, key: Hashable) -> tuple[Any, float] | None:
        """Return the entry for ``key`` if it is live, dropping it if it has expired.

        Does not change recency order or statistics.
        """
        entry = self._entries.get(key)
        if entry is None:
            return None
        if self._is_expired(entry, self._clock()):
            del self._entries[key]
            return None
        return entry

    def _remove_expired(self, now: float) -> None:
        if self._ttl_seconds is None:
            return
        expired_keys = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
        for key in expired_keys:
            del self._entries[key]

    def _make_room(self, now: float) -> None:
        """Free a slot for a new key: drop expired entries first, then evict the LRU entry."""
        if len(self._entries) < self._max_size:
            return
        self._remove_expired(now)
        if len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
            self._evictions += 1


def memoize(cache: Cache) -> Callable[[F], F]:
    """Cache a function's results in ``cache``, keyed by its positional and keyword arguments.

    Lookups go through ``cache.get``, so they count as hits and misses. ``f(1)`` and
    ``f(x=1)`` are cached separately, as with ``functools.lru_cache``.
    """

    def decorator(func: F) -> F:
        # A private token per decorated function keeps its keys apart from those of other
        # functions, and from any keys set directly on the shared cache.
        namespace = object()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (namespace, args, frozenset(kwargs.items()))
            result = cache.get(key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def _is_positive_number(value: object) -> bool:
    # bool is a subclass of int but is not a meaningful duration; `value > 0` is False for NaN.
    return (
        not isinstance(value, bool)
        and isinstance(value, numbers.Real)
        and value > 0
    )

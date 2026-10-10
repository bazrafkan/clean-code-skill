"""An in-memory cache with a size limit, optional expiry, hit statistics and memoization."""

import functools
import numbers
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any

_MISSING = object()


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    evictions: int


@dataclass(frozen=True, slots=True)
class _Entry:
    value: Any
    set_at: float


class Cache:
    """A least-recently-used cache whose entries optionally expire ``ttl_seconds`` after they were last set.

    Expired entries behave as if they were absent.
    """

    def __init__(
        self,
        max_size: int,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not _is_positive_integer(max_size):
            raise ValueError(f"max_size must be an integer greater than 0, got {max_size!r}")
        if ttl_seconds is not None and not _is_positive_number(ttl_seconds):
            raise ValueError(f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}")
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[Hashable, _Entry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def set(self, key: Hashable, value: Any) -> None:
        """Store ``value`` as the most recently used entry and restart its expiry.

        Adding a new key to a full cache first removes expired entries, then evicts the least recently used one.
        """
        now = self._clock()
        if key not in self._entries and self._is_full():
            self._make_room(now)
        self._entries[key] = _Entry(value, set_at=now)
        self._entries.move_to_end(key)

    def get(self, key: Hashable, default: Any = None) -> Any:
        """Return the live value for ``key`` and mark it most recently used, or ``default`` if there is none."""
        entry = self._live_entry(key, self._clock())
        if entry is None:
            self._misses += 1
            return default
        self._entries.move_to_end(key)
        self._hits += 1
        return entry.value

    def delete(self, key: Hashable) -> bool:
        """Remove ``key`` and return whether it had a live entry."""
        entry = self._entries.pop(key, None)
        return entry is not None and not self._is_expired(entry, self._clock())

    def clear(self) -> None:
        """Remove all entries, keeping the statistics."""
        self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)

    def __len__(self) -> int:
        now = self._clock()
        return sum(1 for entry in self._entries.values() if not self._is_expired(entry, now))

    def __contains__(self, key: object) -> bool:
        return self._live_entry(key, self._clock()) is not None

    def _is_full(self) -> bool:
        return len(self._entries) >= self._max_size

    def _make_room(self, now: float) -> None:
        self._remove_expired(now)
        if self._is_full():
            self._entries.popitem(last=False)
            self._evictions += 1

    def _remove_expired(self, now: float) -> None:
        expired_keys = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
        for key in expired_keys:
            del self._entries[key]

    def _live_entry(self, key: object, now: float) -> _Entry | None:
        entry = self._entries.get(key)
        if entry is None or self._is_expired(entry, now):
            return None
        return entry

    def _is_expired(self, entry: _Entry, now: float) -> bool:
        return self._ttl_seconds is not None and now - entry.set_at >= self._ttl_seconds


def memoize(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache a function's results in ``cache``, keyed by its positional and keyword arguments.

    The arguments must be hashable. Several functions can share one cache.
    """

    def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # The function is part of the key so that functions sharing a cache never collide.
            call_key = (func, args, frozenset(kwargs.items()))
            result = cache.get(call_key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(call_key, result)
            return result

        return wrapper

    return decorate


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, numbers.Integral) and not isinstance(value, bool) and value > 0


def _is_positive_number(value: object) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool) and value > 0

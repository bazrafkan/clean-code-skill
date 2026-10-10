"""In-memory cache with a size limit, optional expiry, hit statistics and memoization."""

import functools
import numbers
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any


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
    """Least-recently-used cache holding at most `max_size` entries.

    With `ttl_seconds`, an entry expires once that many seconds have passed
    since it was last set; expired entries behave as if they were absent.
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
            raise ValueError(
                f"ttl_seconds must be None or a number greater than 0, got {ttl_seconds!r}"
            )
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
        now = self._clock()
        if key not in self._entries and len(self._entries) >= self._max_size:
            self._make_room(now)
        self._entries[key] = _Entry(value, set_at=now)
        self._entries.move_to_end(key)

    def get(self, key: Hashable, default: Any = None) -> Any:
        entry = self._find_live_entry(key, self._clock())
        if entry is None:
            self._misses += 1
            return default
        self._hits += 1
        self._entries.move_to_end(key)
        return entry.value

    def delete(self, key: Hashable) -> bool:
        """Remove `key`; return True only if it had a live entry."""
        entry = self._entries.pop(key, None)
        return entry is not None and not self._is_expired(entry, self._clock())

    def clear(self) -> None:
        self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(hits=self._hits, misses=self._misses, evictions=self._evictions)

    def __len__(self) -> int:
        now = self._clock()
        return sum(1 for entry in self._entries.values() if not self._is_expired(entry, now))

    def __contains__(self, key: Hashable) -> bool:
        return self._find_live_entry(key, self._clock()) is not None

    def _make_room(self, now: float) -> None:
        self._remove_expired(now)
        if len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
            self._evictions += 1

    def _remove_expired(self, now: float) -> None:
        expired_keys = [key for key, entry in self._entries.items() if self._is_expired(entry, now)]
        for key in expired_keys:
            del self._entries[key]

    def _find_live_entry(self, key: Hashable, now: float) -> _Entry | None:
        entry = self._entries.get(key)
        if entry is None or self._is_expired(entry, now):
            return None
        return entry

    def _is_expired(self, entry: _Entry, now: float) -> bool:
        return self._ttl_seconds is not None and now - entry.set_at >= self._ttl_seconds


# Distinguishes "not cached" from a cached result of None.
_MISSING = object()


def memoize(cache: Cache) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache a function's results in `cache`, keyed by the function and its arguments."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Hashable, **kwargs: Hashable) -> Any:
            key = (func, args, frozenset(kwargs.items()))
            result = cache.get(key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        return wrapper

    return decorator


def _is_positive_integer(value: object) -> bool:
    return isinstance(value, numbers.Integral) and not isinstance(value, bool) and value > 0


def _is_positive_number(value: object) -> bool:
    # `value > 0` is False for NaN, so NaN is rejected too.
    return isinstance(value, numbers.Real) and not isinstance(value, bool) and value > 0

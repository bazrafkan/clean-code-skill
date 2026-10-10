"""In-memory LRU cache with optional expiry, hit statistics and memoization."""

import functools
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    evictions: int


@dataclass(frozen=True)
class _Entry:
    value: Any
    set_at: float


class Cache:
    """A least-recently-used cache whose entries can expire.

    An entry expires once ``ttl_seconds`` or more have passed since it was last set.
    Expired entries behave as if they were absent.
    """

    def __init__(
        self,
        max_size: int,
        ttl_seconds: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not _is_positive_number(max_size, Integral):
            raise ValueError(
                f"max_size must be an integer greater than 0, got {max_size!r}"
            )
        if ttl_seconds is not None and not _is_positive_number(ttl_seconds, Real):
            raise ValueError(
                "ttl_seconds must be None or a number greater than 0, "
                f"got {ttl_seconds!r}"
            )
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[Hashable, _Entry] = OrderedDict()  # LRU first
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def set(self, key: Hashable, value: Any) -> None:
        """Store ``value``, restart its expiry and make it the most recently used.

        Adding a new key to a full cache first removes expired entries, then evicts
        the least recently used entry if there is still no room.
        """
        now = self._clock()
        if key not in self._entries and self._is_full():
            self._make_room(now)
        self._entries[key] = _Entry(value, set_at=now)
        self._entries.move_to_end(key)

    def get(self, key: Hashable, default: Any = None) -> Any:
        """Return the live value for ``key`` and make it the most recently used.

        Returns ``default`` if the key is absent or expired.
        """
        if key not in self:
            self._misses += 1
            return default
        self._hits += 1
        self._entries.move_to_end(key)
        return self._entries[key].value

    def delete(self, key: Hashable) -> bool:
        """Remove ``key`` and return whether a live entry was removed."""
        was_live = key in self
        self._entries.pop(key, None)
        return was_live

    def clear(self) -> None:
        """Remove all entries. The statistics are kept."""
        self._entries.clear()

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._hits, misses=self._misses, evictions=self._evictions
        )

    def __len__(self) -> int:
        now = self._clock()
        return sum(
            1 for entry in self._entries.values() if not self._is_expired(entry, now)
        )

    def __contains__(self, key: Hashable) -> bool:
        entry = self._entries.get(key)
        return entry is not None and not self._is_expired(entry, self._clock())

    def _is_full(self) -> bool:
        return len(self._entries) >= self._max_size

    def _make_room(self, now: float) -> None:
        self._remove_expired(now)
        if self._is_full():
            self._entries.popitem(last=False)
            self._evictions += 1

    def _remove_expired(self, now: float) -> None:
        expired_keys = [
            key for key, entry in self._entries.items() if self._is_expired(entry, now)
        ]
        for key in expired_keys:
            del self._entries[key]

    def _is_expired(self, entry: _Entry, now: float) -> bool:
        if self._ttl_seconds is None:
            return False
        return now - entry.set_at >= self._ttl_seconds


_MISSING = object()


def memoize(
    cache: Cache,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Cache a function's results in ``cache``, keyed by the function and its arguments.

    Including the function in the key lets several functions share one cache.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (func, args, frozenset(kwargs.items()))
            result = cache.get(key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        return wrapper

    return decorator


def _is_positive_number(value: object, number_type: type) -> bool:
    # bool is a subclass of int, but True is not a meaningful size or duration.
    is_number = isinstance(value, number_type) and not isinstance(value, bool)
    return is_number and value > 0

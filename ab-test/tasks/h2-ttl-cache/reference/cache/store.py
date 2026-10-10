"""In-memory cache with a size limit, optional expiry, hit statistics and memoization."""

import functools
import time
from collections import OrderedDict
from dataclasses import dataclass

_MISSING = object()


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    evictions: int


class Cache:
    """Least-recently-used cache whose entries can expire `ttl_seconds` after they were set."""

    def __init__(self, max_size, ttl_seconds=None, clock=time.monotonic):
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("max_size must be an integer greater than 0")
        if ttl_seconds is not None and (isinstance(ttl_seconds, bool) or not ttl_seconds > 0):
            raise ValueError("ttl_seconds must be None or a number greater than 0")
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries = OrderedDict()  # key -> (value, set_at), least recently used first
        self._hits = self._misses = self._evictions = 0

    def set(self, key, value):
        if key in self._entries:
            self._entries.move_to_end(key)
        elif len(self._entries) >= self._max_size:
            self._make_room()
        self._entries[key] = (value, self._clock())

    def get(self, key, default=None):
        if not self._is_live(key):
            self._misses += 1
            return default
        self._hits += 1
        self._entries.move_to_end(key)
        return self._entries[key][0]

    def delete(self, key):
        was_live = self._is_live(key)
        self._entries.pop(key, None)
        return was_live

    def clear(self):
        self._entries.clear()

    def stats(self):
        return CacheStats(self._hits, self._misses, self._evictions)

    def __len__(self):
        return sum(1 for key in list(self._entries) if self._is_live(key))

    def __contains__(self, key):
        return self._is_live(key)

    def _is_live(self, key):
        """True if `key` has an unexpired entry; drops the entry if it has expired."""
        entry = self._entries.get(key)
        if entry is None:
            return False
        if self._ttl is not None and self._clock() - entry[1] >= self._ttl:
            del self._entries[key]
            return False
        return True

    def _make_room(self):
        for key in list(self._entries):
            self._is_live(key)
        if len(self._entries) >= self._max_size:
            self._entries.popitem(last=False)
            self._evictions += 1


def memoize(cache):
    """Cache a function's results in `cache`, keyed by the function and its arguments."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (func, args, frozenset(kwargs.items()))
            result = cache.get(key, _MISSING)
            if result is _MISSING:
                result = func(*args, **kwargs)
                cache.set(key, result)
            return result

        return wrapper

    return decorator

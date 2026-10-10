Create `cache/store.py` with an in-memory cache that has a size limit, optional expiry, hit statistics and a memoizing decorator.

`Cache(max_size, ttl_seconds=None, clock=time.monotonic)`
- `max_size` is the maximum number of entries. It must be an integer greater than 0.
- `ttl_seconds` is how long an entry lives after it was last set. `None` means entries never expire. Otherwise it must be a number greater than 0.
- `clock` is a zero-argument callable that returns the current time in seconds.
- Invalid arguments raise `ValueError`.
- An entry is expired once `ttl_seconds` or more have passed since it was last set. Expired entries behave as if they were absent.

Methods:
- `set(key, value)` stores the value, replacing any previous one, restarts its expiry, and makes it the most recently used entry. When a new key is added to a full cache, expired entries are removed first. If the cache is still full, the least recently used entry is evicted.
- `get(key, default=None)` returns the value and makes the entry the most recently used, counting a hit. If the key is absent or expired, it returns `default` and counts a miss.
- `delete(key)` removes the key. It returns `True` if a live entry was removed, otherwise `False`.
- `clear()` removes all entries. It does not reset the statistics.
- `len(cache)` is the number of live entries, and `key in cache` tells whether a key has a live entry. Neither counts as a hit or a miss, nor changes which entry is least recently used.
- `stats()` returns an object with integer attributes `hits`, `misses` and `evictions`. `evictions` counts only entries removed to make room, not expired or deleted ones.

`memoize(cache)` is a decorator factory. `@memoize(cache)` caches a function's results by its positional and keyword arguments, which you can assume are hashable.
- It uses the cache's normal lookup, so hits and misses are counted.
- Results are cached even when they are `None`.
- Several functions can share one cache without their entries colliding.

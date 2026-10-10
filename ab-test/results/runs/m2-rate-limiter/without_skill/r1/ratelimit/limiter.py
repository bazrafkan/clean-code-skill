"""Token-bucket rate limiting and a client wrapper that enforces it."""

import math
import threading
import time
from numbers import Real

# Absorbs float rounding in the refill arithmetic (for example 0.1 + 0.2 seconds
# times a rate of 10 giving 2.9999999999999996 tokens instead of 3).
_ROUNDING_TOLERANCE = 1e-9


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


class TokenBucket:
    """A bucket of up to `capacity` tokens, refilled at `refill_rate` tokens per second.

    The bucket starts full. Refill is computed from elapsed `clock` time on each
    acquisition, so no background thread is needed. Instances are safe to share
    between threads.
    """

    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        if not _is_int(capacity) or capacity <= 0:
            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
        if not _is_real(refill_rate) or not math.isfinite(refill_rate) or refill_rate <= 0:
            raise ValueError(f"refill_rate must be a finite number greater than 0, got {refill_rate!r}")
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._lock = threading.Lock()
        self._tokens = float(capacity)
        self._updated_at = clock()

    @property
    def capacity(self):
        return self._capacity

    @property
    def refill_rate(self):
        return self._refill_rate

    def try_acquire(self, tokens=1):
        """Consume `tokens` and return True if they are available, otherwise return False."""
        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
            raise ValueError(
                f"tokens must be an integer between 1 and {self._capacity}, got {tokens!r}"
            )

        with self._lock:
            now = self._clock()
            available = self._available_at(now)
            if available + _ROUNDING_TOLERANCE < tokens:
                # State is left untouched so repeated failed attempts do not
                # accumulate rounding error in the stored token count.
                return False
            self._tokens = max(0.0, available - tokens)
            self._updated_at = max(self._updated_at, now)
            return True

    def _available_at(self, now):
        # A clock that steps backwards must not drain the bucket.
        elapsed = max(0.0, now - self._updated_at)
        return min(float(self._capacity), self._tokens + elapsed * self._refill_rate)


class RateLimitedClient:
    """Forwards `send` calls to a wrapped client, one bucket token per request."""

    def __init__(self, client, bucket):
        self._client = client
        self._bucket = bucket

    def send(self, request):
        """Send `request` through the wrapped client, or raise RateLimitExceeded."""
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded: no token available")
        return self._client.send(request)


def _is_int(value):
    # bool is a subclass of int, but True/False are not meaningful counts.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_real(value):
    return isinstance(value, Real) and not isinstance(value, bool)

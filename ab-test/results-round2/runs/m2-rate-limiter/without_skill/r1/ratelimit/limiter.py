"""Token-bucket rate limiting and a client wrapper that enforces it."""

import math
import numbers
import threading
import time

# Tolerance for float rounding in refill arithmetic, so that e.g. 0.1 s at
# 10 tokens/s reliably yields a whole token rather than 0.9999999999999999.
_EPSILON = 1e-9


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


def _is_int(value):
    return isinstance(value, numbers.Integral) and not isinstance(value, bool)


def _is_real(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


class TokenBucket:
    """A thread-safe token bucket that refills continuously with clock time.

    The bucket starts full. Each call to ``try_acquire`` first credits the
    tokens earned since the previous call (capped at ``capacity``), then
    either consumes the requested tokens or leaves the bucket untouched.
    """

    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        if not _is_int(capacity) or capacity <= 0:
            raise ValueError(f"capacity must be an integer > 0, got {capacity!r}")
        if not _is_real(refill_rate) or not math.isfinite(refill_rate) or refill_rate <= 0:
            raise ValueError(f"refill_rate must be a finite number > 0, got {refill_rate!r}")
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()

    @property
    def capacity(self):
        return self._capacity

    @property
    def refill_rate(self):
        return self._refill_rate

    def try_acquire(self, tokens=1):
        """Consume ``tokens`` and return True if available, else return False.

        ``tokens`` must be an integer between 1 and ``capacity`` inclusive;
        anything else raises ``ValueError`` because it could never succeed.
        """
        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
            raise ValueError(
                f"tokens must be an integer between 1 and {self._capacity}, got {tokens!r}"
            )

        with self._lock:
            self._refill()
            if self._tokens + _EPSILON < tokens:
                return False
            self._tokens = max(0.0, self._tokens - tokens)
            return True

    def _refill(self):
        now = self._clock()
        # A clock that steps backwards earns nothing; keeping the later
        # timestamp avoids crediting the same interval twice.
        if now <= self._last_refill:
            return
        earned = (now - self._last_refill) * self._refill_rate
        self._tokens = min(float(self._capacity), self._tokens + earned)
        self._last_refill = now


class RateLimitedClient:
    """Wraps an object with a ``send(request)`` method and rate-limits it.

    Each call to ``send`` costs one token from ``bucket``. A token spent on a
    request is not refunded if the wrapped client raises.
    """

    def __init__(self, client, bucket):
        if not callable(getattr(client, "send", None)):
            raise TypeError(f"client must have a callable send(request) method, got {client!r}")
        self._client = client
        self._bucket = bucket

    def send(self, request):
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded: no token available")
        return self._client.send(request)

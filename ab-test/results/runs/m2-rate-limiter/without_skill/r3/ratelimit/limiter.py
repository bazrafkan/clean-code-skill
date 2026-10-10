"""Token-bucket rate limiting and a client wrapper that enforces it."""

import math
import threading
import time
from numbers import Integral, Real

# Slack used when checking whether enough tokens are available. Without it,
# refills that should add up to a whole token can fall just short because of
# float rounding (for example, ten 0.1 s clock steps at 1 token per second).
_FLOAT_TOLERANCE = 1e-9


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


class TokenBucket:
    """A thread-safe token bucket.

    The bucket holds at most ``capacity`` tokens and starts full. Tokens are
    added continuously at ``refill_rate`` tokens per second of ``clock`` time.
    """

    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        if not _is_int(capacity) or capacity <= 0:
            raise ValueError(
                f"capacity must be an integer greater than 0, got {capacity!r}"
            )
        if not _is_positive_finite_number(refill_rate):
            raise ValueError(
                f"refill_rate must be a finite number greater than 0, got {refill_rate!r}"
            )
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")

        self._capacity = capacity
        self._refill_rate = float(refill_rate)
        self._clock = clock
        self._tokens = float(capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()

    def try_acquire(self, tokens=1):
        """Consume ``tokens`` and return True, or return False and consume nothing.

        ``tokens`` must be an integer from 1 to ``capacity``; anything else
        raises ValueError, because such a request could never be satisfied.
        """
        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
            raise ValueError(
                f"tokens must be an integer from 1 to {self._capacity}, got {tokens!r}"
            )

        with self._lock:
            self._refill()
            if self._tokens + _FLOAT_TOLERANCE < tokens:
                return False
            self._tokens = max(0.0, self._tokens - tokens)
            return True

    def _refill(self):
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            # A clock that stalls or steps backwards adds nothing. Keeping the
            # later timestamp stops the same interval from being credited twice.
            return
        self._tokens = min(
            float(self._capacity), self._tokens + elapsed * self._refill_rate
        )
        self._last_refill = now


class RateLimitedClient:
    """Wraps an object with a ``send(request)`` method and rate-limits its calls.

    Each call to ``send`` takes one token from ``bucket``. The token is spent
    even if the wrapped client then raises, since the request was attempted.
    """

    def __init__(self, client, bucket):
        self._client = client
        self._bucket = bucket

    def send(self, request):
        """Forward ``request`` to the wrapped client and return its result.

        Raises RateLimitExceeded, without calling the client, if no token is
        available.
        """
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded; the request was not sent")
        return self._client.send(request)


def _is_int(value):
    # bool is a subclass of int, but True/False are not meaningful counts.
    return isinstance(value, Integral) and not isinstance(value, bool)


def _is_positive_finite_number(value):
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and value > 0
        and math.isfinite(value)
    )

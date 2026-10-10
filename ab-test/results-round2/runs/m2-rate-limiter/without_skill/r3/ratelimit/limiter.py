"""Token-bucket rate limiting and a client wrapper that enforces it."""

import math
import numbers
import threading
import time

# Refill arithmetic is done in floats, so a bucket that should hold exactly
# one token can hold 0.9999999999999998. This tolerance absorbs that drift so
# a token that is due is not rejected.
_TOLERANCE = 1e-9


class RateLimitExceeded(Exception):
    """Raised by RateLimitedClient.send when the bucket has no token left."""


class TokenBucket:
    """A thread-safe token bucket.

    The bucket holds at most ``capacity`` tokens and starts full. Tokens are
    added continuously at ``refill_rate`` per second of elapsed ``clock`` time.
    """

    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        if not _is_integer(capacity) or capacity <= 0:
            raise ValueError(
                f"capacity must be an integer greater than 0, got {capacity!r}"
            )
        if not callable(clock):
            raise ValueError(f"clock must be a callable, got {clock!r}")

        self._capacity = int(capacity)
        self._refill_rate = _positive_finite_rate(refill_rate)
        self._clock = clock
        self._tokens = float(self._capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()

    def try_acquire(self, tokens=1):
        """Consume ``tokens`` and return True, or return False and consume nothing."""
        if not _is_integer(tokens) or not 1 <= tokens <= self._capacity:
            raise ValueError(
                f"tokens must be an integer from 1 to {self._capacity}, got {tokens!r}"
            )
        with self._lock:
            self._refill()
            if self._tokens + _TOLERANCE < tokens:
                return False
            self._tokens = max(0.0, self._tokens - tokens)
            return True

    def _refill(self):
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            # A clock that stalls or steps backwards must never remove tokens,
            # and keeping the later timestamp avoids crediting time twice.
            return
        self._tokens = min(
            float(self._capacity), self._tokens + elapsed * self._refill_rate
        )
        self._last_refill = now


class RateLimitedClient:
    """Forwards ``send`` to a wrapped client, spending one bucket token per call.

    A token is spent as soon as the call is let through, so a call that the
    wrapped client then fails still counts against the limit.
    """

    def __init__(self, client, bucket):
        if not callable(getattr(client, "send", None)):
            raise TypeError("client must have a callable send(request) method")
        if not callable(getattr(bucket, "try_acquire", None)):
            raise TypeError("bucket must have a callable try_acquire() method")
        self._client = client
        self._bucket = bucket

    def send(self, request):
        """Return ``client.send(request)``, or raise RateLimitExceeded if no token is free."""
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded: no token available")
        return self._client.send(request)


def _is_integer(value):
    # bool is a subclass of int, but True is not a meaningful token count.
    return isinstance(value, numbers.Integral) and not isinstance(value, bool)


def _positive_finite_rate(value):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"refill_rate must be a number, got {value!r}")
    try:
        rate = float(value)
    except OverflowError:
        rate = math.inf
    # NaN fails "rate > 0", and infinity would turn a zero elapsed time into NaN.
    if not (rate > 0 and math.isfinite(rate)):
        raise ValueError(
            f"refill_rate must be a finite number greater than 0, got {value!r}"
        )
    return rate

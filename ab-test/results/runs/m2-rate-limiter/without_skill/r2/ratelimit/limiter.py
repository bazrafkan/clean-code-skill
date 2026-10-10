"""Token-bucket rate limiting and a client wrapper that enforces it."""

import math
import threading
import time
from collections.abc import Callable
from numbers import Real
from typing import Any, Protocol

# Refilling adds small float amounts over many calls, so the total can land a
# hair short of a whole token (ten refills of 0.1 sum to 0.9999999999999999).
# Amounts this close to the request count as enough, so such requests still pass.
_FLOAT_TOLERANCE = 1e-9


class RateLimitExceeded(Exception):
    """Raised when a request is refused because no token is available."""


class SupportsSend(Protocol):
    def send(self, request: Any) -> Any: ...


def _is_real_number(value: object) -> bool:
    # bool is a subclass of int, but True/False are never meant as quantities.
    return isinstance(value, Real) and not isinstance(value, bool)


class TokenBucket:
    """A bucket of up to `capacity` tokens, refilled at `refill_rate` tokens per second.

    The bucket starts full. It is safe to share between threads.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
        if not _is_real_number(refill_rate) or not math.isfinite(refill_rate) or refill_rate <= 0:
            raise ValueError(f"refill_rate must be a finite number greater than 0, got {refill_rate!r}")
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")

        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()

    def try_acquire(self, tokens: float = 1) -> bool:
        """Consume `tokens` and return True if enough are available; otherwise consume nothing and return False."""
        if not _is_real_number(tokens) or not 1 <= tokens <= self._capacity:
            raise ValueError(f"tokens must be between 1 and capacity ({self._capacity}), got {tokens!r}")

        with self._lock:
            self._refill()
            if not self._has_at_least(tokens):
                return False
            self._tokens = max(0.0, self._tokens - tokens)
            return True

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        # A clock that stalls or steps backwards must neither drain the bucket
        # nor move the reference point back (which would over-refill later).
        if elapsed <= 0:
            return
        self._tokens = min(float(self._capacity), self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def _has_at_least(self, tokens: float) -> bool:
        return self._tokens >= tokens or math.isclose(self._tokens, tokens, rel_tol=_FLOAT_TOLERANCE)


class RateLimitedClient:
    """Forwards `send` calls to `client` only while `bucket` has a token to spend."""

    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request: Any) -> Any:
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded; the request was not sent")
        return self._client.send(request)

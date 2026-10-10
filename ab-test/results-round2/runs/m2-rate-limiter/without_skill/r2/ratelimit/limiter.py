"""Token-bucket rate limiting and a client wrapper that enforces it."""

from __future__ import annotations

import math
import threading
import time
from numbers import Integral, Real
from typing import Any, Callable, Protocol


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


class TokenBucket:
    """A thread-safe token bucket.

    The bucket holds at most ``capacity`` tokens and starts full. Tokens are
    added continuously at ``refill_rate`` tokens per second of elapsed
    ``clock`` time, never exceeding ``capacity``. If the clock moves
    backwards, no tokens are added until it passes its latest reading again.
    """

    # Clock readings are floats, so a refill can land a hair below a whole
    # token (ten steps of 0.1 s add up to 0.9999999999999999 s). Count such
    # near-misses as available instead of rejecting them.
    _TOLERANCE = 1e-9

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not _is_int(capacity) or capacity <= 0:
            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
        if not _is_positive_finite(refill_rate):
            raise ValueError(f"refill_rate must be a finite number greater than 0, got {refill_rate!r}")
        if not callable(clock):
            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")

        self._capacity = int(capacity)
        self._refill_rate = float(refill_rate)
        self._clock = clock
        self._tokens = float(self._capacity)
        self._last_refill = clock()
        self._lock = threading.Lock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Consume ``tokens`` and return True, or return False and consume nothing."""
        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
            raise ValueError(
                f"tokens must be an integer between 1 and {self._capacity}, got {tokens!r}"
            )
        with self._lock:
            self._refill()
            if self._tokens + self._TOLERANCE < tokens:
                return False
            self._tokens = max(0.0, self._tokens - tokens)
            return True

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_refill = now


class SupportsSend(Protocol):
    def send(self, request: Any) -> Any: ...


class RateLimitedClient:
    """Forwards ``send`` calls to a client while the bucket has tokens."""

    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request: Any) -> Any:
        """Send ``request`` through the client, or raise RateLimitExceeded without sending."""
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded; request was not sent")
        return self._client.send(request)


def _is_int(value: object) -> bool:
    # bool is an Integral subclass, but True/False are not meaningful counts.
    return isinstance(value, Integral) and not isinstance(value, bool)


def _is_positive_finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    # NaN fails both comparisons, so it is rejected here too.
    return 0 < value < math.inf

"""Token-bucket rate limiting and a client wrapper that enforces it."""

import math
import numbers
import threading
import time
from collections.abc import Callable
from typing import Any, Protocol


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available for it."""


class TokenBucket:
    """Admits work at a sustained rate, with bursts of up to ``capacity`` tokens.

    The bucket starts full and refills continuously at ``refill_rate`` tokens per
    second of ``clock`` time. One instance can be shared between threads.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not _is_positive_integer(capacity):
            raise ValueError(
                f"capacity must be an integer greater than 0, got {capacity!r}"
            )
        if not _is_positive_finite_number(refill_rate):
            raise ValueError(
                "refill_rate must be a finite number greater than 0, "
                f"got {refill_rate!r}"
            )
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._tokens: float = capacity
        self._last_refill = clock()
        self._lock = threading.Lock()

    def try_acquire(self, tokens: float = 1) -> bool:
        """Consume ``tokens`` and return True, or return False and consume nothing.

        Raises ValueError unless ``1 <= tokens <= capacity``.
        """
        if not 1 <= tokens <= self._capacity:
            raise ValueError(
                f"tokens must be between 1 and capacity ({self._capacity}), "
                f"got {tokens!r}"
            )
        with self._lock:
            self._refill()
            if self._tokens < tokens:
                return False
            self._tokens -= tokens
            return True

    def _refill(self) -> None:
        now = self._clock()
        # An injected clock may step backwards (time.time can); that must not drain
        # tokens. The re-counted time afterwards is harmless: refill caps at capacity.
        elapsed = max(0.0, now - self._last_refill)
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now


class SupportsSend(Protocol):
    """Any client that can send a request and return its result."""

    def send(self, request: Any) -> Any: ...


class RateLimitedClient:
    """Forwards ``send`` calls to a client only while the bucket has a token."""

    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request: Any) -> Any:
        """Return ``client.send(request)`` if a token is available.

        Raises RateLimitExceeded, without calling the client, when none is.
        """
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded: the request was not sent")
        return self._client.send(request)


def _is_positive_integer(value: object) -> bool:
    is_integer = isinstance(value, numbers.Integral) and not isinstance(value, bool)
    return is_integer and value > 0


def _is_positive_finite_number(value: object) -> bool:
    is_number = isinstance(value, numbers.Real) and not isinstance(value, bool)
    return is_number and math.isfinite(value) and value > 0

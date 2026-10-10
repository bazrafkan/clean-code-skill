"""Token-bucket rate limiting, and a client wrapper that enforces it."""

import math
import numbers
import threading
import time
from collections.abc import Callable
from typing import Generic, Protocol, TypeVar

RequestT_contra = TypeVar("RequestT_contra", contravariant=True)
ResponseT_co = TypeVar("ResponseT_co", covariant=True)


class TokenBucket:
    """A token-bucket rate limiter.

    Holds at most ``capacity`` tokens and starts full. Tokens refill continuously
    at ``refill_rate`` tokens per second, measured with ``clock`` (seconds).
    Safe to share between threads.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        _validate_bucket_arguments(capacity, refill_rate, clock)
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._lock = threading.Lock()
        self._available_tokens: float = capacity
        self._last_refill_time = clock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Consume ``tokens`` and return True if that many are available.

        Otherwise return False and consume nothing. Raises ValueError unless
        ``tokens`` is an integer from 1 to ``capacity``.
        """
        if not (_is_integer(tokens) and 1 <= tokens <= self._capacity):
            raise ValueError(
                f"tokens must be an integer from 1 to capacity ({self._capacity}), "
                f"got {tokens!r}"
            )
        with self._lock:
            self._refill()
            if self._available_tokens < tokens:
                return False
            self._available_tokens -= tokens
            return True

    def _refill(self) -> None:
        now = self._clock()
        # An injected clock may step backwards; that must add nothing, not drain tokens.
        elapsed_seconds = max(0.0, now - self._last_refill_time)
        self._available_tokens = min(
            self._capacity,
            self._available_tokens + elapsed_seconds * self._refill_rate,
        )
        self._last_refill_time = now


def _validate_bucket_arguments(
    capacity: int, refill_rate: float, clock: Callable[[], float]
) -> None:
    if not (_is_integer(capacity) and capacity > 0):
        raise ValueError(
            f"capacity must be an integer greater than 0, got {capacity!r}"
        )
    if not (_is_real(refill_rate) and math.isfinite(refill_rate) and refill_rate > 0):
        raise ValueError(
            f"refill_rate must be a finite number greater than 0, got {refill_rate!r}"
        )
    if not callable(clock):
        # The contract is ValueError for every invalid argument, wrong types included.
        message = f"clock must be a zero-argument callable, got {clock!r}"
        raise ValueError(message)  # noqa: TRY004


def _is_integer(value: object) -> bool:
    # bool is an int subclass, but True/False as a count is almost always a bug.
    return isinstance(value, numbers.Integral) and not isinstance(value, bool)


def _is_real(value: object) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no rate-limit token is available."""


class SupportsSend(Protocol[RequestT_contra, ResponseT_co]):
    def send(self, request: RequestT_contra, /) -> ResponseT_co: ...


class RateLimitedClient(Generic[RequestT_contra, ResponseT_co]):
    """Wraps a client so that every ``send`` must first take a token from ``bucket``."""

    def __init__(
        self,
        client: SupportsSend[RequestT_contra, ResponseT_co],
        bucket: TokenBucket,
    ) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request: RequestT_contra) -> ResponseT_co:
        """Forward ``request`` to the wrapped client and return its result.

        Raises RateLimitExceeded, without calling the client, when no token is
        available. The token is spent even if the client then fails.
        """
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded: request was not sent")
        return self._client.send(request)

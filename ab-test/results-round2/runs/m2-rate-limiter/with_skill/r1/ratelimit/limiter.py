"""Token-bucket rate limiting, and a client wrapper that applies it to sends."""

import time
from typing import Callable


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


class TokenBucket:
    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` tokens per second.

    The bucket starts full. `clock` returns the current time in seconds.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
        if refill_rate <= 0:
            raise ValueError(f"refill_rate must be greater than 0, got {refill_rate!r}")
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._available_tokens: float = capacity
        self._last_refill_time = clock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Consume `tokens` and return True if enough are available.

        Otherwise consume nothing and return False.
        """
        if not 1 <= tokens <= self._capacity:
            raise ValueError(f"tokens must be between 1 and {self._capacity}, got {tokens!r}")
        self._refill()
        if self._available_tokens < tokens:
            return False
        self._available_tokens -= tokens
        return True

    def _refill(self) -> None:
        now = self._clock()
        elapsed_seconds = now - self._last_refill_time
        self._available_tokens = min(
            self._capacity,
            self._available_tokens + elapsed_seconds * self._refill_rate,
        )
        self._last_refill_time = now


class RateLimitedClient:
    """Wraps any object with a `send(request)` method, sending only while `bucket` has tokens."""

    def __init__(self, client, bucket: TokenBucket) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request):
        """Forward `request` to the wrapped client and return its result.

        Raises RateLimitExceeded, without calling the client, when no token is available.
        """
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("rate limit exceeded: no token available, request not sent")
        return self._client.send(request)

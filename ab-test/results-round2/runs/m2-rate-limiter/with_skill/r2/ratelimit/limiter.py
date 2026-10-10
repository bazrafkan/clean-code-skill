"""Token-bucket rate limiting, and a client wrapper that enforces it."""

import time
from collections.abc import Callable


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


class TokenBucket:
    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` per second.

    `clock` must return the current time in seconds. The bucket starts full.
    Raises ValueError if `capacity` is not an integer > 0 or `refill_rate` is not > 0.
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
        self._tokens: float = capacity
        self._last_refill_time = clock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Consume `tokens` and return True if enough are available.

        Otherwise consume nothing and return False.
        Raises ValueError unless 1 <= `tokens` <= capacity.
        """
        if not 1 <= tokens <= self._capacity:
            raise ValueError(f"tokens must be between 1 and {self._capacity}, got {tokens!r}")
        self._refill()
        if self._tokens < tokens:
            return False
        self._tokens -= tokens
        return True

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill_time
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill_time = now


class RateLimitedClient:
    """Forwards `send` to the wrapped client only while `bucket` has a token."""

    def __init__(self, client, bucket: TokenBucket) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request):
        """Return `client.send(request)`, or raise RateLimitExceeded without calling the client."""
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("no token available; request was not sent")
        return self._client.send(request)

"""Token-bucket rate limiting, and a client wrapper that enforces it."""

import time
from collections.abc import Callable
from typing import Any, Protocol

__all__ = ["RateLimitExceeded", "RateLimitedClient", "SupportsSend", "TokenBucket"]

# Float clock arithmetic can come up a hair short (0.3 - 0.2 < 0.1), which would
# deny a token to a caller that waited exactly long enough. Shortfalls this small
# are ignored.
_ROUNDING_TOLERANCE = 1e-9


class RateLimitExceeded(Exception):
    """Raised when a request is rejected because no token is available."""


class TokenBucket:
    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` per second.

    Not thread-safe: guard a shared instance with a lock.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a full bucket. `clock()` must return the current time in seconds.

        Raise ValueError unless `capacity` is an integer > 0, `refill_rate` is a
        number > 0 and `clock` is callable.
        """
        if not _is_positive_int(capacity):
            raise ValueError(
                f"capacity must be an integer greater than 0, got {capacity!r}"
            )
        if not _is_positive_number(refill_rate):
            raise ValueError(
                f"refill_rate must be a number greater than 0, got {refill_rate!r}"
            )
        if not callable(clock):
            # The contract: every invalid argument raises ValueError, wrong types too.
            raise ValueError(f"clock must be callable, got {clock!r}")  # noqa: TRY004
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._tokens: float = capacity
        self._last_refill = clock()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Consume `tokens` and return True if that many are available.

        Otherwise consume nothing and return False. Raise ValueError unless `tokens`
        is an integer from 1 to the capacity.
        """
        self._validate_token_count(tokens)
        self._refill()
        if not self._has_available(tokens):
            return False
        # A shortfall accepted within the rounding tolerance must not go negative.
        self._tokens = max(self._tokens - tokens, 0.0)
        return True

    def _validate_token_count(self, tokens: int) -> None:
        if not (_is_positive_int(tokens) and tokens <= self._capacity):
            raise ValueError(
                f"tokens must be an integer from 1 to capacity ({self._capacity}), "
                f"got {tokens!r}"
            )

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            # time.monotonic never steps back, but an injected clock may; keeping the
            # old reference time avoids crediting the same interval twice.
            return
        self._tokens = min(self._tokens + elapsed * self._refill_rate, self._capacity)
        self._last_refill = now

    def _has_available(self, tokens: int) -> bool:
        return self._tokens + _ROUNDING_TOLERANCE >= tokens


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and _is_positive_number(value)


def _is_positive_number(value: object) -> bool:
    # bool subclasses int, but True as a count or rate is a caller bug, not 1.
    return isinstance(value, int | float) and not isinstance(value, bool) and value > 0


class SupportsSend(Protocol):
    """Any client with a `send(request)` method."""

    def send(self, request: Any) -> Any: ...


class RateLimitedClient:
    """Lets requests through to `client` only while `bucket` has a token for them."""

    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
        self._client = client
        self._bucket = bucket

    def send(self, request: Any) -> Any:
        """Spend one token, then forward `request` to the client and return its result.

        Raise RateLimitExceeded, without calling the client, when no token is
        available. The token stays spent if the client raises.
        """
        if not self._bucket.try_acquire():
            raise RateLimitExceeded("no rate-limit token available; request not sent")
        return self._client.send(request)

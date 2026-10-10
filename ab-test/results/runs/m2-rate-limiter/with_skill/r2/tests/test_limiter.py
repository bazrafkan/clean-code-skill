import math
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    """A clock, in seconds, that moves only when the test advances it."""

    def __init__(self) -> None:
        self._now = 1000.0

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class RecordingClient:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def send(self, request: str) -> str:
        self.requests.append(request)
        return f"response to {request}"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_new_bucket_starts_full(clock: FakeClock) -> None:
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)

    results = [bucket.try_acquire() for _ in range(4)]

    assert results == [True, True, True, False]


def test_acquiring_the_whole_capacity_at_once_empties_the_bucket(
    clock: FakeClock,
) -> None:
    bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)

    assert bucket.try_acquire(5)
    assert not bucket.try_acquire()


def test_failed_acquire_consumes_nothing(clock: FakeClock) -> None:
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
    bucket.try_acquire(2)

    assert not bucket.try_acquire(2)
    assert bucket.try_acquire(1)


def test_tokens_refill_at_refill_rate_per_second(clock: FakeClock) -> None:
    bucket = TokenBucket(capacity=4, refill_rate=0.5, clock=clock)
    bucket.try_acquire(4)

    clock.advance(4.0)

    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


def test_partial_refills_accumulate_across_calls(clock: FakeClock) -> None:
    bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)
    bucket.try_acquire()

    clock.advance(0.5)
    assert not bucket.try_acquire()
    clock.advance(0.5)
    assert bucket.try_acquire()


def test_refill_stops_at_capacity(clock: FakeClock) -> None:
    bucket = TokenBucket(capacity=2, refill_rate=10, clock=clock)
    bucket.try_acquire(2)

    clock.advance(60.0)

    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


def test_clock_stepping_backwards_does_not_remove_tokens(clock: FakeClock) -> None:
    bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)

    clock.advance(-10.0)

    assert bucket.try_acquire()


def test_works_with_the_default_clock() -> None:
    bucket = TokenBucket(capacity=1, refill_rate=1)

    assert bucket.try_acquire()


@pytest.fixture
def frequent_thread_switches() -> Iterator[None]:
    """Make the interpreter switch threads very often, so that races surface."""
    original_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    yield
    sys.setswitchinterval(original_interval)


@pytest.mark.usefixtures("frequent_thread_switches")
def test_concurrent_acquires_never_hand_out_more_than_capacity() -> None:
    capacity, attempts_per_round, rounds = 100, 300, 20

    # A single round seldom exposes a race, so several are run.
    with ThreadPoolExecutor(max_workers=8) as pool:
        granted_per_round = [
            count_grants(
                pool,
                TokenBucket(capacity, refill_rate=1, clock=FakeClock()),
                attempts_per_round,
            )
            for _ in range(rounds)
        ]

    assert granted_per_round == [capacity] * rounds


def count_grants(pool: ThreadPoolExecutor, bucket: TokenBucket, attempts: int) -> int:
    return sum(pool.map(lambda _: bucket.try_acquire(), range(attempts)))


@pytest.mark.parametrize("capacity", [0, -1, 2.5, "3", True, None])
def test_rejects_invalid_capacity(capacity: Any) -> None:
    with pytest.raises(ValueError, match="capacity"):
        TokenBucket(capacity=capacity, refill_rate=1)


@pytest.mark.parametrize("refill_rate", [0, -0.5, math.nan, math.inf, "1", True, None])
def test_rejects_invalid_refill_rate(refill_rate: Any) -> None:
    with pytest.raises(ValueError, match="refill_rate"):
        TokenBucket(capacity=1, refill_rate=refill_rate)


@pytest.mark.parametrize("not_a_clock", [None, 42])
def test_rejects_a_clock_that_is_not_callable(not_a_clock: Any) -> None:
    with pytest.raises(ValueError, match="clock"):
        TokenBucket(capacity=1, refill_rate=1, clock=not_a_clock)


@pytest.mark.parametrize("tokens", [0, -1, 4, 1.5, "1", True])
def test_rejects_token_counts_outside_one_to_capacity(
    clock: FakeClock, tokens: Any
) -> None:
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)

    with pytest.raises(ValueError, match="tokens"):
        bucket.try_acquire(tokens)


def test_send_forwards_the_request_and_returns_the_response(clock: FakeClock) -> None:
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(1, refill_rate=1, clock=clock))

    response = limited.send("ping")

    assert response == "response to ping"
    assert client.requests == ["ping"]


def test_send_spends_one_token_and_raises_without_calling_client_when_empty(
    clock: FakeClock,
) -> None:
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(2, refill_rate=1, clock=clock))
    limited.send("first")
    limited.send("second")

    with pytest.raises(RateLimitExceeded):
        limited.send("third")

    assert client.requests == ["first", "second"]

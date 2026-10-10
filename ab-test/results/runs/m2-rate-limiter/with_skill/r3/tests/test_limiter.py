import math
from concurrent.futures import ThreadPoolExecutor

import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    """A clock that only moves when the test advances it."""

    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class RecordingClient:
    """A client fake that records every request it receives."""

    def __init__(self) -> None:
        self.sent_requests: list[object] = []

    def send(self, request: object) -> str:
        self.sent_requests.append(request)
        return f"response to {request}"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def empty_bucket(clock: FakeClock, capacity: int, refill_rate: float) -> TokenBucket:
    bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate, clock=clock)
    bucket.try_acquire(capacity)
    return bucket


class TestTokenBucketAcquire:
    def test_new_bucket_starts_full(self, clock):
        bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)

        results = [bucket.try_acquire() for _ in range(4)]

        assert results == [True, True, True, False]

    def test_whole_capacity_can_be_acquired_at_once(self, clock):
        bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)

        assert bucket.try_acquire(5) is True

    def test_failed_acquire_consumes_nothing(self, clock):
        bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
        bucket.try_acquire(2)

        assert bucket.try_acquire(2) is False
        assert bucket.try_acquire(1) is True

    def test_works_with_default_clock(self):
        bucket = TokenBucket(capacity=1, refill_rate=1)

        assert bucket.try_acquire() is True

    def test_concurrent_acquires_never_admit_more_than_capacity(self, clock):
        capacity = 1000
        bucket = TokenBucket(capacity=capacity, refill_rate=1, clock=clock)

        def count_successes(attempts: int) -> int:
            return sum(bucket.try_acquire() for _ in range(attempts))

        with ThreadPoolExecutor(max_workers=8) as executor:
            admitted = sum(executor.map(count_successes, [250] * 8))

        assert admitted == capacity


class TestTokenBucketRefill:
    def test_refills_a_token_after_its_share_of_time(self, clock):
        bucket = empty_bucket(clock, capacity=2, refill_rate=4)

        clock.advance(0.25)

        assert bucket.try_acquire() is True

    def test_does_not_refill_a_token_before_its_share_of_time(self, clock):
        bucket = empty_bucket(clock, capacity=2, refill_rate=4)

        clock.advance(0.2)

        assert bucket.try_acquire() is False

    def test_partial_refills_accumulate_across_failed_attempts(self, clock):
        bucket = empty_bucket(clock, capacity=1, refill_rate=2)
        clock.advance(0.25)
        bucket.try_acquire()

        clock.advance(0.25)

        assert bucket.try_acquire() is True

    def test_fractional_refill_rate_refills_slower_than_one_per_second(self, clock):
        bucket = empty_bucket(clock, capacity=1, refill_rate=0.5)

        clock.advance(1.5)
        too_early = bucket.try_acquire()
        clock.advance(0.5)
        on_time = bucket.try_acquire()

        assert (too_early, on_time) == (False, True)

    def test_refill_stops_at_capacity(self, clock):
        bucket = empty_bucket(clock, capacity=2, refill_rate=10)

        clock.advance(60)

        assert bucket.try_acquire(2) is True
        assert bucket.try_acquire() is False

    def test_clock_stepping_backwards_does_not_remove_tokens(self, clock):
        bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)

        clock.advance(-10)

        assert bucket.try_acquire(2) is True


class TestTokenBucketValidation:
    @pytest.mark.parametrize("capacity", [0, -1, 2.0, 2.5, "3", True, None])
    def test_rejects_capacity_that_is_not_a_positive_integer(self, capacity):
        with pytest.raises(ValueError, match="capacity"):
            TokenBucket(capacity=capacity, refill_rate=1)

    @pytest.mark.parametrize(
        "refill_rate", [0, -0.5, math.nan, math.inf, "1", True, None]
    )
    def test_rejects_refill_rate_that_is_not_a_positive_finite_number(
        self, refill_rate
    ):
        with pytest.raises(ValueError, match="refill_rate"):
            TokenBucket(capacity=1, refill_rate=refill_rate)

    @pytest.mark.parametrize("tokens", [0, 0.5, -1, 4, math.nan])
    def test_try_acquire_rejects_tokens_outside_one_to_capacity(self, clock, tokens):
        bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)

        with pytest.raises(ValueError, match="tokens"):
            bucket.try_acquire(tokens)


class TestRateLimitedClient:
    def test_forwards_request_and_returns_client_result(self, clock):
        client = RecordingClient()
        bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)
        limited_client = RateLimitedClient(client, bucket)

        response = limited_client.send("ping")

        assert response == "response to ping"
        assert client.sent_requests == ["ping"]

    def test_raises_without_calling_client_when_no_token_is_available(self, clock):
        client = RecordingClient()
        limited_client = RateLimitedClient(
            client, empty_bucket(clock, capacity=1, refill_rate=1)
        )

        with pytest.raises(RateLimitExceeded):
            limited_client.send("ping")

        assert client.sent_requests == []

    def test_each_send_consumes_one_token(self, clock):
        client = RecordingClient()
        bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)
        limited_client = RateLimitedClient(client, bucket)
        limited_client.send("first")
        limited_client.send("second")

        with pytest.raises(RateLimitExceeded):
            limited_client.send("third")

        assert client.sent_requests == ["first", "second"]

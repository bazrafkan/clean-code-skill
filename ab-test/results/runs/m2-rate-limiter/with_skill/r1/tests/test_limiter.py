from typing import Any

import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingClient:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    def send(self, request: Any) -> str:
        self.sent.append(request)
        return f"response to {request}"


def drained_bucket(capacity: int, refill_rate: float, clock: FakeClock) -> TokenBucket:
    bucket = TokenBucket(capacity, refill_rate, clock)
    assert bucket.try_acquire(capacity)
    return bucket


class TestTokenBucketConstruction:
    @pytest.mark.parametrize("capacity", [0, -1, 1.5, 2.0, True, "3", None])
    def test_rejects_capacity_that_is_not_a_positive_integer(
        self, capacity: Any
    ) -> None:
        with pytest.raises(ValueError, match="capacity"):
            TokenBucket(capacity, refill_rate=1, clock=FakeClock())

    @pytest.mark.parametrize("refill_rate", [0, -0.5, float("nan"), True, "1", None])
    def test_rejects_refill_rate_that_is_not_a_positive_number(
        self, refill_rate: Any
    ) -> None:
        with pytest.raises(ValueError, match="refill_rate"):
            TokenBucket(capacity=1, refill_rate=refill_rate, clock=FakeClock())

    def test_rejects_clock_that_is_not_callable(self) -> None:
        with pytest.raises(ValueError, match="clock"):
            TokenBucket(capacity=1, refill_rate=1, clock=0.0)  # type: ignore[arg-type]

    def test_works_with_the_default_clock(self) -> None:
        bucket = TokenBucket(capacity=1, refill_rate=1)

        assert bucket.try_acquire()


class TestTokenBucketAcquire:
    def test_new_bucket_is_full(self) -> None:
        bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())

        assert bucket.try_acquire(3)
        assert not bucket.try_acquire()

    def test_acquire_consumes_only_the_requested_tokens(self) -> None:
        bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())

        assert bucket.try_acquire(3)
        assert bucket.try_acquire(2)
        assert not bucket.try_acquire()

    def test_failed_acquire_consumes_nothing(self) -> None:
        bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
        bucket.try_acquire(2)

        assert not bucket.try_acquire(2)
        assert bucket.try_acquire(1)

    @pytest.mark.parametrize("tokens", [0, -1, 4, 1.5, True, "1", None])
    def test_rejects_token_count_that_is_not_an_integer_from_one_to_capacity(
        self, tokens: Any
    ) -> None:
        bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())

        with pytest.raises(ValueError, match="tokens"):
            bucket.try_acquire(tokens)


class TestTokenBucketRefill:
    def test_tokens_refill_at_refill_rate(self) -> None:
        clock = FakeClock()
        bucket = drained_bucket(capacity=4, refill_rate=2, clock=clock)

        clock.advance(1)

        assert bucket.try_acquire(2)
        assert not bucket.try_acquire()

    def test_refill_accumulates_fractions_of_a_token(self) -> None:
        clock = FakeClock()
        bucket = drained_bucket(capacity=1, refill_rate=0.5, clock=clock)

        clock.advance(1)
        assert not bucket.try_acquire()
        clock.advance(1)
        assert bucket.try_acquire()

    def test_refill_stops_at_capacity(self) -> None:
        clock = FakeClock()
        bucket = drained_bucket(capacity=2, refill_rate=1, clock=clock)

        clock.advance(100)

        assert bucket.try_acquire(2)
        assert not bucket.try_acquire()

    def test_waiting_exactly_one_refill_interval_yields_a_token(self) -> None:
        clock = FakeClock()
        bucket = drained_bucket(capacity=1, refill_rate=10, clock=clock)

        for now in (0.1, 0.2, 0.3):  # 0.3 - 0.2 is slightly less than 0.1 in floats
            clock.now = now
            assert bucket.try_acquire(), f"no token at t={now}"

    def test_clock_stepping_backwards_removes_no_tokens(self) -> None:
        clock = FakeClock(now=10)
        bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)

        clock.now = 5

        assert bucket.try_acquire()

    def test_clock_stepping_backwards_adds_no_tokens(self) -> None:
        clock = FakeClock(now=10)
        bucket = drained_bucket(capacity=1, refill_rate=1, clock=clock)

        clock.now = 5
        assert not bucket.try_acquire()
        clock.now = 10.5
        assert not bucket.try_acquire()
        clock.now = 11
        assert bucket.try_acquire()


class TestRateLimitedClient:
    def test_send_forwards_request_and_returns_client_result(self) -> None:
        client = RecordingClient()
        bucket = TokenBucket(capacity=1, refill_rate=1, clock=FakeClock())
        limited = RateLimitedClient(client, bucket)

        response = limited.send("ping")

        assert response == "response to ping"
        assert client.sent == ["ping"]

    def test_each_send_spends_one_token(self) -> None:
        bucket = TokenBucket(capacity=2, refill_rate=1, clock=FakeClock())
        limited = RateLimitedClient(RecordingClient(), bucket)

        limited.send("first")
        limited.send("second")

        assert not bucket.try_acquire()

    def test_send_raises_without_calling_client_when_no_token(self) -> None:
        client = RecordingClient()
        limited = RateLimitedClient(
            client, drained_bucket(capacity=1, refill_rate=1, clock=FakeClock())
        )

        with pytest.raises(RateLimitExceeded):
            limited.send("ping")
        assert client.sent == []

    def test_send_succeeds_again_after_refill(self) -> None:
        client = RecordingClient()
        clock = FakeClock()
        limited = RateLimitedClient(
            client, drained_bucket(capacity=1, refill_rate=1, clock=clock)
        )

        clock.advance(1)

        assert limited.send("ping") == "response to ping"

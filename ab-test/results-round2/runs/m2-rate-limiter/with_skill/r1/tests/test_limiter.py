import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingClient:
    def __init__(self) -> None:
        self.sent_requests = []

    def send(self, request):
        self.sent_requests.append(request)
        return f"response to {request}"


def drained_bucket(clock: FakeClock, capacity: int = 2, refill_rate: float = 2) -> TokenBucket:
    bucket = TokenBucket(capacity, refill_rate, clock=clock)
    assert bucket.try_acquire(capacity)
    return bucket


def test_bucket_starts_full():
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())

    results = [bucket.try_acquire() for _ in range(4)]

    assert results == [True, True, True, False]


def test_try_acquire_consumes_the_requested_number_of_tokens():
    bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())

    assert bucket.try_acquire(3)
    assert bucket.try_acquire(2)
    assert not bucket.try_acquire(1)


def test_failed_acquire_consumes_nothing():
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
    bucket.try_acquire(2)

    assert not bucket.try_acquire(2)
    assert bucket.try_acquire(1)


def test_tokens_refill_with_elapsed_time():
    clock = FakeClock()
    bucket = drained_bucket(clock, capacity=2, refill_rate=2)

    clock.advance(1)

    assert bucket.try_acquire(2)


def test_tokens_refill_continuously_in_fractions():
    clock = FakeClock()
    bucket = drained_bucket(clock, capacity=2, refill_rate=2)

    clock.advance(0.25)
    assert not bucket.try_acquire()
    clock.advance(0.25)
    assert bucket.try_acquire()


def test_refill_stops_at_capacity():
    clock = FakeClock()
    bucket = drained_bucket(clock, capacity=2, refill_rate=2)

    clock.advance(60)

    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


def test_default_clock_is_usable():
    bucket = TokenBucket(capacity=1, refill_rate=1)

    assert bucket.try_acquire()


@pytest.mark.parametrize("capacity", [0, -1, 2.5, "3"])
def test_invalid_capacity_is_rejected(capacity):
    with pytest.raises(ValueError):
        TokenBucket(capacity, refill_rate=1, clock=FakeClock())


@pytest.mark.parametrize("refill_rate", [0, -0.5])
def test_non_positive_refill_rate_is_rejected(refill_rate):
    with pytest.raises(ValueError):
        TokenBucket(capacity=1, refill_rate=refill_rate, clock=FakeClock())


@pytest.mark.parametrize("tokens", [0, -1, 4])
def test_tokens_outside_one_to_capacity_are_rejected(tokens):
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())

    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)


def test_client_send_forwards_request_and_returns_result():
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(capacity=1, refill_rate=1, clock=FakeClock()))

    result = limited.send("ping")

    assert result == "response to ping"
    assert client.sent_requests == ["ping"]


def test_client_send_without_token_raises_and_does_not_call_client():
    client = RecordingClient()
    limited = RateLimitedClient(client, drained_bucket(FakeClock()))

    with pytest.raises(RateLimitExceeded):
        limited.send("ping")

    assert client.sent_requests == []

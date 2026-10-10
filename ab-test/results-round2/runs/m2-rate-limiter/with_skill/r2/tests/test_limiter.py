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


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def drained_bucket(capacity: int, refill_rate: float, clock: FakeClock) -> TokenBucket:
    bucket = TokenBucket(capacity, refill_rate, clock)
    assert bucket.try_acquire(capacity)
    return bucket


def test_bucket_starts_full(clock):
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)

    results = [bucket.try_acquire() for _ in range(4)]

    assert results == [True, True, True, False]


def test_can_acquire_whole_capacity_at_once(clock):
    bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)

    assert bucket.try_acquire(5)


def test_failed_acquire_consumes_nothing(clock):
    bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)
    bucket.try_acquire()

    assert not bucket.try_acquire(2)
    assert bucket.try_acquire(1)


def test_tokens_refill_with_elapsed_time(clock):
    bucket = drained_bucket(capacity=2, refill_rate=2, clock=clock)

    clock.advance(0.5)

    assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_partial_refill_accumulates_across_attempts(clock):
    bucket = drained_bucket(capacity=1, refill_rate=1, clock=clock)

    clock.advance(0.5)
    assert not bucket.try_acquire()
    clock.advance(0.5)
    assert bucket.try_acquire()


def test_refill_stops_at_capacity(clock):
    bucket = drained_bucket(capacity=2, refill_rate=1, clock=clock)

    clock.advance(100)

    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


@pytest.mark.parametrize("capacity", [0, -1, 2.5])
def test_rejects_invalid_capacity(capacity, clock):
    with pytest.raises(ValueError):
        TokenBucket(capacity=capacity, refill_rate=1, clock=clock)


@pytest.mark.parametrize("refill_rate", [0, -0.5])
def test_rejects_non_positive_refill_rate(refill_rate, clock):
    with pytest.raises(ValueError):
        TokenBucket(capacity=1, refill_rate=refill_rate, clock=clock)


@pytest.mark.parametrize("tokens", [0, 4])
def test_rejects_token_count_outside_one_to_capacity(tokens, clock):
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)

    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)


def test_client_forwards_request_and_returns_response(clock):
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(capacity=1, refill_rate=1, clock=clock))

    response = limited.send("ping")

    assert response == "response to ping"
    assert client.sent_requests == ["ping"]


def test_client_raises_without_sending_when_no_token(clock):
    client = RecordingClient()
    limited = RateLimitedClient(client, drained_bucket(capacity=1, refill_rate=1, clock=clock))

    with pytest.raises(RateLimitExceeded):
        limited.send("ping")

    assert client.sent_requests == []

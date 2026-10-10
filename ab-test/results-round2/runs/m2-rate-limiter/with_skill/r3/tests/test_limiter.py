import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class RecordingClient:
    def __init__(self):
        self.sent_requests = []

    def send(self, request):
        self.sent_requests.append(request)
        return f"response to {request}"


def drained_bucket(capacity, refill_rate, clock):
    bucket = TokenBucket(capacity, refill_rate, clock)
    assert bucket.try_acquire(capacity)
    return bucket


def test_bucket_starts_full():
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())

    results = [bucket.try_acquire() for _ in range(4)]

    assert results == [True, True, True, False]


def test_try_acquire_consumes_the_requested_number_of_tokens():
    bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())

    assert bucket.try_acquire(3)
    assert not bucket.try_acquire(3)
    assert bucket.try_acquire(2)


def test_failed_acquire_consumes_nothing():
    bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
    bucket.try_acquire(4)

    assert not bucket.try_acquire(2)

    assert bucket.try_acquire(1)


def test_tokens_refill_continuously_with_elapsed_time():
    clock = FakeClock()
    bucket = drained_bucket(capacity=2, refill_rate=2, clock=clock)

    clock.advance(0.25)
    assert not bucket.try_acquire()

    clock.advance(0.25)
    assert bucket.try_acquire()


def test_refill_stops_at_capacity():
    clock = FakeClock()
    bucket = drained_bucket(capacity=2, refill_rate=10, clock=clock)

    clock.advance(100)

    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


@pytest.mark.parametrize("capacity", [0, -1, 1.5, "3"])
def test_invalid_capacity_is_rejected(capacity):
    with pytest.raises(ValueError):
        TokenBucket(capacity, refill_rate=1, clock=FakeClock())


@pytest.mark.parametrize("refill_rate", [0, -0.5])
def test_non_positive_refill_rate_is_rejected(refill_rate):
    with pytest.raises(ValueError):
        TokenBucket(capacity=1, refill_rate=refill_rate, clock=FakeClock())


@pytest.mark.parametrize("tokens", [0, 4])
def test_try_acquire_rejects_tokens_outside_one_to_capacity(tokens):
    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())

    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)


def test_client_forwards_request_and_returns_its_result_when_token_available():
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(capacity=1, refill_rate=1, clock=FakeClock()))

    response = limited.send("ping")

    assert response == "response to ping"
    assert client.sent_requests == ["ping"]


def test_client_raises_without_sending_when_no_token_available():
    client = RecordingClient()
    empty_bucket = drained_bucket(capacity=1, refill_rate=1, clock=FakeClock())
    limited = RateLimitedClient(client, empty_bucket)

    with pytest.raises(RateLimitExceeded):
        limited.send("ping")

    assert client.sent_requests == []

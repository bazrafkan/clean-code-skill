import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class RecordingClient:
    def __init__(self):
        self.sent = []

    def send(self, request):
        self.sent.append(request)
        return "ok:" + str(request)


def test_starts_full():
    clock = FakeClock()
    bucket = TokenBucket(3, 1.0, clock=clock)
    assert [bucket.try_acquire() for _ in range(4)] == [True, True, True, False]


def test_refills_with_time():
    clock = FakeClock()
    bucket = TokenBucket(2, 2.0, clock=clock)
    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()
    clock.now += 0.5
    assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_refill_is_capped_at_capacity():
    clock = FakeClock()
    bucket = TokenBucket(2, 1.0, clock=clock)
    assert bucket.try_acquire(2)
    clock.now += 100
    assert bucket.try_acquire()
    assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_failed_acquire_consumes_nothing():
    clock = FakeClock()
    bucket = TokenBucket(3, 1.0, clock=clock)
    assert bucket.try_acquire(2)
    assert not bucket.try_acquire(2)
    assert bucket.try_acquire(1)


def test_fractional_refill_accumulates():
    clock = FakeClock()
    bucket = TokenBucket(1, 1.0, clock=clock)
    assert bucket.try_acquire()
    clock.now += 0.4
    assert not bucket.try_acquire()
    clock.now += 0.6
    assert bucket.try_acquire()


@pytest.mark.parametrize("capacity, rate", [(0, 1.0), (-1, 1.0), (2, 0), (2, -0.5)])
def test_invalid_construction(capacity, rate):
    with pytest.raises(ValueError):
        TokenBucket(capacity, rate, clock=FakeClock())


@pytest.mark.parametrize("tokens", [0, -1, 4])
def test_invalid_token_request(tokens):
    bucket = TokenBucket(3, 1.0, clock=FakeClock())
    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)


def test_default_clock_works():
    bucket = TokenBucket(1, 1.0)
    assert bucket.try_acquire()


def test_client_forwards_and_returns_result():
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(2, 1.0, clock=FakeClock()))
    assert limited.send("a") == "ok:a"
    assert client.sent == ["a"]


def test_client_raises_when_limited_and_does_not_forward():
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(1, 1.0, clock=FakeClock()))
    limited.send("a")
    with pytest.raises(RateLimitExceeded):
        limited.send("b")
    assert client.sent == ["a"]


def test_rate_limit_exceeded_is_an_exception():
    assert issubclass(RateLimitExceeded, Exception)

import threading

import pytest

from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class RecordingClient:
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return f"response to {request}"


@pytest.fixture
def clock():
    return FakeClock()


# --- TokenBucket construction ---

@pytest.mark.parametrize("capacity", [0, -1, 1.0, 2.5, "3", None, True])
def test_rejects_invalid_capacity(capacity):
    with pytest.raises(ValueError):
        TokenBucket(capacity, 1)


@pytest.mark.parametrize("rate", [0, -0.5, float("nan"), float("inf"), "1", None, True])
def test_rejects_invalid_refill_rate(rate):
    with pytest.raises(ValueError):
        TokenBucket(1, rate)


def test_rejects_non_callable_clock():
    with pytest.raises(ValueError):
        TokenBucket(1, 1, clock=5)


def test_accepts_fractional_refill_rate(clock):
    bucket = TokenBucket(1, 0.25, clock=clock)
    assert bucket.refill_rate == 0.25


def test_uses_monotonic_clock_by_default():
    bucket = TokenBucket(2, 1)
    assert bucket.try_acquire(2) is True
    assert bucket.try_acquire() is False


# --- try_acquire ---

def test_starts_full(clock):
    bucket = TokenBucket(3, 1, clock=clock)
    assert bucket.try_acquire(3) is True
    assert bucket.try_acquire() is False


def test_failed_acquire_consumes_nothing(clock):
    bucket = TokenBucket(3, 1, clock=clock)
    assert bucket.try_acquire(2) is True
    assert bucket.try_acquire(2) is False
    assert bucket.try_acquire(1) is True
    assert bucket.try_acquire(1) is False


def test_refills_continuously_with_elapsed_time(clock):
    bucket = TokenBucket(5, 2, clock=clock)
    assert bucket.try_acquire(5) is True
    clock.advance(0.25)
    assert bucket.try_acquire() is False  # only 0.5 tokens so far
    clock.advance(0.25)
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_refill_is_capped_at_capacity(clock):
    bucket = TokenBucket(3, 10, clock=clock)
    assert bucket.try_acquire(3) is True
    clock.advance(1000)
    assert bucket.try_acquire(3) is True
    assert bucket.try_acquire() is False


def test_failed_attempts_do_not_delay_refill(clock):
    bucket = TokenBucket(1, 0.1, clock=clock)
    assert bucket.try_acquire() is True
    for _ in range(9):
        clock.advance(1)
        assert bucket.try_acquire() is False
    clock.advance(1)
    assert bucket.try_acquire() is True


def test_float_rounding_does_not_lose_a_token(clock):
    clock.now = 0.1
    bucket = TokenBucket(2, 10, clock=clock)
    assert bucket.try_acquire(2) is True
    clock.now = 0.3  # (0.3 - 0.1) * 10 == 1.9999999999999998 in floating point
    assert bucket.try_acquire(2) is True


def test_clock_going_backwards_does_not_drain_or_overfill(clock):
    clock.now = 100.0
    bucket = TokenBucket(2, 1, clock=clock)
    assert bucket.try_acquire() is True
    clock.now = 50.0
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False
    clock.now = 100.5
    assert bucket.try_acquire() is False
    clock.now = 101.0
    assert bucket.try_acquire() is True


@pytest.mark.parametrize("tokens", [0, -1, 4, 1.0, "1", None, True])
def test_rejects_invalid_token_count(clock, tokens):
    bucket = TokenBucket(3, 1, clock=clock)
    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)
    assert bucket.try_acquire(3) is True  # nothing consumed by the bad call


def test_concurrent_acquires_never_exceed_capacity(clock):
    bucket = TokenBucket(100, 1, clock=clock)
    results = []
    results_lock = threading.Lock()

    def worker():
        for _ in range(50):
            ok = bucket.try_acquire()
            with results_lock:
                results.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(True) == 100


# --- RateLimitedClient ---

def test_forwards_request_and_returns_result(clock):
    inner = RecordingClient()
    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
    assert client.send("ping") == "response to ping"
    assert inner.requests == ["ping"]


def test_raises_without_calling_client_when_limited(clock):
    inner = RecordingClient()
    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
    client.send("first")
    with pytest.raises(RateLimitExceeded):
        client.send("second")
    assert inner.requests == ["first"]


def test_allows_requests_again_after_refill(clock):
    inner = RecordingClient()
    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
    client.send("first")
    clock.advance(1)
    assert client.send("second") == "response to second"
    assert inner.requests == ["first", "second"]


def test_client_errors_propagate(clock):
    class FailingClient:
        def send(self, request):
            raise ConnectionError("down")

    client = RateLimitedClient(FailingClient(), TokenBucket(1, 1, clock=clock))
    with pytest.raises(ConnectionError):
        client.send("ping")

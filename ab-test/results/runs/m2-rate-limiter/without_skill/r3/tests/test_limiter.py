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


# --- TokenBucket construction ---------------------------------------------


@pytest.mark.parametrize("capacity", [0, -1, 1.5, 2.0, "3", None, True])
def test_rejects_invalid_capacity(capacity, clock):
    with pytest.raises(ValueError):
        TokenBucket(capacity, 1, clock=clock)


@pytest.mark.parametrize(
    "refill_rate", [0, -1, -0.5, float("nan"), float("inf"), "1", None, True]
)
def test_rejects_invalid_refill_rate(refill_rate, clock):
    with pytest.raises(ValueError):
        TokenBucket(1, refill_rate, clock=clock)


def test_rejects_non_callable_clock():
    with pytest.raises(ValueError):
        TokenBucket(1, 1, clock=0.0)


def test_accepts_fractional_refill_rate(clock):
    bucket = TokenBucket(1, 0.5, clock=clock)
    assert bucket.try_acquire()


def test_uses_monotonic_clock_by_default():
    bucket = TokenBucket(2, 1)
    assert bucket.try_acquire(2)


# --- TokenBucket.try_acquire ----------------------------------------------


def test_starts_full(clock):
    bucket = TokenBucket(3, 1, clock=clock)
    assert [bucket.try_acquire() for _ in range(4)] == [True, True, True, False]


def test_acquires_several_tokens_at_once(clock):
    bucket = TokenBucket(5, 1, clock=clock)
    assert bucket.try_acquire(3)
    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


def test_failed_acquire_consumes_nothing(clock):
    bucket = TokenBucket(5, 1, clock=clock)
    assert bucket.try_acquire(3)
    assert not bucket.try_acquire(3)
    assert bucket.try_acquire(2)


@pytest.mark.parametrize("tokens", [0, -1, 6, 1.0, 1.5, "1", None, True])
def test_rejects_invalid_token_count(tokens, clock):
    bucket = TokenBucket(5, 1, clock=clock)
    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)


def test_invalid_token_count_consumes_nothing(clock):
    bucket = TokenBucket(2, 1, clock=clock)
    with pytest.raises(ValueError):
        bucket.try_acquire(3)
    assert bucket.try_acquire(2)


def test_refills_continuously(clock):
    bucket = TokenBucket(2, 2, clock=clock)
    assert bucket.try_acquire(2)

    clock.advance(0.25)  # 0.5 tokens
    assert not bucket.try_acquire()

    clock.advance(0.25)  # 1 token
    assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_partial_tokens_carry_over(clock):
    bucket = TokenBucket(1, 1, clock=clock)
    assert bucket.try_acquire()

    clock.advance(0.6)
    assert not bucket.try_acquire()
    clock.advance(0.4)
    assert bucket.try_acquire()


def test_refill_is_capped_at_capacity(clock):
    bucket = TokenBucket(3, 10, clock=clock)
    assert bucket.try_acquire(3)

    clock.advance(1000)
    assert bucket.try_acquire(3)
    assert not bucket.try_acquire()


def test_ten_tenth_second_steps_refill_one_token(clock):
    # 0.1 added ten times is slightly less than 1.0 in floating point.
    bucket = TokenBucket(1, 1, clock=clock)
    assert bucket.try_acquire()

    for _ in range(9):
        clock.advance(0.1)
        assert not bucket.try_acquire()
    clock.advance(0.1)
    assert bucket.try_acquire()


def test_backwards_clock_does_not_add_or_remove_tokens(clock):
    clock.now = 100.0
    bucket = TokenBucket(2, 1, clock=clock)
    assert bucket.try_acquire(2)

    clock.now = 50.0
    assert not bucket.try_acquire()

    # The interval up to the previous high-water mark is not credited again.
    clock.now = 100.5
    assert not bucket.try_acquire()
    clock.now = 101.0
    assert bucket.try_acquire()


def test_concurrent_acquires_never_exceed_capacity(clock):
    bucket = TokenBucket(100, 1, clock=clock)
    results = []
    lock = threading.Lock()

    def worker():
        for _ in range(50):
            acquired = bucket.try_acquire()
            with lock:
                results.append(acquired)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(True) == 100


# --- RateLimitedClient ----------------------------------------------------


def test_client_forwards_request_and_returns_result(clock):
    inner = RecordingClient()
    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))

    assert client.send("ping") == "response to ping"
    assert inner.requests == ["ping"]


def test_client_raises_without_calling_inner_when_limited(clock):
    inner = RecordingClient()
    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
    client.send("first")

    with pytest.raises(RateLimitExceeded):
        client.send("second")
    assert inner.requests == ["first"]


def test_client_recovers_after_refill(clock):
    inner = RecordingClient()
    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
    client.send("first")

    clock.advance(1)
    assert client.send("second") == "response to second"
    assert inner.requests == ["first", "second"]


def test_client_spends_token_even_if_inner_client_fails(clock):
    class FailingClient:
        def send(self, request):
            raise ConnectionError("down")

    client = RateLimitedClient(FailingClient(), TokenBucket(1, 1, clock=clock))

    with pytest.raises(ConnectionError):
        client.send("x")
    with pytest.raises(RateLimitExceeded):
        client.send("y")


def test_rate_limit_exceeded_is_an_exception():
    assert issubclass(RateLimitExceeded, Exception)

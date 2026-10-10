import math
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
    def __init__(self, response="ok"):
        self.response = response
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return self.response


def drain(bucket, capacity):
    for _ in range(capacity):
        assert bucket.try_acquire()


# --- TokenBucket: construction --------------------------------------------

@pytest.mark.parametrize("capacity", [0, -1, 1.5, 2.0, True, "3", None])
def test_invalid_capacity_raises(capacity):
    with pytest.raises(ValueError):
        TokenBucket(capacity, 1)


@pytest.mark.parametrize("rate", [0, -0.5, math.nan, math.inf, True, "1", None])
def test_invalid_refill_rate_raises(rate):
    with pytest.raises(ValueError):
        TokenBucket(1, rate)


def test_non_callable_clock_raises():
    with pytest.raises(ValueError):
        TokenBucket(1, 1, clock=5)


def test_fractional_refill_rate_is_accepted():
    clock = FakeClock()
    bucket = TokenBucket(1, 0.5, clock=clock)
    assert bucket.try_acquire()
    clock.advance(1.5)
    assert not bucket.try_acquire()
    clock.advance(0.5)
    assert bucket.try_acquire()


def test_default_clock_works():
    bucket = TokenBucket(2, 1)
    assert bucket.try_acquire()
    assert bucket.try_acquire()
    assert not bucket.try_acquire()


# --- TokenBucket: try_acquire ---------------------------------------------

def test_bucket_starts_full():
    bucket = TokenBucket(3, 1, clock=FakeClock())
    assert [bucket.try_acquire() for _ in range(4)] == [True, True, True, False]


def test_failed_acquire_consumes_nothing():
    bucket = TokenBucket(5, 1, clock=FakeClock())
    assert bucket.try_acquire(3)
    assert not bucket.try_acquire(3)
    assert bucket.try_acquire(2)
    assert not bucket.try_acquire()


def test_acquire_whole_capacity():
    bucket = TokenBucket(4, 1, clock=FakeClock())
    assert bucket.try_acquire(4)
    assert not bucket.try_acquire()


@pytest.mark.parametrize("tokens", [0, -1, 4, 1.5, True, "1", None])
def test_invalid_token_count_raises(tokens):
    bucket = TokenBucket(3, 1, clock=FakeClock())
    with pytest.raises(ValueError):
        bucket.try_acquire(tokens)
    # The rejected call must not have consumed anything.
    assert bucket.try_acquire(3)


def test_refills_continuously_with_elapsed_time():
    clock = FakeClock()
    bucket = TokenBucket(2, 2, clock=clock)
    drain(bucket, 2)
    clock.advance(0.25)
    assert not bucket.try_acquire()
    clock.advance(0.25)
    assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_partial_refill_is_kept_across_failed_attempts():
    clock = FakeClock()
    bucket = TokenBucket(1, 1, clock=clock)
    drain(bucket, 1)
    for _ in range(3):
        clock.advance(0.25)
        assert not bucket.try_acquire()
    clock.advance(0.25)
    assert bucket.try_acquire()


def test_refill_is_capped_at_capacity():
    clock = FakeClock()
    bucket = TokenBucket(3, 10, clock=clock)
    drain(bucket, 3)
    clock.advance(1000)
    drain(bucket, 3)
    assert not bucket.try_acquire()


def test_float_rounding_does_not_cause_spurious_rejection():
    clock = FakeClock()
    bucket = TokenBucket(1, 1, clock=clock)
    drain(bucket, 1)
    for _ in range(10):
        clock.advance(0.1)  # sums to 0.9999999999999999
    assert bucket.try_acquire()


def test_clock_going_backwards_adds_no_tokens():
    clock = FakeClock(100.0)
    bucket = TokenBucket(1, 1, clock=clock)
    drain(bucket, 1)
    clock.now = 50.0
    assert not bucket.try_acquire()
    clock.now = 100.5
    assert not bucket.try_acquire()
    clock.now = 101.0
    assert bucket.try_acquire()


def test_concurrent_acquires_never_exceed_capacity():
    bucket = TokenBucket(50, 1, clock=FakeClock())
    results = []
    lock = threading.Lock()
    start = threading.Barrier(20)

    def worker():
        start.wait()
        for _ in range(10):
            ok = bucket.try_acquire()
            with lock:
                results.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 50


# --- RateLimitedClient ----------------------------------------------------

def test_client_forwards_request_and_returns_result():
    client = RecordingClient(response={"status": 200})
    limited = RateLimitedClient(client, TokenBucket(2, 1, clock=FakeClock()))
    assert limited.send("req-1") == {"status": 200}
    assert client.requests == ["req-1"]


def test_client_raises_without_sending_when_limited():
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(1, 1, clock=FakeClock()))
    limited.send("first")
    with pytest.raises(RateLimitExceeded):
        limited.send("second")
    assert client.requests == ["first"]


def test_client_sends_again_after_refill():
    clock = FakeClock()
    client = RecordingClient()
    limited = RateLimitedClient(client, TokenBucket(1, 1, clock=clock))
    limited.send("a")
    with pytest.raises(RateLimitExceeded):
        limited.send("b")
    clock.advance(1)
    limited.send("c")
    assert client.requests == ["a", "c"]


def test_client_errors_propagate_and_still_use_a_token():
    class FailingClient:
        def send(self, request):
            raise ConnectionError("boom")

    limited = RateLimitedClient(FailingClient(), TokenBucket(1, 1, clock=FakeClock()))
    with pytest.raises(ConnectionError):
        limited.send("x")
    with pytest.raises(RateLimitExceeded):
        limited.send("y")

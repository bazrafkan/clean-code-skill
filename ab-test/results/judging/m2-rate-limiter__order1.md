You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{"pairs": [{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}, ...]}

Read only this packet file. Do not look at any other file or directory, and do not write any files.


## Task given to both developers

Create `ratelimit/limiter.py` with a token-bucket rate limiter and a client wrapper that uses it.

`TokenBucket(capacity, refill_rate, clock=time.monotonic)`
- `capacity` is the maximum number of tokens. It must be an integer greater than 0.
- `refill_rate` is tokens added per second. It must be greater than 0.
- `clock` is a zero-argument callable that returns the current time in seconds.
- Invalid arguments raise `ValueError`.
- The bucket starts full. Tokens refill continuously with elapsed clock time, up to `capacity`.
- `try_acquire(tokens=1) -> bool`:
  - If enough tokens are available, consume them and return `True`.
  - Otherwise return `False` without consuming anything.
  - `tokens` must be at least 1 and at most `capacity`, otherwise raise `ValueError`.

`RateLimitedClient(client, bucket)`
- Wraps any object that has a `send(request)` method.
- `send(request)` forwards to `client.send(request)` and returns its result when a token is available.
- When no token is available, it raises `RateLimitExceeded` (defined in the same module) without calling the client.

## Pair 1

### Implementation 1

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,118 @@
+"""Token-bucket rate limiting, and a client wrapper that enforces it."""
+
+import time
+from collections.abc import Callable
+from typing import Any, Protocol
+
+__all__ = ["RateLimitExceeded", "RateLimitedClient", "SupportsSend", "TokenBucket"]
+
+# Float clock arithmetic can come up a hair short (0.3 - 0.2 < 0.1), which would
+# deny a token to a caller that waited exactly long enough. Shortfalls this small
+# are ignored.
+_ROUNDING_TOLERANCE = 1e-9
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+class TokenBucket:
+    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` per second.
+
+    Not thread-safe: guard a shared instance with a lock.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        """Create a full bucket. `clock()` must return the current time in seconds.
+
+        Raise ValueError unless `capacity` is an integer > 0, `refill_rate` is a
+        number > 0 and `clock` is callable.
+        """
+        if not _is_positive_int(capacity):
+            raise ValueError(
+                f"capacity must be an integer greater than 0, got {capacity!r}"
+            )
+        if not _is_positive_number(refill_rate):
+            raise ValueError(
+                f"refill_rate must be a number greater than 0, got {refill_rate!r}"
+            )
+        if not callable(clock):
+            # The contract: every invalid argument raises ValueError, wrong types too.
+            raise ValueError(f"clock must be callable, got {clock!r}")  # noqa: TRY004
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._tokens: float = capacity
+        self._last_refill = clock()
+
+    def try_acquire(self, tokens: int = 1) -> bool:
+        """Consume `tokens` and return True if that many are available.
+
+        Otherwise consume nothing and return False. Raise ValueError unless `tokens`
+        is an integer from 1 to the capacity.
+        """
+        self._validate_token_count(tokens)
+        self._refill()
+        if not self._has_available(tokens):
+            return False
+        # A shortfall accepted within the rounding tolerance must not go negative.
+        self._tokens = max(self._tokens - tokens, 0.0)
+        return True
+
+    def _validate_token_count(self, tokens: int) -> None:
+        if not (_is_positive_int(tokens) and tokens <= self._capacity):
+            raise ValueError(
+                f"tokens must be an integer from 1 to capacity ({self._capacity}), "
+                f"got {tokens!r}"
+            )
+
+    def _refill(self) -> None:
+        now = self._clock()
+        elapsed = now - self._last_refill
+        if elapsed <= 0:
+            # time.monotonic never steps back, but an injected clock may; keeping the
+            # old reference time avoids crediting the same interval twice.
+            return
+        self._tokens = min(self._tokens + elapsed * self._refill_rate, self._capacity)
+        self._last_refill = now
+
+    def _has_available(self, tokens: int) -> bool:
+        return self._tokens + _ROUNDING_TOLERANCE >= tokens
+
+
+def _is_positive_int(value: object) -> bool:
+    return isinstance(value, int) and _is_positive_number(value)
+
+
+def _is_positive_number(value: object) -> bool:
+    # bool subclasses int, but True as a count or rate is a caller bug, not 1.
+    return isinstance(value, int | float) and not isinstance(value, bool) and value > 0
+
+
+class SupportsSend(Protocol):
+    """Any client with a `send(request)` method."""
+
+    def send(self, request: Any) -> Any: ...
+
+
+class RateLimitedClient:
+    """Lets requests through to `client` only while `bucket` has a token for them."""
+
+    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request: Any) -> Any:
+        """Spend one token, then forward `request` to the client and return its result.
+
+        Raise RateLimitExceeded, without calling the client, when no token is
+        available. The token stays spent if the client raises.
+        """
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("no rate-limit token available; request not sent")
+        return self._client.send(request)
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,185 @@
+from typing import Any
+
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    def __init__(self, now: float = 0.0) -> None:
+        self.now = now
+
+    def __call__(self) -> float:
+        return self.now
+
+    def advance(self, seconds: float) -> None:
+        self.now += seconds
+
+
+class RecordingClient:
+    def __init__(self) -> None:
+        self.sent: list[Any] = []
+
+    def send(self, request: Any) -> str:
+        self.sent.append(request)
+        return f"response to {request}"
+
+
+def drained_bucket(capacity: int, refill_rate: float, clock: FakeClock) -> TokenBucket:
+    bucket = TokenBucket(capacity, refill_rate, clock)
+    assert bucket.try_acquire(capacity)
+    return bucket
+
+
+class TestTokenBucketConstruction:
+    @pytest.mark.parametrize("capacity", [0, -1, 1.5, 2.0, True, "3", None])
+    def test_rejects_capacity_that_is_not_a_positive_integer(
+        self, capacity: Any
+    ) -> None:
+        with pytest.raises(ValueError, match="capacity"):
+            TokenBucket(capacity, refill_rate=1, clock=FakeClock())
+
+    @pytest.mark.parametrize("refill_rate", [0, -0.5, float("nan"), True, "1", None])
+    def test_rejects_refill_rate_that_is_not_a_positive_number(
+        self, refill_rate: Any
+    ) -> None:
+        with pytest.raises(ValueError, match="refill_rate"):
+            TokenBucket(capacity=1, refill_rate=refill_rate, clock=FakeClock())
+
+    def test_rejects_clock_that_is_not_callable(self) -> None:
+        with pytest.raises(ValueError, match="clock"):
+            TokenBucket(capacity=1, refill_rate=1, clock=0.0)  # type: ignore[arg-type]
+
+    def test_works_with_the_default_clock(self) -> None:
+        bucket = TokenBucket(capacity=1, refill_rate=1)
+
+        assert bucket.try_acquire()
+
+
+class TestTokenBucketAcquire:
+    def test_new_bucket_is_full(self) -> None:
+        bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+
+        assert bucket.try_acquire(3)
+        assert not bucket.try_acquire()
+
+    def test_acquire_consumes_only_the_requested_tokens(self) -> None:
+        bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
+
+        assert bucket.try_acquire(3)
+        assert bucket.try_acquire(2)
+        assert not bucket.try_acquire()
+
+    def test_failed_acquire_consumes_nothing(self) -> None:
+        bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+        bucket.try_acquire(2)
+
+        assert not bucket.try_acquire(2)
+        assert bucket.try_acquire(1)
+
+    @pytest.mark.parametrize("tokens", [0, -1, 4, 1.5, True, "1", None])
+    def test_rejects_token_count_that_is_not_an_integer_from_one_to_capacity(
+        self, tokens: Any
+    ) -> None:
+        bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+
+        with pytest.raises(ValueError, match="tokens"):
+            bucket.try_acquire(tokens)
+
+
+class TestTokenBucketRefill:
+    def test_tokens_refill_at_refill_rate(self) -> None:
+        clock = FakeClock()
+        bucket = drained_bucket(capacity=4, refill_rate=2, clock=clock)
+
+        clock.advance(1)
+
+        assert bucket.try_acquire(2)
+        assert not bucket.try_acquire()
+
+    def test_refill_accumulates_fractions_of_a_token(self) -> None:
+        clock = FakeClock()
+        bucket = drained_bucket(capacity=1, refill_rate=0.5, clock=clock)
+
+        clock.advance(1)
+        assert not bucket.try_acquire()
+        clock.advance(1)
+        assert bucket.try_acquire()
+
+    def test_refill_stops_at_capacity(self) -> None:
+        clock = FakeClock()
+        bucket = drained_bucket(capacity=2, refill_rate=1, clock=clock)
+
+        clock.advance(100)
+
+        assert bucket.try_acquire(2)
+        assert not bucket.try_acquire()
+
+    def test_waiting_exactly_one_refill_interval_yields_a_token(self) -> None:
+        clock = FakeClock()
+        bucket = drained_bucket(capacity=1, refill_rate=10, clock=clock)
+
+        for now in (0.1, 0.2, 0.3):  # 0.3 - 0.2 is slightly less than 0.1 in floats
+            clock.now = now
+            assert bucket.try_acquire(), f"no token at t={now}"
+
+    def test_clock_stepping_backwards_removes_no_tokens(self) -> None:
+        clock = FakeClock(now=10)
+        bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)
+
+        clock.now = 5
+
+        assert bucket.try_acquire()
+
+    def test_clock_stepping_backwards_adds_no_tokens(self) -> None:
+        clock = FakeClock(now=10)
+        bucket = drained_bucket(capacity=1, refill_rate=1, clock=clock)
+
+        clock.now = 5
+        assert not bucket.try_acquire()
+        clock.now = 10.5
+        assert not bucket.try_acquire()
+        clock.now = 11
+        assert bucket.try_acquire()
+
+
+class TestRateLimitedClient:
+    def test_send_forwards_request_and_returns_client_result(self) -> None:
+        client = RecordingClient()
+        bucket = TokenBucket(capacity=1, refill_rate=1, clock=FakeClock())
+        limited = RateLimitedClient(client, bucket)
+
+        response = limited.send("ping")
+
+        assert response == "response to ping"
+        assert client.sent == ["ping"]
+
+    def test_each_send_spends_one_token(self) -> None:
+        bucket = TokenBucket(capacity=2, refill_rate=1, clock=FakeClock())
+        limited = RateLimitedClient(RecordingClient(), bucket)
+
+        limited.send("first")
+        limited.send("second")
+
+        assert not bucket.try_acquire()
+
+    def test_send_raises_without_calling_client_when_no_token(self) -> None:
+        client = RecordingClient()
+        limited = RateLimitedClient(
+            client, drained_bucket(capacity=1, refill_rate=1, clock=FakeClock())
+        )
+
+        with pytest.raises(RateLimitExceeded):
+            limited.send("ping")
+        assert client.sent == []
+
+    def test_send_succeeds_again_after_refill(self) -> None:
+        client = RecordingClient()
+        clock = FakeClock()
+        limited = RateLimitedClient(
+            client, drained_bucket(capacity=1, refill_rate=1, clock=clock)
+        )
+
+        clock.advance(1)
+
+        assert limited.send("ping") == "response to ping"
```

### Implementation 2

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,92 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+import math
+import threading
+import time
+from numbers import Real
+
+# Absorbs float rounding in the refill arithmetic (for example 0.1 + 0.2 seconds
+# times a rate of 10 giving 2.9999999999999996 tokens instead of 3).
+_ROUNDING_TOLERANCE = 1e-9
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+class TokenBucket:
+    """A bucket of up to `capacity` tokens, refilled at `refill_rate` tokens per second.
+
+    The bucket starts full. Refill is computed from elapsed `clock` time on each
+    acquisition, so no background thread is needed. Instances are safe to share
+    between threads.
+    """
+
+    def __init__(self, capacity, refill_rate, clock=time.monotonic):
+        if not _is_int(capacity) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
+        if not _is_real(refill_rate) or not math.isfinite(refill_rate) or refill_rate <= 0:
+            raise ValueError(f"refill_rate must be a finite number greater than 0, got {refill_rate!r}")
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._lock = threading.Lock()
+        self._tokens = float(capacity)
+        self._updated_at = clock()
+
+    @property
+    def capacity(self):
+        return self._capacity
+
+    @property
+    def refill_rate(self):
+        return self._refill_rate
+
+    def try_acquire(self, tokens=1):
+        """Consume `tokens` and return True if they are available, otherwise return False."""
+        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be an integer between 1 and {self._capacity}, got {tokens!r}"
+            )
+
+        with self._lock:
+            now = self._clock()
+            available = self._available_at(now)
+            if available + _ROUNDING_TOLERANCE < tokens:
+                # State is left untouched so repeated failed attempts do not
+                # accumulate rounding error in the stored token count.
+                return False
+            self._tokens = max(0.0, available - tokens)
+            self._updated_at = max(self._updated_at, now)
+            return True
+
+    def _available_at(self, now):
+        # A clock that steps backwards must not drain the bucket.
+        elapsed = max(0.0, now - self._updated_at)
+        return min(float(self._capacity), self._tokens + elapsed * self._refill_rate)
+
+
+class RateLimitedClient:
+    """Forwards `send` calls to a wrapped client, one bucket token per request."""
+
+    def __init__(self, client, bucket):
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        """Send `request` through the wrapped client, or raise RateLimitExceeded."""
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: no token available")
+        return self._client.send(request)
+
+
+def _is_int(value):
+    # bool is a subclass of int, but True/False are not meaningful counts.
+    return isinstance(value, int) and not isinstance(value, bool)
+
+
+def _is_real(value):
+    return isinstance(value, Real) and not isinstance(value, bool)
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,190 @@
+import threading
+
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    def __init__(self, now=0.0):
+        self.now = now
+
+    def __call__(self):
+        return self.now
+
+    def advance(self, seconds):
+        self.now += seconds
+
+
+class RecordingClient:
+    def __init__(self):
+        self.requests = []
+
+    def send(self, request):
+        self.requests.append(request)
+        return f"response to {request}"
+
+
+@pytest.fixture
+def clock():
+    return FakeClock()
+
+
+# --- TokenBucket construction ---
+
+@pytest.mark.parametrize("capacity", [0, -1, 1.0, 2.5, "3", None, True])
+def test_rejects_invalid_capacity(capacity):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity, 1)
+
+
+@pytest.mark.parametrize("rate", [0, -0.5, float("nan"), float("inf"), "1", None, True])
+def test_rejects_invalid_refill_rate(rate):
+    with pytest.raises(ValueError):
+        TokenBucket(1, rate)
+
+
+def test_rejects_non_callable_clock():
+    with pytest.raises(ValueError):
+        TokenBucket(1, 1, clock=5)
+
+
+def test_accepts_fractional_refill_rate(clock):
+    bucket = TokenBucket(1, 0.25, clock=clock)
+    assert bucket.refill_rate == 0.25
+
+
+def test_uses_monotonic_clock_by_default():
+    bucket = TokenBucket(2, 1)
+    assert bucket.try_acquire(2) is True
+    assert bucket.try_acquire() is False
+
+
+# --- try_acquire ---
+
+def test_starts_full(clock):
+    bucket = TokenBucket(3, 1, clock=clock)
+    assert bucket.try_acquire(3) is True
+    assert bucket.try_acquire() is False
+
+
+def test_failed_acquire_consumes_nothing(clock):
+    bucket = TokenBucket(3, 1, clock=clock)
+    assert bucket.try_acquire(2) is True
+    assert bucket.try_acquire(2) is False
+    assert bucket.try_acquire(1) is True
+    assert bucket.try_acquire(1) is False
+
+
+def test_refills_continuously_with_elapsed_time(clock):
+    bucket = TokenBucket(5, 2, clock=clock)
+    assert bucket.try_acquire(5) is True
+    clock.advance(0.25)
+    assert bucket.try_acquire() is False  # only 0.5 tokens so far
+    clock.advance(0.25)
+    assert bucket.try_acquire() is True
+    assert bucket.try_acquire() is False
+
+
+def test_refill_is_capped_at_capacity(clock):
+    bucket = TokenBucket(3, 10, clock=clock)
+    assert bucket.try_acquire(3) is True
+    clock.advance(1000)
+    assert bucket.try_acquire(3) is True
+    assert bucket.try_acquire() is False
+
+
+def test_failed_attempts_do_not_delay_refill(clock):
+    bucket = TokenBucket(1, 0.1, clock=clock)
+    assert bucket.try_acquire() is True
+    for _ in range(9):
+        clock.advance(1)
+        assert bucket.try_acquire() is False
+    clock.advance(1)
+    assert bucket.try_acquire() is True
+
+
+def test_float_rounding_does_not_lose_a_token(clock):
+    clock.now = 0.1
+    bucket = TokenBucket(2, 10, clock=clock)
+    assert bucket.try_acquire(2) is True
+    clock.now = 0.3  # (0.3 - 0.1) * 10 == 1.9999999999999998 in floating point
+    assert bucket.try_acquire(2) is True
+
+
+def test_clock_going_backwards_does_not_drain_or_overfill(clock):
+    clock.now = 100.0
+    bucket = TokenBucket(2, 1, clock=clock)
+    assert bucket.try_acquire() is True
+    clock.now = 50.0
+    assert bucket.try_acquire() is True
+    assert bucket.try_acquire() is False
+    clock.now = 100.5
+    assert bucket.try_acquire() is False
+    clock.now = 101.0
+    assert bucket.try_acquire() is True
+
+
+@pytest.mark.parametrize("tokens", [0, -1, 4, 1.0, "1", None, True])
+def test_rejects_invalid_token_count(clock, tokens):
+    bucket = TokenBucket(3, 1, clock=clock)
+    with pytest.raises(ValueError):
+        bucket.try_acquire(tokens)
+    assert bucket.try_acquire(3) is True  # nothing consumed by the bad call
+
+
+def test_concurrent_acquires_never_exceed_capacity(clock):
+    bucket = TokenBucket(100, 1, clock=clock)
+    results = []
+    results_lock = threading.Lock()
+
+    def worker():
+        for _ in range(50):
+            ok = bucket.try_acquire()
+            with results_lock:
+                results.append(ok)
+
+    threads = [threading.Thread(target=worker) for _ in range(8)]
+    for thread in threads:
+        thread.start()
+    for thread in threads:
+        thread.join()
+
+    assert results.count(True) == 100
+
+
+# --- RateLimitedClient ---
+
+def test_forwards_request_and_returns_result(clock):
+    inner = RecordingClient()
+    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
+    assert client.send("ping") == "response to ping"
+    assert inner.requests == ["ping"]
+
+
+def test_raises_without_calling_client_when_limited(clock):
+    inner = RecordingClient()
+    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
+    client.send("first")
+    with pytest.raises(RateLimitExceeded):
+        client.send("second")
+    assert inner.requests == ["first"]
+
+
+def test_allows_requests_again_after_refill(clock):
+    inner = RecordingClient()
+    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
+    client.send("first")
+    clock.advance(1)
+    assert client.send("second") == "response to second"
+    assert inner.requests == ["first", "second"]
+
+
+def test_client_errors_propagate(clock):
+    class FailingClient:
+        def send(self, request):
+            raise ConnectionError("down")
+
+    client = RateLimitedClient(FailingClient(), TokenBucket(1, 1, clock=clock))
+    with pytest.raises(ConnectionError):
+        client.send("ping")
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,118 @@
+"""Token-bucket rate limiting, and a client wrapper that enforces it."""
+
+import math
+import numbers
+import threading
+import time
+from collections.abc import Callable
+from typing import Generic, Protocol, TypeVar
+
+RequestT_contra = TypeVar("RequestT_contra", contravariant=True)
+ResponseT_co = TypeVar("ResponseT_co", covariant=True)
+
+
+class TokenBucket:
+    """A token-bucket rate limiter.
+
+    Holds at most ``capacity`` tokens and starts full. Tokens refill continuously
+    at ``refill_rate`` tokens per second, measured with ``clock`` (seconds).
+    Safe to share between threads.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        _validate_bucket_arguments(capacity, refill_rate, clock)
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._lock = threading.Lock()
+        self._available_tokens: float = capacity
+        self._last_refill_time = clock()
+
+    def try_acquire(self, tokens: int = 1) -> bool:
+        """Consume ``tokens`` and return True if that many are available.
+
+        Otherwise return False and consume nothing. Raises ValueError unless
+        ``tokens`` is an integer from 1 to ``capacity``.
+        """
+        if not (_is_integer(tokens) and 1 <= tokens <= self._capacity):
+            raise ValueError(
+                f"tokens must be an integer from 1 to capacity ({self._capacity}), "
+                f"got {tokens!r}"
+            )
+        with self._lock:
+            self._refill()
+            if self._available_tokens < tokens:
+                return False
+            self._available_tokens -= tokens
+            return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        # An injected clock may step backwards; that must add nothing, not drain tokens.
+        elapsed_seconds = max(0.0, now - self._last_refill_time)
+        self._available_tokens = min(
+            self._capacity,
+            self._available_tokens + elapsed_seconds * self._refill_rate,
+        )
+        self._last_refill_time = now
+
+
+def _validate_bucket_arguments(
+    capacity: int, refill_rate: float, clock: Callable[[], float]
+) -> None:
+    if not (_is_integer(capacity) and capacity > 0):
+        raise ValueError(
+            f"capacity must be an integer greater than 0, got {capacity!r}"
+        )
+    if not (_is_real(refill_rate) and math.isfinite(refill_rate) and refill_rate > 0):
+        raise ValueError(
+            f"refill_rate must be a finite number greater than 0, got {refill_rate!r}"
+        )
+    if not callable(clock):
+        # The contract is ValueError for every invalid argument, wrong types included.
+        message = f"clock must be a zero-argument callable, got {clock!r}"
+        raise ValueError(message)  # noqa: TRY004
+
+
+def _is_integer(value: object) -> bool:
+    # bool is an int subclass, but True/False as a count is almost always a bug.
+    return isinstance(value, numbers.Integral) and not isinstance(value, bool)
+
+
+def _is_real(value: object) -> bool:
+    return isinstance(value, numbers.Real) and not isinstance(value, bool)
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no rate-limit token is available."""
+
+
+class SupportsSend(Protocol[RequestT_contra, ResponseT_co]):
+    def send(self, request: RequestT_contra, /) -> ResponseT_co: ...
+
+
+class RateLimitedClient(Generic[RequestT_contra, ResponseT_co]):
+    """Wraps a client so that every ``send`` must first take a token from ``bucket``."""
+
+    def __init__(
+        self,
+        client: SupportsSend[RequestT_contra, ResponseT_co],
+        bucket: TokenBucket,
+    ) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request: RequestT_contra) -> ResponseT_co:
+        """Forward ``request`` to the wrapped client and return its result.
+
+        Raises RateLimitExceeded, without calling the client, when no token is
+        available. The token is spent even if the client then fails.
+        """
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: request was not sent")
+        return self._client.send(request)
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,188 @@
+import math
+import sys
+from collections.abc import Iterator
+from concurrent.futures import ThreadPoolExecutor
+from typing import Any
+
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    """A clock, in seconds, that moves only when the test advances it."""
+
+    def __init__(self) -> None:
+        self._now = 1000.0
+
+    def __call__(self) -> float:
+        return self._now
+
+    def advance(self, seconds: float) -> None:
+        self._now += seconds
+
+
+class RecordingClient:
+    def __init__(self) -> None:
+        self.requests: list[str] = []
+
+    def send(self, request: str) -> str:
+        self.requests.append(request)
+        return f"response to {request}"
+
+
+@pytest.fixture
+def clock() -> FakeClock:
+    return FakeClock()
+
+
+def test_new_bucket_starts_full(clock: FakeClock) -> None:
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+
+    results = [bucket.try_acquire() for _ in range(4)]
+
+    assert results == [True, True, True, False]
+
+
+def test_acquiring_the_whole_capacity_at_once_empties_the_bucket(
+    clock: FakeClock,
+) -> None:
+    bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
+
+    assert bucket.try_acquire(5)
+    assert not bucket.try_acquire()
+
+
+def test_failed_acquire_consumes_nothing(clock: FakeClock) -> None:
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+    bucket.try_acquire(2)
+
+    assert not bucket.try_acquire(2)
+    assert bucket.try_acquire(1)
+
+
+def test_tokens_refill_at_refill_rate_per_second(clock: FakeClock) -> None:
+    bucket = TokenBucket(capacity=4, refill_rate=0.5, clock=clock)
+    bucket.try_acquire(4)
+
+    clock.advance(4.0)
+
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+def test_partial_refills_accumulate_across_calls(clock: FakeClock) -> None:
+    bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)
+    bucket.try_acquire()
+
+    clock.advance(0.5)
+    assert not bucket.try_acquire()
+    clock.advance(0.5)
+    assert bucket.try_acquire()
+
+
+def test_refill_stops_at_capacity(clock: FakeClock) -> None:
+    bucket = TokenBucket(capacity=2, refill_rate=10, clock=clock)
+    bucket.try_acquire(2)
+
+    clock.advance(60.0)
+
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+def test_clock_stepping_backwards_does_not_remove_tokens(clock: FakeClock) -> None:
+    bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)
+
+    clock.advance(-10.0)
+
+    assert bucket.try_acquire()
+
+
+def test_works_with_the_default_clock() -> None:
+    bucket = TokenBucket(capacity=1, refill_rate=1)
+
+    assert bucket.try_acquire()
+
+
+@pytest.fixture
+def frequent_thread_switches() -> Iterator[None]:
+    """Make the interpreter switch threads very often, so that races surface."""
+    original_interval = sys.getswitchinterval()
+    sys.setswitchinterval(1e-6)
+    yield
+    sys.setswitchinterval(original_interval)
+
+
+@pytest.mark.usefixtures("frequent_thread_switches")
+def test_concurrent_acquires_never_hand_out_more_than_capacity() -> None:
+    capacity, attempts_per_round, rounds = 100, 300, 20
+
+    # A single round seldom exposes a race, so several are run.
+    with ThreadPoolExecutor(max_workers=8) as pool:
+        granted_per_round = [
+            count_grants(
+                pool,
+                TokenBucket(capacity, refill_rate=1, clock=FakeClock()),
+                attempts_per_round,
+            )
+            for _ in range(rounds)
+        ]
+
+    assert granted_per_round == [capacity] * rounds
+
+
+def count_grants(pool: ThreadPoolExecutor, bucket: TokenBucket, attempts: int) -> int:
+    return sum(pool.map(lambda _: bucket.try_acquire(), range(attempts)))
+
+
+@pytest.mark.parametrize("capacity", [0, -1, 2.5, "3", True, None])
+def test_rejects_invalid_capacity(capacity: Any) -> None:
+    with pytest.raises(ValueError, match="capacity"):
+        TokenBucket(capacity=capacity, refill_rate=1)
+
+
+@pytest.mark.parametrize("refill_rate", [0, -0.5, math.nan, math.inf, "1", True, None])
+def test_rejects_invalid_refill_rate(refill_rate: Any) -> None:
+    with pytest.raises(ValueError, match="refill_rate"):
+        TokenBucket(capacity=1, refill_rate=refill_rate)
+
+
+@pytest.mark.parametrize("not_a_clock", [None, 42])
+def test_rejects_a_clock_that_is_not_callable(not_a_clock: Any) -> None:
+    with pytest.raises(ValueError, match="clock"):
+        TokenBucket(capacity=1, refill_rate=1, clock=not_a_clock)
+
+
+@pytest.mark.parametrize("tokens", [0, -1, 4, 1.5, "1", True])
+def test_rejects_token_counts_outside_one_to_capacity(
+    clock: FakeClock, tokens: Any
+) -> None:
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+
+    with pytest.raises(ValueError, match="tokens"):
+        bucket.try_acquire(tokens)
+
+
+def test_send_forwards_the_request_and_returns_the_response(clock: FakeClock) -> None:
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(1, refill_rate=1, clock=clock))
+
+    response = limited.send("ping")
+
+    assert response == "response to ping"
+    assert client.requests == ["ping"]
+
+
+def test_send_spends_one_token_and_raises_without_calling_client_when_empty(
+    clock: FakeClock,
+) -> None:
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(2, refill_rate=1, clock=clock))
+    limited.send("first")
+    limited.send("second")
+
+    with pytest.raises(RateLimitExceeded):
+        limited.send("third")
+
+    assert client.requests == ["first", "second"]
```

### Implementation 2

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,91 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+import math
+import threading
+import time
+from collections.abc import Callable
+from numbers import Real
+from typing import Any, Protocol
+
+# Refilling adds small float amounts over many calls, so the total can land a
+# hair short of a whole token (ten refills of 0.1 sum to 0.9999999999999999).
+# Amounts this close to the request count as enough, so such requests still pass.
+_FLOAT_TOLERANCE = 1e-9
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is refused because no token is available."""
+
+
+class SupportsSend(Protocol):
+    def send(self, request: Any) -> Any: ...
+
+
+def _is_real_number(value: object) -> bool:
+    # bool is a subclass of int, but True/False are never meant as quantities.
+    return isinstance(value, Real) and not isinstance(value, bool)
+
+
+class TokenBucket:
+    """A bucket of up to `capacity` tokens, refilled at `refill_rate` tokens per second.
+
+    The bucket starts full. It is safe to share between threads.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
+        if not _is_real_number(refill_rate) or not math.isfinite(refill_rate) or refill_rate <= 0:
+            raise ValueError(f"refill_rate must be a finite number greater than 0, got {refill_rate!r}")
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._tokens = float(capacity)
+        self._last_refill = clock()
+        self._lock = threading.Lock()
+
+    def try_acquire(self, tokens: float = 1) -> bool:
+        """Consume `tokens` and return True if enough are available; otherwise consume nothing and return False."""
+        if not _is_real_number(tokens) or not 1 <= tokens <= self._capacity:
+            raise ValueError(f"tokens must be between 1 and capacity ({self._capacity}), got {tokens!r}")
+
+        with self._lock:
+            self._refill()
+            if not self._has_at_least(tokens):
+                return False
+            self._tokens = max(0.0, self._tokens - tokens)
+            return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        elapsed = now - self._last_refill
+        # A clock that stalls or steps backwards must neither drain the bucket
+        # nor move the reference point back (which would over-refill later).
+        if elapsed <= 0:
+            return
+        self._tokens = min(float(self._capacity), self._tokens + elapsed * self._refill_rate)
+        self._last_refill = now
+
+    def _has_at_least(self, tokens: float) -> bool:
+        return self._tokens >= tokens or math.isclose(self._tokens, tokens, rel_tol=_FLOAT_TOLERANCE)
+
+
+class RateLimitedClient:
+    """Forwards `send` calls to `client` only while `bucket` has a token to spend."""
+
+    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request: Any) -> Any:
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded; the request was not sent")
+        return self._client.send(request)
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,108 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+import math
+import threading
+import time
+from numbers import Integral, Real
+
+# Slack used when checking whether enough tokens are available. Without it,
+# refills that should add up to a whole token can fall just short because of
+# float rounding (for example, ten 0.1 s clock steps at 1 token per second).
+_FLOAT_TOLERANCE = 1e-9
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+class TokenBucket:
+    """A thread-safe token bucket.
+
+    The bucket holds at most ``capacity`` tokens and starts full. Tokens are
+    added continuously at ``refill_rate`` tokens per second of ``clock`` time.
+    """
+
+    def __init__(self, capacity, refill_rate, clock=time.monotonic):
+        if not _is_int(capacity) or capacity <= 0:
+            raise ValueError(
+                f"capacity must be an integer greater than 0, got {capacity!r}"
+            )
+        if not _is_positive_finite_number(refill_rate):
+            raise ValueError(
+                f"refill_rate must be a finite number greater than 0, got {refill_rate!r}"
+            )
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+
+        self._capacity = capacity
+        self._refill_rate = float(refill_rate)
+        self._clock = clock
+        self._tokens = float(capacity)
+        self._last_refill = clock()
+        self._lock = threading.Lock()
+
+    def try_acquire(self, tokens=1):
+        """Consume ``tokens`` and return True, or return False and consume nothing.
+
+        ``tokens`` must be an integer from 1 to ``capacity``; anything else
+        raises ValueError, because such a request could never be satisfied.
+        """
+        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be an integer from 1 to {self._capacity}, got {tokens!r}"
+            )
+
+        with self._lock:
+            self._refill()
+            if self._tokens + _FLOAT_TOLERANCE < tokens:
+                return False
+            self._tokens = max(0.0, self._tokens - tokens)
+            return True
+
+    def _refill(self):
+        now = self._clock()
+        elapsed = now - self._last_refill
+        if elapsed <= 0:
+            # A clock that stalls or steps backwards adds nothing. Keeping the
+            # later timestamp stops the same interval from being credited twice.
+            return
+        self._tokens = min(
+            float(self._capacity), self._tokens + elapsed * self._refill_rate
+        )
+        self._last_refill = now
+
+
+class RateLimitedClient:
+    """Wraps an object with a ``send(request)`` method and rate-limits its calls.
+
+    Each call to ``send`` takes one token from ``bucket``. The token is spent
+    even if the wrapped client then raises, since the request was attempted.
+    """
+
+    def __init__(self, client, bucket):
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        """Forward ``request`` to the wrapped client and return its result.
+
+        Raises RateLimitExceeded, without calling the client, if no token is
+        available.
+        """
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded; the request was not sent")
+        return self._client.send(request)
+
+
+def _is_int(value):
+    # bool is a subclass of int, but True/False are not meaningful counts.
+    return isinstance(value, Integral) and not isinstance(value, bool)
+
+
+def _is_positive_finite_number(value):
+    return (
+        isinstance(value, Real)
+        and not isinstance(value, bool)
+        and value > 0
+        and math.isfinite(value)
+    )
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,224 @@
+import threading
+
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    def __init__(self, now=0.0):
+        self.now = now
+
+    def __call__(self):
+        return self.now
+
+    def advance(self, seconds):
+        self.now += seconds
+
+
+class RecordingClient:
+    def __init__(self):
+        self.requests = []
+
+    def send(self, request):
+        self.requests.append(request)
+        return f"response to {request}"
+
+
+@pytest.fixture
+def clock():
+    return FakeClock()
+
+
+# --- TokenBucket construction ---------------------------------------------
+
+
+@pytest.mark.parametrize("capacity", [0, -1, 1.5, 2.0, "3", None, True])
+def test_rejects_invalid_capacity(capacity, clock):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity, 1, clock=clock)
+
+
+@pytest.mark.parametrize(
+    "refill_rate", [0, -1, -0.5, float("nan"), float("inf"), "1", None, True]
+)
+def test_rejects_invalid_refill_rate(refill_rate, clock):
+    with pytest.raises(ValueError):
+        TokenBucket(1, refill_rate, clock=clock)
+
+
+def test_rejects_non_callable_clock():
+    with pytest.raises(ValueError):
+        TokenBucket(1, 1, clock=0.0)
+
+
+def test_accepts_fractional_refill_rate(clock):
+    bucket = TokenBucket(1, 0.5, clock=clock)
+    assert bucket.try_acquire()
+
+
+def test_uses_monotonic_clock_by_default():
+    bucket = TokenBucket(2, 1)
+    assert bucket.try_acquire(2)
+
+
+# --- TokenBucket.try_acquire ----------------------------------------------
+
+
+def test_starts_full(clock):
+    bucket = TokenBucket(3, 1, clock=clock)
+    assert [bucket.try_acquire() for _ in range(4)] == [True, True, True, False]
+
+
+def test_acquires_several_tokens_at_once(clock):
+    bucket = TokenBucket(5, 1, clock=clock)
+    assert bucket.try_acquire(3)
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+def test_failed_acquire_consumes_nothing(clock):
+    bucket = TokenBucket(5, 1, clock=clock)
+    assert bucket.try_acquire(3)
+    assert not bucket.try_acquire(3)
+    assert bucket.try_acquire(2)
+
+
+@pytest.mark.parametrize("tokens", [0, -1, 6, 1.0, 1.5, "1", None, True])
+def test_rejects_invalid_token_count(tokens, clock):
+    bucket = TokenBucket(5, 1, clock=clock)
+    with pytest.raises(ValueError):
+        bucket.try_acquire(tokens)
+
+
+def test_invalid_token_count_consumes_nothing(clock):
+    bucket = TokenBucket(2, 1, clock=clock)
+    with pytest.raises(ValueError):
+        bucket.try_acquire(3)
+    assert bucket.try_acquire(2)
+
+
+def test_refills_continuously(clock):
+    bucket = TokenBucket(2, 2, clock=clock)
+    assert bucket.try_acquire(2)
+
+    clock.advance(0.25)  # 0.5 tokens
+    assert not bucket.try_acquire()
+
+    clock.advance(0.25)  # 1 token
+    assert bucket.try_acquire()
+    assert not bucket.try_acquire()
+
+
+def test_partial_tokens_carry_over(clock):
+    bucket = TokenBucket(1, 1, clock=clock)
+    assert bucket.try_acquire()
+
+    clock.advance(0.6)
+    assert not bucket.try_acquire()
+    clock.advance(0.4)
+    assert bucket.try_acquire()
+
+
+def test_refill_is_capped_at_capacity(clock):
+    bucket = TokenBucket(3, 10, clock=clock)
+    assert bucket.try_acquire(3)
+
+    clock.advance(1000)
+    assert bucket.try_acquire(3)
+    assert not bucket.try_acquire()
+
+
+def test_ten_tenth_second_steps_refill_one_token(clock):
+    # 0.1 added ten times is slightly less than 1.0 in floating point.
+    bucket = TokenBucket(1, 1, clock=clock)
+    assert bucket.try_acquire()
+
+    for _ in range(9):
+        clock.advance(0.1)
+        assert not bucket.try_acquire()
+    clock.advance(0.1)
+    assert bucket.try_acquire()
+
+
+def test_backwards_clock_does_not_add_or_remove_tokens(clock):
+    clock.now = 100.0
+    bucket = TokenBucket(2, 1, clock=clock)
+    assert bucket.try_acquire(2)
+
+    clock.now = 50.0
+    assert not bucket.try_acquire()
+
+    # The interval up to the previous high-water mark is not credited again.
+    clock.now = 100.5
+    assert not bucket.try_acquire()
+    clock.now = 101.0
+    assert bucket.try_acquire()
+
+
+def test_concurrent_acquires_never_exceed_capacity(clock):
+    bucket = TokenBucket(100, 1, clock=clock)
+    results = []
+    lock = threading.Lock()
+
+    def worker():
+        for _ in range(50):
+            acquired = bucket.try_acquire()
+            with lock:
+                results.append(acquired)
+
+    threads = [threading.Thread(target=worker) for _ in range(8)]
+    for thread in threads:
+        thread.start()
+    for thread in threads:
+        thread.join()
+
+    assert results.count(True) == 100
+
+
+# --- RateLimitedClient ----------------------------------------------------
+
+
+def test_client_forwards_request_and_returns_result(clock):
+    inner = RecordingClient()
+    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
+
+    assert client.send("ping") == "response to ping"
+    assert inner.requests == ["ping"]
+
+
+def test_client_raises_without_calling_inner_when_limited(clock):
+    inner = RecordingClient()
+    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
+    client.send("first")
+
+    with pytest.raises(RateLimitExceeded):
+        client.send("second")
+    assert inner.requests == ["first"]
+
+
+def test_client_recovers_after_refill(clock):
+    inner = RecordingClient()
+    client = RateLimitedClient(inner, TokenBucket(1, 1, clock=clock))
+    client.send("first")
+
+    clock.advance(1)
+    assert client.send("second") == "response to second"
+    assert inner.requests == ["first", "second"]
+
+
+def test_client_spends_token_even_if_inner_client_fails(clock):
+    class FailingClient:
+        def send(self, request):
+            raise ConnectionError("down")
+
+    client = RateLimitedClient(FailingClient(), TokenBucket(1, 1, clock=clock))
+
+    with pytest.raises(ConnectionError):
+        client.send("x")
+    with pytest.raises(RateLimitExceeded):
+        client.send("y")
+
+
+def test_rate_limit_exceeded_is_an_exception():
+    assert issubclass(RateLimitExceeded, Exception)
```

### Implementation 2

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,100 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+import math
+import numbers
+import threading
+import time
+from collections.abc import Callable
+from typing import Any, Protocol
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available for it."""
+
+
+class TokenBucket:
+    """Admits work at a sustained rate, with bursts of up to ``capacity`` tokens.
+
+    The bucket starts full and refills continuously at ``refill_rate`` tokens per
+    second of ``clock`` time. One instance can be shared between threads.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not _is_positive_integer(capacity):
+            raise ValueError(
+                f"capacity must be an integer greater than 0, got {capacity!r}"
+            )
+        if not _is_positive_finite_number(refill_rate):
+            raise ValueError(
+                "refill_rate must be a finite number greater than 0, "
+                f"got {refill_rate!r}"
+            )
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._tokens: float = capacity
+        self._last_refill = clock()
+        self._lock = threading.Lock()
+
+    def try_acquire(self, tokens: float = 1) -> bool:
+        """Consume ``tokens`` and return True, or return False and consume nothing.
+
+        Raises ValueError unless ``1 <= tokens <= capacity``.
+        """
+        if not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be between 1 and capacity ({self._capacity}), "
+                f"got {tokens!r}"
+            )
+        with self._lock:
+            self._refill()
+            if self._tokens < tokens:
+                return False
+            self._tokens -= tokens
+            return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        # An injected clock may step backwards (time.time can); that must not drain
+        # tokens. The re-counted time afterwards is harmless: refill caps at capacity.
+        elapsed = max(0.0, now - self._last_refill)
+        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
+        self._last_refill = now
+
+
+class SupportsSend(Protocol):
+    """Any client that can send a request and return its result."""
+
+    def send(self, request: Any) -> Any: ...
+
+
+class RateLimitedClient:
+    """Forwards ``send`` calls to a client only while the bucket has a token."""
+
+    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request: Any) -> Any:
+        """Return ``client.send(request)`` if a token is available.
+
+        Raises RateLimitExceeded, without calling the client, when none is.
+        """
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: the request was not sent")
+        return self._client.send(request)
+
+
+def _is_positive_integer(value: object) -> bool:
+    is_integer = isinstance(value, numbers.Integral) and not isinstance(value, bool)
+    return is_integer and value > 0
+
+
+def _is_positive_finite_number(value: object) -> bool:
+    is_number = isinstance(value, numbers.Real) and not isinstance(value, bool)
+    return is_number and math.isfinite(value) and value > 0
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,187 @@
+import math
+from concurrent.futures import ThreadPoolExecutor
+
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    """A clock that only moves when the test advances it."""
+
+    def __init__(self) -> None:
+        self._now = 0.0
+
+    def __call__(self) -> float:
+        return self._now
+
+    def advance(self, seconds: float) -> None:
+        self._now += seconds
+
+
+class RecordingClient:
+    """A client fake that records every request it receives."""
+
+    def __init__(self) -> None:
+        self.sent_requests: list[object] = []
+
+    def send(self, request: object) -> str:
+        self.sent_requests.append(request)
+        return f"response to {request}"
+
+
+@pytest.fixture
+def clock() -> FakeClock:
+    return FakeClock()
+
+
+def empty_bucket(clock: FakeClock, capacity: int, refill_rate: float) -> TokenBucket:
+    bucket = TokenBucket(capacity=capacity, refill_rate=refill_rate, clock=clock)
+    bucket.try_acquire(capacity)
+    return bucket
+
+
+class TestTokenBucketAcquire:
+    def test_new_bucket_starts_full(self, clock):
+        bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+
+        results = [bucket.try_acquire() for _ in range(4)]
+
+        assert results == [True, True, True, False]
+
+    def test_whole_capacity_can_be_acquired_at_once(self, clock):
+        bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
+
+        assert bucket.try_acquire(5) is True
+
+    def test_failed_acquire_consumes_nothing(self, clock):
+        bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+        bucket.try_acquire(2)
+
+        assert bucket.try_acquire(2) is False
+        assert bucket.try_acquire(1) is True
+
+    def test_works_with_default_clock(self):
+        bucket = TokenBucket(capacity=1, refill_rate=1)
+
+        assert bucket.try_acquire() is True
+
+    def test_concurrent_acquires_never_admit_more_than_capacity(self, clock):
+        capacity = 1000
+        bucket = TokenBucket(capacity=capacity, refill_rate=1, clock=clock)
+
+        def count_successes(attempts: int) -> int:
+            return sum(bucket.try_acquire() for _ in range(attempts))
+
+        with ThreadPoolExecutor(max_workers=8) as executor:
+            admitted = sum(executor.map(count_successes, [250] * 8))
+
+        assert admitted == capacity
+
+
+class TestTokenBucketRefill:
+    def test_refills_a_token_after_its_share_of_time(self, clock):
+        bucket = empty_bucket(clock, capacity=2, refill_rate=4)
+
+        clock.advance(0.25)
+
+        assert bucket.try_acquire() is True
+
+    def test_does_not_refill_a_token_before_its_share_of_time(self, clock):
+        bucket = empty_bucket(clock, capacity=2, refill_rate=4)
+
+        clock.advance(0.2)
+
+        assert bucket.try_acquire() is False
+
+    def test_partial_refills_accumulate_across_failed_attempts(self, clock):
+        bucket = empty_bucket(clock, capacity=1, refill_rate=2)
+        clock.advance(0.25)
+        bucket.try_acquire()
+
+        clock.advance(0.25)
+
+        assert bucket.try_acquire() is True
+
+    def test_fractional_refill_rate_refills_slower_than_one_per_second(self, clock):
+        bucket = empty_bucket(clock, capacity=1, refill_rate=0.5)
+
+        clock.advance(1.5)
+        too_early = bucket.try_acquire()
+        clock.advance(0.5)
+        on_time = bucket.try_acquire()
+
+        assert (too_early, on_time) == (False, True)
+
+    def test_refill_stops_at_capacity(self, clock):
+        bucket = empty_bucket(clock, capacity=2, refill_rate=10)
+
+        clock.advance(60)
+
+        assert bucket.try_acquire(2) is True
+        assert bucket.try_acquire() is False
+
+    def test_clock_stepping_backwards_does_not_remove_tokens(self, clock):
+        bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)
+
+        clock.advance(-10)
+
+        assert bucket.try_acquire(2) is True
+
+
+class TestTokenBucketValidation:
+    @pytest.mark.parametrize("capacity", [0, -1, 2.0, 2.5, "3", True, None])
+    def test_rejects_capacity_that_is_not_a_positive_integer(self, capacity):
+        with pytest.raises(ValueError, match="capacity"):
+            TokenBucket(capacity=capacity, refill_rate=1)
+
+    @pytest.mark.parametrize(
+        "refill_rate", [0, -0.5, math.nan, math.inf, "1", True, None]
+    )
+    def test_rejects_refill_rate_that_is_not_a_positive_finite_number(
+        self, refill_rate
+    ):
+        with pytest.raises(ValueError, match="refill_rate"):
+            TokenBucket(capacity=1, refill_rate=refill_rate)
+
+    @pytest.mark.parametrize("tokens", [0, 0.5, -1, 4, math.nan])
+    def test_try_acquire_rejects_tokens_outside_one_to_capacity(self, clock, tokens):
+        bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+
+        with pytest.raises(ValueError, match="tokens"):
+            bucket.try_acquire(tokens)
+
+
+class TestRateLimitedClient:
+    def test_forwards_request_and_returns_client_result(self, clock):
+        client = RecordingClient()
+        bucket = TokenBucket(capacity=1, refill_rate=1, clock=clock)
+        limited_client = RateLimitedClient(client, bucket)
+
+        response = limited_client.send("ping")
+
+        assert response == "response to ping"
+        assert client.sent_requests == ["ping"]
+
+    def test_raises_without_calling_client_when_no_token_is_available(self, clock):
+        client = RecordingClient()
+        limited_client = RateLimitedClient(
+            client, empty_bucket(clock, capacity=1, refill_rate=1)
+        )
+
+        with pytest.raises(RateLimitExceeded):
+            limited_client.send("ping")
+
+        assert client.sent_requests == []
+
+    def test_each_send_consumes_one_token(self, clock):
+        client = RecordingClient()
+        bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)
+        limited_client = RateLimitedClient(client, bucket)
+        limited_client.send("first")
+        limited_client.send("second")
+
+        with pytest.raises(RateLimitExceeded):
+            limited_client.send("third")
+
+        assert client.sent_requests == ["first", "second"]
```

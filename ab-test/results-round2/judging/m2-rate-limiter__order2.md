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
@@ -0,0 +1,101 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+import math
+import numbers
+import threading
+import time
+
+# Tolerance for float rounding in refill arithmetic, so that e.g. 0.1 s at
+# 10 tokens/s reliably yields a whole token rather than 0.9999999999999999.
+_EPSILON = 1e-9
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+def _is_int(value):
+    return isinstance(value, numbers.Integral) and not isinstance(value, bool)
+
+
+def _is_real(value):
+    return isinstance(value, numbers.Real) and not isinstance(value, bool)
+
+
+class TokenBucket:
+    """A thread-safe token bucket that refills continuously with clock time.
+
+    The bucket starts full. Each call to ``try_acquire`` first credits the
+    tokens earned since the previous call (capped at ``capacity``), then
+    either consumes the requested tokens or leaves the bucket untouched.
+    """
+
+    def __init__(self, capacity, refill_rate, clock=time.monotonic):
+        if not _is_int(capacity) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer > 0, got {capacity!r}")
+        if not _is_real(refill_rate) or not math.isfinite(refill_rate) or refill_rate <= 0:
+            raise ValueError(f"refill_rate must be a finite number > 0, got {refill_rate!r}")
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
+    @property
+    def capacity(self):
+        return self._capacity
+
+    @property
+    def refill_rate(self):
+        return self._refill_rate
+
+    def try_acquire(self, tokens=1):
+        """Consume ``tokens`` and return True if available, else return False.
+
+        ``tokens`` must be an integer between 1 and ``capacity`` inclusive;
+        anything else raises ``ValueError`` because it could never succeed.
+        """
+        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be an integer between 1 and {self._capacity}, got {tokens!r}"
+            )
+
+        with self._lock:
+            self._refill()
+            if self._tokens + _EPSILON < tokens:
+                return False
+            self._tokens = max(0.0, self._tokens - tokens)
+            return True
+
+    def _refill(self):
+        now = self._clock()
+        # A clock that steps backwards earns nothing; keeping the later
+        # timestamp avoids crediting the same interval twice.
+        if now <= self._last_refill:
+            return
+        earned = (now - self._last_refill) * self._refill_rate
+        self._tokens = min(float(self._capacity), self._tokens + earned)
+        self._last_refill = now
+
+
+class RateLimitedClient:
+    """Wraps an object with a ``send(request)`` method and rate-limits it.
+
+    Each call to ``send`` costs one token from ``bucket``. A token spent on a
+    request is not refunded if the wrapped client raises.
+    """
+
+    def __init__(self, client, bucket):
+        if not callable(getattr(client, "send", None)):
+            raise TypeError(f"client must have a callable send(request) method, got {client!r}")
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: no token available")
+        return self._client.send(request)
```

### Implementation 2

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,70 @@
+"""Token-bucket rate limiting, and a client wrapper that applies it to sends."""
+
+import time
+from typing import Callable
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+class TokenBucket:
+    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` tokens per second.
+
+    The bucket starts full. `clock` returns the current time in seconds.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not isinstance(capacity, int) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
+        if refill_rate <= 0:
+            raise ValueError(f"refill_rate must be greater than 0, got {refill_rate!r}")
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._available_tokens: float = capacity
+        self._last_refill_time = clock()
+
+    def try_acquire(self, tokens: int = 1) -> bool:
+        """Consume `tokens` and return True if enough are available.
+
+        Otherwise consume nothing and return False.
+        """
+        if not 1 <= tokens <= self._capacity:
+            raise ValueError(f"tokens must be between 1 and {self._capacity}, got {tokens!r}")
+        self._refill()
+        if self._available_tokens < tokens:
+            return False
+        self._available_tokens -= tokens
+        return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        elapsed_seconds = now - self._last_refill_time
+        self._available_tokens = min(
+            self._capacity,
+            self._available_tokens + elapsed_seconds * self._refill_rate,
+        )
+        self._last_refill_time = now
+
+
+class RateLimitedClient:
+    """Wraps any object with a `send(request)` method, sending only while `bucket` has tokens."""
+
+    def __init__(self, client, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        """Forward `request` to the wrapped client and return its result.
+
+        Raises RateLimitExceeded, without calling the client, when no token is available.
+        """
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: no token available, request not sent")
+        return self._client.send(request)
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,128 @@
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    def __init__(self) -> None:
+        self.now = 0.0
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
+        self.sent_requests = []
+
+    def send(self, request):
+        self.sent_requests.append(request)
+        return f"response to {request}"
+
+
+def drained_bucket(clock: FakeClock, capacity: int = 2, refill_rate: float = 2) -> TokenBucket:
+    bucket = TokenBucket(capacity, refill_rate, clock=clock)
+    assert bucket.try_acquire(capacity)
+    return bucket
+
+
+def test_bucket_starts_full():
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+
+    results = [bucket.try_acquire() for _ in range(4)]
+
+    assert results == [True, True, True, False]
+
+
+def test_try_acquire_consumes_the_requested_number_of_tokens():
+    bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
+
+    assert bucket.try_acquire(3)
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire(1)
+
+
+def test_failed_acquire_consumes_nothing():
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+    bucket.try_acquire(2)
+
+    assert not bucket.try_acquire(2)
+    assert bucket.try_acquire(1)
+
+
+def test_tokens_refill_with_elapsed_time():
+    clock = FakeClock()
+    bucket = drained_bucket(clock, capacity=2, refill_rate=2)
+
+    clock.advance(1)
+
+    assert bucket.try_acquire(2)
+
+
+def test_tokens_refill_continuously_in_fractions():
+    clock = FakeClock()
+    bucket = drained_bucket(clock, capacity=2, refill_rate=2)
+
+    clock.advance(0.25)
+    assert not bucket.try_acquire()
+    clock.advance(0.25)
+    assert bucket.try_acquire()
+
+
+def test_refill_stops_at_capacity():
+    clock = FakeClock()
+    bucket = drained_bucket(clock, capacity=2, refill_rate=2)
+
+    clock.advance(60)
+
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+def test_default_clock_is_usable():
+    bucket = TokenBucket(capacity=1, refill_rate=1)
+
+    assert bucket.try_acquire()
+
+
+@pytest.mark.parametrize("capacity", [0, -1, 2.5, "3"])
+def test_invalid_capacity_is_rejected(capacity):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity, refill_rate=1, clock=FakeClock())
+
+
+@pytest.mark.parametrize("refill_rate", [0, -0.5])
+def test_non_positive_refill_rate_is_rejected(refill_rate):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity=1, refill_rate=refill_rate, clock=FakeClock())
+
+
+@pytest.mark.parametrize("tokens", [0, -1, 4])
+def test_tokens_outside_one_to_capacity_are_rejected(tokens):
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+
+    with pytest.raises(ValueError):
+        bucket.try_acquire(tokens)
+
+
+def test_client_send_forwards_request_and_returns_result():
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(capacity=1, refill_rate=1, clock=FakeClock()))
+
+    result = limited.send("ping")
+
+    assert result == "response to ping"
+    assert client.sent_requests == ["ping"]
+
+
+def test_client_send_without_token_raises_and_does_not_call_client():
+    client = RecordingClient()
+    limited = RateLimitedClient(client, drained_bucket(FakeClock()))
+
+    with pytest.raises(RateLimitExceeded):
+        limited.send("ping")
+
+    assert client.sent_requests == []
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,98 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+from __future__ import annotations
+
+import math
+import threading
+import time
+from numbers import Integral, Real
+from typing import Any, Callable, Protocol
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
+    added continuously at ``refill_rate`` tokens per second of elapsed
+    ``clock`` time, never exceeding ``capacity``. If the clock moves
+    backwards, no tokens are added until it passes its latest reading again.
+    """
+
+    # Clock readings are floats, so a refill can land a hair below a whole
+    # token (ten steps of 0.1 s add up to 0.9999999999999999 s). Count such
+    # near-misses as available instead of rejecting them.
+    _TOLERANCE = 1e-9
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not _is_int(capacity) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
+        if not _is_positive_finite(refill_rate):
+            raise ValueError(f"refill_rate must be a finite number greater than 0, got {refill_rate!r}")
+        if not callable(clock):
+            raise ValueError(f"clock must be a zero-argument callable, got {clock!r}")
+
+        self._capacity = int(capacity)
+        self._refill_rate = float(refill_rate)
+        self._clock = clock
+        self._tokens = float(self._capacity)
+        self._last_refill = clock()
+        self._lock = threading.Lock()
+
+    def try_acquire(self, tokens: int = 1) -> bool:
+        """Consume ``tokens`` and return True, or return False and consume nothing."""
+        if not _is_int(tokens) or not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be an integer between 1 and {self._capacity}, got {tokens!r}"
+            )
+        with self._lock:
+            self._refill()
+            if self._tokens + self._TOLERANCE < tokens:
+                return False
+            self._tokens = max(0.0, self._tokens - tokens)
+            return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        elapsed = now - self._last_refill
+        if elapsed > 0:
+            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
+            self._last_refill = now
+
+
+class SupportsSend(Protocol):
+    def send(self, request: Any) -> Any: ...
+
+
+class RateLimitedClient:
+    """Forwards ``send`` calls to a client while the bucket has tokens."""
+
+    def __init__(self, client: SupportsSend, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request: Any) -> Any:
+        """Send ``request`` through the client, or raise RateLimitExceeded without sending."""
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded; request was not sent")
+        return self._client.send(request)
+
+
+def _is_int(value: object) -> bool:
+    # bool is an Integral subclass, but True/False are not meaningful counts.
+    return isinstance(value, Integral) and not isinstance(value, bool)
+
+
+def _is_positive_finite(value: object) -> bool:
+    if isinstance(value, bool) or not isinstance(value, Real):
+        return False
+    # NaN fails both comparisons, so it is rejected here too.
+    return 0 < value < math.inf
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,213 @@
+import math
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
+    def __init__(self, response="ok"):
+        self.response = response
+        self.requests = []
+
+    def send(self, request):
+        self.requests.append(request)
+        return self.response
+
+
+def drain(bucket, capacity):
+    for _ in range(capacity):
+        assert bucket.try_acquire()
+
+
+# --- TokenBucket: construction --------------------------------------------
+
+@pytest.mark.parametrize("capacity", [0, -1, 1.5, 2.0, True, "3", None])
+def test_invalid_capacity_raises(capacity):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity, 1)
+
+
+@pytest.mark.parametrize("rate", [0, -0.5, math.nan, math.inf, True, "1", None])
+def test_invalid_refill_rate_raises(rate):
+    with pytest.raises(ValueError):
+        TokenBucket(1, rate)
+
+
+def test_non_callable_clock_raises():
+    with pytest.raises(ValueError):
+        TokenBucket(1, 1, clock=5)
+
+
+def test_fractional_refill_rate_is_accepted():
+    clock = FakeClock()
+    bucket = TokenBucket(1, 0.5, clock=clock)
+    assert bucket.try_acquire()
+    clock.advance(1.5)
+    assert not bucket.try_acquire()
+    clock.advance(0.5)
+    assert bucket.try_acquire()
+
+
+def test_default_clock_works():
+    bucket = TokenBucket(2, 1)
+    assert bucket.try_acquire()
+    assert bucket.try_acquire()
+    assert not bucket.try_acquire()
+
+
+# --- TokenBucket: try_acquire ---------------------------------------------
+
+def test_bucket_starts_full():
+    bucket = TokenBucket(3, 1, clock=FakeClock())
+    assert [bucket.try_acquire() for _ in range(4)] == [True, True, True, False]
+
+
+def test_failed_acquire_consumes_nothing():
+    bucket = TokenBucket(5, 1, clock=FakeClock())
+    assert bucket.try_acquire(3)
+    assert not bucket.try_acquire(3)
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+def test_acquire_whole_capacity():
+    bucket = TokenBucket(4, 1, clock=FakeClock())
+    assert bucket.try_acquire(4)
+    assert not bucket.try_acquire()
+
+
+@pytest.mark.parametrize("tokens", [0, -1, 4, 1.5, True, "1", None])
+def test_invalid_token_count_raises(tokens):
+    bucket = TokenBucket(3, 1, clock=FakeClock())
+    with pytest.raises(ValueError):
+        bucket.try_acquire(tokens)
+    # The rejected call must not have consumed anything.
+    assert bucket.try_acquire(3)
+
+
+def test_refills_continuously_with_elapsed_time():
+    clock = FakeClock()
+    bucket = TokenBucket(2, 2, clock=clock)
+    drain(bucket, 2)
+    clock.advance(0.25)
+    assert not bucket.try_acquire()
+    clock.advance(0.25)
+    assert bucket.try_acquire()
+    assert not bucket.try_acquire()
+
+
+def test_partial_refill_is_kept_across_failed_attempts():
+    clock = FakeClock()
+    bucket = TokenBucket(1, 1, clock=clock)
+    drain(bucket, 1)
+    for _ in range(3):
+        clock.advance(0.25)
+        assert not bucket.try_acquire()
+    clock.advance(0.25)
+    assert bucket.try_acquire()
+
+
+def test_refill_is_capped_at_capacity():
+    clock = FakeClock()
+    bucket = TokenBucket(3, 10, clock=clock)
+    drain(bucket, 3)
+    clock.advance(1000)
+    drain(bucket, 3)
+    assert not bucket.try_acquire()
+
+
+def test_float_rounding_does_not_cause_spurious_rejection():
+    clock = FakeClock()
+    bucket = TokenBucket(1, 1, clock=clock)
+    drain(bucket, 1)
+    for _ in range(10):
+        clock.advance(0.1)  # sums to 0.9999999999999999
+    assert bucket.try_acquire()
+
+
+def test_clock_going_backwards_adds_no_tokens():
+    clock = FakeClock(100.0)
+    bucket = TokenBucket(1, 1, clock=clock)
+    drain(bucket, 1)
+    clock.now = 50.0
+    assert not bucket.try_acquire()
+    clock.now = 100.5
+    assert not bucket.try_acquire()
+    clock.now = 101.0
+    assert bucket.try_acquire()
+
+
+def test_concurrent_acquires_never_exceed_capacity():
+    bucket = TokenBucket(50, 1, clock=FakeClock())
+    results = []
+    lock = threading.Lock()
+    start = threading.Barrier(20)
+
+    def worker():
+        start.wait()
+        for _ in range(10):
+            ok = bucket.try_acquire()
+            with lock:
+                results.append(ok)
+
+    threads = [threading.Thread(target=worker) for _ in range(20)]
+    for t in threads:
+        t.start()
+    for t in threads:
+        t.join()
+    assert results.count(True) == 50
+
+
+# --- RateLimitedClient ----------------------------------------------------
+
+def test_client_forwards_request_and_returns_result():
+    client = RecordingClient(response={"status": 200})
+    limited = RateLimitedClient(client, TokenBucket(2, 1, clock=FakeClock()))
+    assert limited.send("req-1") == {"status": 200}
+    assert client.requests == ["req-1"]
+
+
+def test_client_raises_without_sending_when_limited():
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(1, 1, clock=FakeClock()))
+    limited.send("first")
+    with pytest.raises(RateLimitExceeded):
+        limited.send("second")
+    assert client.requests == ["first"]
+
+
+def test_client_sends_again_after_refill():
+    clock = FakeClock()
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(1, 1, clock=clock))
+    limited.send("a")
+    with pytest.raises(RateLimitExceeded):
+        limited.send("b")
+    clock.advance(1)
+    limited.send("c")
+    assert client.requests == ["a", "c"]
+
+
+def test_client_errors_propagate_and_still_use_a_token():
+    class FailingClient:
+        def send(self, request):
+            raise ConnectionError("boom")
+
+    limited = RateLimitedClient(FailingClient(), TokenBucket(1, 1, clock=FakeClock()))
+    with pytest.raises(ConnectionError):
+        limited.send("x")
+    with pytest.raises(RateLimitExceeded):
+        limited.send("y")
```

### Implementation 2

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,66 @@
+"""Token-bucket rate limiting, and a client wrapper that enforces it."""
+
+import time
+from collections.abc import Callable
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+class TokenBucket:
+    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` per second.
+
+    `clock` must return the current time in seconds. The bucket starts full.
+    Raises ValueError if `capacity` is not an integer > 0 or `refill_rate` is not > 0.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not isinstance(capacity, int) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
+        if refill_rate <= 0:
+            raise ValueError(f"refill_rate must be greater than 0, got {refill_rate!r}")
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._tokens: float = capacity
+        self._last_refill_time = clock()
+
+    def try_acquire(self, tokens: int = 1) -> bool:
+        """Consume `tokens` and return True if enough are available.
+
+        Otherwise consume nothing and return False.
+        Raises ValueError unless 1 <= `tokens` <= capacity.
+        """
+        if not 1 <= tokens <= self._capacity:
+            raise ValueError(f"tokens must be between 1 and {self._capacity}, got {tokens!r}")
+        self._refill()
+        if self._tokens < tokens:
+            return False
+        self._tokens -= tokens
+        return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        elapsed = now - self._last_refill_time
+        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
+        self._last_refill_time = now
+
+
+class RateLimitedClient:
+    """Forwards `send` to the wrapped client only while `bucket` has a token."""
+
+    def __init__(self, client, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        """Return `client.send(request)`, or raise RateLimitExceeded without calling the client."""
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("no token available; request was not sent")
+        return self._client.send(request)
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,123 @@
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    def __init__(self) -> None:
+        self.now = 0.0
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
+        self.sent_requests = []
+
+    def send(self, request):
+        self.sent_requests.append(request)
+        return f"response to {request}"
+
+
+@pytest.fixture
+def clock() -> FakeClock:
+    return FakeClock()
+
+
+def drained_bucket(capacity: int, refill_rate: float, clock: FakeClock) -> TokenBucket:
+    bucket = TokenBucket(capacity, refill_rate, clock)
+    assert bucket.try_acquire(capacity)
+    return bucket
+
+
+def test_bucket_starts_full(clock):
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+
+    results = [bucket.try_acquire() for _ in range(4)]
+
+    assert results == [True, True, True, False]
+
+
+def test_can_acquire_whole_capacity_at_once(clock):
+    bucket = TokenBucket(capacity=5, refill_rate=1, clock=clock)
+
+    assert bucket.try_acquire(5)
+
+
+def test_failed_acquire_consumes_nothing(clock):
+    bucket = TokenBucket(capacity=2, refill_rate=1, clock=clock)
+    bucket.try_acquire()
+
+    assert not bucket.try_acquire(2)
+    assert bucket.try_acquire(1)
+
+
+def test_tokens_refill_with_elapsed_time(clock):
+    bucket = drained_bucket(capacity=2, refill_rate=2, clock=clock)
+
+    clock.advance(0.5)
+
+    assert bucket.try_acquire()
+    assert not bucket.try_acquire()
+
+
+def test_partial_refill_accumulates_across_attempts(clock):
+    bucket = drained_bucket(capacity=1, refill_rate=1, clock=clock)
+
+    clock.advance(0.5)
+    assert not bucket.try_acquire()
+    clock.advance(0.5)
+    assert bucket.try_acquire()
+
+
+def test_refill_stops_at_capacity(clock):
+    bucket = drained_bucket(capacity=2, refill_rate=1, clock=clock)
+
+    clock.advance(100)
+
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+@pytest.mark.parametrize("capacity", [0, -1, 2.5])
+def test_rejects_invalid_capacity(capacity, clock):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity=capacity, refill_rate=1, clock=clock)
+
+
+@pytest.mark.parametrize("refill_rate", [0, -0.5])
+def test_rejects_non_positive_refill_rate(refill_rate, clock):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity=1, refill_rate=refill_rate, clock=clock)
+
+
+@pytest.mark.parametrize("tokens", [0, 4])
+def test_rejects_token_count_outside_one_to_capacity(tokens, clock):
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=clock)
+
+    with pytest.raises(ValueError):
+        bucket.try_acquire(tokens)
+
+
+def test_client_forwards_request_and_returns_response(clock):
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(capacity=1, refill_rate=1, clock=clock))
+
+    response = limited.send("ping")
+
+    assert response == "response to ping"
+    assert client.sent_requests == ["ping"]
+
+
+def test_client_raises_without_sending_when_no_token(clock):
+    client = RecordingClient()
+    limited = RateLimitedClient(client, drained_bucket(capacity=1, refill_rate=1, clock=clock))
+
+    with pytest.raises(RateLimitExceeded):
+        limited.send("ping")
+
+    assert client.sent_requests == []
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,105 @@
+"""Token-bucket rate limiting and a client wrapper that enforces it."""
+
+import math
+import numbers
+import threading
+import time
+
+# Refill arithmetic is done in floats, so a bucket that should hold exactly
+# one token can hold 0.9999999999999998. This tolerance absorbs that drift so
+# a token that is due is not rejected.
+_TOLERANCE = 1e-9
+
+
+class RateLimitExceeded(Exception):
+    """Raised by RateLimitedClient.send when the bucket has no token left."""
+
+
+class TokenBucket:
+    """A thread-safe token bucket.
+
+    The bucket holds at most ``capacity`` tokens and starts full. Tokens are
+    added continuously at ``refill_rate`` per second of elapsed ``clock`` time.
+    """
+
+    def __init__(self, capacity, refill_rate, clock=time.monotonic):
+        if not _is_integer(capacity) or capacity <= 0:
+            raise ValueError(
+                f"capacity must be an integer greater than 0, got {capacity!r}"
+            )
+        if not callable(clock):
+            raise ValueError(f"clock must be a callable, got {clock!r}")
+
+        self._capacity = int(capacity)
+        self._refill_rate = _positive_finite_rate(refill_rate)
+        self._clock = clock
+        self._tokens = float(self._capacity)
+        self._last_refill = clock()
+        self._lock = threading.Lock()
+
+    def try_acquire(self, tokens=1):
+        """Consume ``tokens`` and return True, or return False and consume nothing."""
+        if not _is_integer(tokens) or not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be an integer from 1 to {self._capacity}, got {tokens!r}"
+            )
+        with self._lock:
+            self._refill()
+            if self._tokens + _TOLERANCE < tokens:
+                return False
+            self._tokens = max(0.0, self._tokens - tokens)
+            return True
+
+    def _refill(self):
+        now = self._clock()
+        elapsed = now - self._last_refill
+        if elapsed <= 0:
+            # A clock that stalls or steps backwards must never remove tokens,
+            # and keeping the later timestamp avoids crediting time twice.
+            return
+        self._tokens = min(
+            float(self._capacity), self._tokens + elapsed * self._refill_rate
+        )
+        self._last_refill = now
+
+
+class RateLimitedClient:
+    """Forwards ``send`` to a wrapped client, spending one bucket token per call.
+
+    A token is spent as soon as the call is let through, so a call that the
+    wrapped client then fails still counts against the limit.
+    """
+
+    def __init__(self, client, bucket):
+        if not callable(getattr(client, "send", None)):
+            raise TypeError("client must have a callable send(request) method")
+        if not callable(getattr(bucket, "try_acquire", None)):
+            raise TypeError("bucket must have a callable try_acquire() method")
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        """Return ``client.send(request)``, or raise RateLimitExceeded if no token is free."""
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: no token available")
+        return self._client.send(request)
+
+
+def _is_integer(value):
+    # bool is a subclass of int, but True is not a meaningful token count.
+    return isinstance(value, numbers.Integral) and not isinstance(value, bool)
+
+
+def _positive_finite_rate(value):
+    if isinstance(value, bool) or not isinstance(value, numbers.Real):
+        raise ValueError(f"refill_rate must be a number, got {value!r}")
+    try:
+        rate = float(value)
+    except OverflowError:
+        rate = math.inf
+    # NaN fails "rate > 0", and infinity would turn a zero elapsed time into NaN.
+    if not (rate > 0 and math.isfinite(rate)):
+        raise ValueError(
+            f"refill_rate must be a finite number greater than 0, got {value!r}"
+        )
+    return rate
```

### Implementation 2

```diff
diff -ruN before/ratelimit/limiter.py after/ratelimit/limiter.py
--- before/ratelimit/limiter.py
+++ after/ratelimit/limiter.py
@@ -0,0 +1,65 @@
+"""Token-bucket rate limiting, and a client wrapper that enforces it."""
+
+import time
+from typing import Callable
+
+
+class RateLimitExceeded(Exception):
+    """Raised when a request is rejected because no token is available."""
+
+
+class TokenBucket:
+    """Holds up to `capacity` tokens, refilled continuously at `refill_rate` per second.
+
+    The bucket starts full. `clock` returns the current time in seconds.
+    """
+
+    def __init__(
+        self,
+        capacity: int,
+        refill_rate: float,
+        clock: Callable[[], float] = time.monotonic,
+    ) -> None:
+        if not isinstance(capacity, int) or capacity <= 0:
+            raise ValueError(f"capacity must be an integer greater than 0, got {capacity!r}")
+        if refill_rate <= 0:
+            raise ValueError(f"refill_rate must be greater than 0, got {refill_rate!r}")
+        self._capacity = capacity
+        self._refill_rate = refill_rate
+        self._clock = clock
+        self._tokens = float(capacity)
+        self._last_refill_time = clock()
+
+    def try_acquire(self, tokens: int = 1) -> bool:
+        """Consume `tokens` and return True if enough are available.
+
+        Otherwise consume nothing and return False.
+        """
+        if not 1 <= tokens <= self._capacity:
+            raise ValueError(
+                f"tokens must be between 1 and capacity ({self._capacity}), got {tokens!r}"
+            )
+        self._refill()
+        if self._tokens < tokens:
+            return False
+        self._tokens -= tokens
+        return True
+
+    def _refill(self) -> None:
+        now = self._clock()
+        elapsed_seconds = now - self._last_refill_time
+        self._tokens = min(self._capacity, self._tokens + elapsed_seconds * self._refill_rate)
+        self._last_refill_time = now
+
+
+class RateLimitedClient:
+    """Forwards requests to `client.send` only while `bucket` has a token for them."""
+
+    def __init__(self, client, bucket: TokenBucket) -> None:
+        self._client = client
+        self._bucket = bucket
+
+    def send(self, request):
+        if not self._bucket.try_acquire():
+            raise RateLimitExceeded("rate limit exceeded: no token available, request not sent")
+        return self._client.send(request)
diff -ruN before/tests/test_limiter.py after/tests/test_limiter.py
--- before/tests/test_limiter.py
+++ after/tests/test_limiter.py
@@ -0,0 +1,116 @@
+import pytest
+
+from ratelimit.limiter import RateLimitedClient, RateLimitExceeded, TokenBucket
+
+
+class FakeClock:
+    def __init__(self):
+        self.now = 0.0
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
+        self.sent_requests = []
+
+    def send(self, request):
+        self.sent_requests.append(request)
+        return f"response to {request}"
+
+
+def drained_bucket(capacity, refill_rate, clock):
+    bucket = TokenBucket(capacity, refill_rate, clock)
+    assert bucket.try_acquire(capacity)
+    return bucket
+
+
+def test_bucket_starts_full():
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+
+    results = [bucket.try_acquire() for _ in range(4)]
+
+    assert results == [True, True, True, False]
+
+
+def test_try_acquire_consumes_the_requested_number_of_tokens():
+    bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
+
+    assert bucket.try_acquire(3)
+    assert not bucket.try_acquire(3)
+    assert bucket.try_acquire(2)
+
+
+def test_failed_acquire_consumes_nothing():
+    bucket = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
+    bucket.try_acquire(4)
+
+    assert not bucket.try_acquire(2)
+
+    assert bucket.try_acquire(1)
+
+
+def test_tokens_refill_continuously_with_elapsed_time():
+    clock = FakeClock()
+    bucket = drained_bucket(capacity=2, refill_rate=2, clock=clock)
+
+    clock.advance(0.25)
+    assert not bucket.try_acquire()
+
+    clock.advance(0.25)
+    assert bucket.try_acquire()
+
+
+def test_refill_stops_at_capacity():
+    clock = FakeClock()
+    bucket = drained_bucket(capacity=2, refill_rate=10, clock=clock)
+
+    clock.advance(100)
+
+    assert bucket.try_acquire(2)
+    assert not bucket.try_acquire()
+
+
+@pytest.mark.parametrize("capacity", [0, -1, 1.5, "3"])
+def test_invalid_capacity_is_rejected(capacity):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity, refill_rate=1, clock=FakeClock())
+
+
+@pytest.mark.parametrize("refill_rate", [0, -0.5])
+def test_non_positive_refill_rate_is_rejected(refill_rate):
+    with pytest.raises(ValueError):
+        TokenBucket(capacity=1, refill_rate=refill_rate, clock=FakeClock())
+
+
+@pytest.mark.parametrize("tokens", [0, 4])
+def test_try_acquire_rejects_tokens_outside_one_to_capacity(tokens):
+    bucket = TokenBucket(capacity=3, refill_rate=1, clock=FakeClock())
+
+    with pytest.raises(ValueError):
+        bucket.try_acquire(tokens)
+
+
+def test_client_forwards_request_and_returns_its_result_when_token_available():
+    client = RecordingClient()
+    limited = RateLimitedClient(client, TokenBucket(capacity=1, refill_rate=1, clock=FakeClock()))
+
+    response = limited.send("ping")
+
+    assert response == "response to ping"
+    assert client.sent_requests == ["ping"]
+
+
+def test_client_raises_without_sending_when_no_token_available():
+    client = RecordingClient()
+    empty_bucket = drained_bucket(capacity=1, refill_rate=1, clock=FakeClock())
+    limited = RateLimitedClient(client, empty_bucket)
+
+    with pytest.raises(RateLimitExceeded):
+        limited.send("ping")
+
+    assert client.sent_requests == []
```

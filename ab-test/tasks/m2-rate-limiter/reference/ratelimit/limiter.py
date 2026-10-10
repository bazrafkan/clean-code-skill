import time


class RateLimitExceeded(Exception):
    pass


class TokenBucket:
    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        if not isinstance(capacity, int) or capacity <= 0 or refill_rate <= 0:
            raise ValueError("invalid bucket")
        self._capacity = capacity
        self._rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def try_acquire(self, tokens=1):
        if tokens < 1 or tokens > self._capacity:
            raise ValueError("invalid token count")
        now = self._clock()
        self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._rate)
        self._last = now
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False


class RateLimitedClient:
    def __init__(self, client, bucket):
        self._client = client
        self._bucket = bucket

    def send(self, request):
        if not self._bucket.try_acquire():
            raise RateLimitExceeded()
        return self._client.send(request)

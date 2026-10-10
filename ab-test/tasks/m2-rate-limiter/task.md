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

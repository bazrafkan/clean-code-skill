import sys

from notify import DeliveryError


class FakeSender:
    """Records every send, and fails the first `failures` of them with DeliveryError."""

    def __init__(self, failures: int = 0) -> None:
        self._failures_left = failures
        self.calls: list[tuple[str, str]] = []

    @classmethod
    def broken(cls) -> "FakeSender":
        """A sender whose every send fails."""
        return cls(failures=sys.maxsize)

    def send(self, address: str, message: str) -> None:
        self.calls.append((address, message))
        if self._failures_left > 0:
            self._failures_left -= 1
            raise DeliveryError("simulated outage")


class CrashingSender:
    """A sender with a bug: it raises an error that is not a DeliveryError."""

    def __init__(self) -> None:
        self.calls = 0

    def send(self, address: str, message: str) -> None:
        self.calls += 1
        raise RuntimeError("sender bug")

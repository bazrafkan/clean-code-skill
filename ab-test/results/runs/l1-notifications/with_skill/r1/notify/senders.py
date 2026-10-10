"""The contract that channel senders (email, SMS, push...) implement."""

from typing import Protocol


class DeliveryError(Exception):
    """A sender could not deliver a message; the service retries or falls back."""


class Sender(Protocol):
    def send(self, address: str, message: str) -> None:
        """Deliver ``message`` to ``address``, raising DeliveryError on failure."""

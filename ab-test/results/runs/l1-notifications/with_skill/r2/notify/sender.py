from typing import Protocol


class DeliveryError(Exception):
    """Raised by a sender when a message could not be delivered.

    The notification service treats it as a failed attempt and retries or falls back.
    """


class Sender(Protocol):
    """Delivers messages on one channel, such as email, SMS or push."""

    def send(self, address: str, message: str) -> None:
        """Deliver `message` to `address`, raising DeliveryError if delivery fails."""
        ...

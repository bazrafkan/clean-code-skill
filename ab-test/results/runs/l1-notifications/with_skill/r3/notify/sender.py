from typing import Protocol


class DeliveryError(Exception):
    """Raised by a sender when it could not deliver a message."""


class Sender(Protocol):
    """Delivers messages on one channel, such as email, SMS or push."""

    def send(self, address: str, message: str) -> None:
        """Deliver `message` to `address`, or raise DeliveryError."""

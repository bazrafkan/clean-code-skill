"""The contract between the notification service and channel senders."""

from typing import Protocol


class DeliveryError(Exception):
    """Raised by a sender when it could not deliver a message."""


class Sender(Protocol):
    """Delivers a message to an address on one channel (email, SMS, push...)."""

    def send(self, address: str, message: str) -> None:
        """Deliver ``message`` to ``address``; raise DeliveryError on failure."""
        ...

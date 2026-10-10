"""Types shared between the service and the senders it drives."""

from dataclasses import dataclass, field
from typing import Protocol


class DeliveryError(Exception):
    """Raised by a sender when it could not deliver a message."""


class Sender(Protocol):
    """Anything that can deliver a message to an address on one channel."""

    def send(self, address: str, message: str) -> None:
        """Deliver ``message`` to ``address``; raise DeliveryError on failure."""


@dataclass
class DeliveryReport:
    """Outcome of one ``NotificationService.notify`` call.

    ``attempts`` lists every send attempt as ``(channel, succeeded)``,
    in the order the attempts happened.
    """

    delivered: bool
    channel: str | None = None
    attempts: list[tuple[str, bool]] = field(default_factory=list)

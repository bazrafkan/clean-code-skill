from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol

from .templates import TemplateStore
from .user import User


class DeliveryError(Exception):
    """Raised by a sender when it could not deliver a message."""


class Sender(Protocol):
    def send(self, address: str, message: str) -> None:
        """Delivers the message to the address, or raises DeliveryError."""


@dataclass(frozen=True)
class DeliveryReport:
    delivered: bool
    channel: str | None
    attempts: list[tuple[str, bool]]


class NotificationService:
    """Sends a templated message through a user's preferred channels.

    Each channel is retried up to max_retries times before falling back to the next one.
    """

    def __init__(
        self, senders: Mapping[str, Sender], templates: TemplateStore, max_retries: int = 2
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must not be negative, got {max_retries}")
        self._senders = senders
        self._templates = templates
        self._max_attempts_per_channel = max_retries + 1

    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
        message = self._templates.render(template_name, **params)
        attempts: list[tuple[str, bool]] = []
        for channel, sender, address in self._reachable_channels(user):
            for _ in range(self._max_attempts_per_channel):
                succeeded = _try_send(sender, address, message)
                attempts.append((channel, succeeded))
                if succeeded:
                    return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _reachable_channels(self, user: User) -> Iterator[tuple[str, Sender, str]]:
        """Yields, in preference order, the channels that have both a sender and an address."""
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is not None and address is not None:
                yield channel, sender, address


def _try_send(sender: Sender, address: str, message: str) -> bool:
    try:
        sender.send(address, message)
    except DeliveryError:
        return False
    return True

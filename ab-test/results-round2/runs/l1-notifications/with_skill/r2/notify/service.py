from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol

from .templates import TemplateStore
from .user import User


class DeliveryError(Exception):
    """Raised by a sender when it could not deliver a message."""


class Sender(Protocol):
    def send(self, address: str, message: str) -> None:
        """Delivers `message` to `address`, raising DeliveryError on failure."""


@dataclass(frozen=True)
class DeliveryReport:
    """Outcome of one notification.

    `attempts` holds a `(channel, succeeded)` tuple for every send, in the order they happened.
    """

    delivered: bool
    channel: str | None
    attempts: list[tuple[str, bool]]


class NotificationService:
    """Sends a templated message through a user's preferred channels, retrying each before falling back to the next."""

    def __init__(self, senders: Mapping[str, Sender], templates: TemplateStore, max_retries: int = 2) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must not be negative, got {max_retries}")
        self._senders = senders
        self._templates = templates
        self._attempts_per_channel = 1 + max_retries

    # `user` and `template_name` are positional-only so that templates can use placeholders with those names.
    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
        """Template errors are raised before anything is sent. Sender errors other than DeliveryError propagate."""
        message = self._templates.render(template_name, **params)
        attempts: list[tuple[str, bool]] = []
        for channel, sender, address in self._usable_channels(user):
            for _ in range(self._attempts_per_channel):
                succeeded = _try_send(sender, address, message)
                attempts.append((channel, succeeded))
                if succeeded:
                    return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _usable_channels(self, user: User) -> Iterator[tuple[str, Sender, str]]:
        """Yields `(channel, sender, address)` for each preferred channel that has both a sender and an address."""
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

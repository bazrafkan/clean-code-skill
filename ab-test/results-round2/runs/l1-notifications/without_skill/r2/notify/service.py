"""Delivery of templated messages over a user's preferred channels."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from notify.errors import DeliveryError
from notify.templates import TemplateStore
from notify.user import User


class Sender(Protocol):
    """Delivers a message to an address on one channel.

    Raises DeliveryError when delivery fails.
    """

    def send(self, address: str, message: str) -> None: ...


@dataclass(frozen=True)
class DeliveryReport:
    """The outcome of one `NotificationService.notify` call."""

    delivered: bool
    channel: str | None
    attempts: list[tuple[str, bool]]


class NotificationService:
    """Sends a rendered template through a user's channels, with retries and fallback."""

    def __init__(
        self,
        senders: Mapping[str, Sender],
        templates: TemplateStore,
        max_retries: int = 2,
    ) -> None:
        """
        Args:
            senders: channel name -> sender for that channel.
            templates: where message templates are looked up.
            max_retries: extra attempts on a channel after its first failure.
        """
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        self._senders = dict(senders)
        self._templates = templates
        self._max_retries = max_retries

    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
        """Render `template_name` with `params` and deliver it to `user`.

        Channels are tried in the user's order of preference. A channel with
        no sender, no address for this user or an unknown name is skipped
        without an attempt. Each channel gets up to `max_retries` extra
        attempts after a DeliveryError before the next channel is tried.
        Delivery stops at the first success.

        `user` and `template_name` are positional-only so templates may use
        `{user}` or `{template_name}` placeholders.

        Raises:
            KeyError, ValueError: the template is unknown or a parameter is
                missing; nothing is sent.
            Any exception other than DeliveryError raised by a sender.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[tuple[str, bool]] = []
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is None or address is None:
                continue
            if self._send_with_retries(channel, sender, address, message, attempts):
                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _send_with_retries(
        self,
        channel: str,
        sender: Sender,
        address: str,
        message: str,
        attempts: list[tuple[str, bool]],
    ) -> bool:
        """Try one channel up to 1 + max_retries times, recording each attempt."""
        for _ in range(1 + self._max_retries):
            try:
                sender.send(address, message)
            except DeliveryError:
                attempts.append((channel, False))
            else:
                attempts.append((channel, True))
                return True
        return False

"""Delivering a rendered message over a user's preferred channels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol

from notify.errors import DeliveryError
from notify.templates import TemplateStore
from notify.user import User


class Sender(Protocol):
    """Delivers a message to an address on one channel.

    Implementations raise ``DeliveryError`` when delivery fails.
    """

    def send(self, address: str, message: str) -> None: ...


@dataclass
class DeliveryReport:
    """The outcome of one ``NotificationService.notify`` call.

    ``attempts`` lists every send attempt as ``(channel, succeeded)``, in the
    order the attempts happened.
    """

    delivered: bool
    channel: Optional[str] = None
    attempts: list[tuple[str, bool]] = field(default_factory=list)


class NotificationService:
    """Sends templated messages to users, with retries and channel fallback."""

    def __init__(
        self,
        senders: Mapping[str, Sender],
        templates: TemplateStore,
        max_retries: int = 2,
    ) -> None:
        """
        Args:
            senders: channel name -> sender for that channel.
            templates: where messages are rendered from.
            max_retries: extra attempts on a channel after its first failure.

        Raises:
            ValueError: ``max_retries`` is negative.
        """
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        self._senders = dict(senders)
        self._templates = templates
        self._max_retries = max_retries

    def notify(
        self, user: User, template_name: str, /, **params: Any
    ) -> DeliveryReport:
        """Render ``template_name`` and deliver it to ``user``.

        ``user`` and ``template_name`` are positional-only so that templates
        can use placeholders with those names.

        Channels are tried in the user's order of preference. A channel is
        skipped, with no attempt recorded, when it has no sender, the user has
        no address for it, or its name is unknown. A channel that keeps
        raising ``DeliveryError`` is tried ``1 + max_retries`` times before
        falling back to the next one. Delivery stops at the first success.

        Raises:
            KeyError, ValueError: the template is unknown or a parameter is
                missing; raised before anything is sent.
            Exception: anything other than ``DeliveryError`` raised by a sender.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[tuple[str, bool]] = []
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is None or address is None:
                continue
            outcomes = self._send_with_retries(sender, address, message)
            attempts.extend((channel, succeeded) for succeeded in outcomes)
            if outcomes[-1]:
                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _send_with_retries(
        self, sender: Sender, address: str, message: str
    ) -> list[bool]:
        """Send until it succeeds or the retries run out.

        Returns the outcome of each attempt, in order. The list is never
        empty, and only its last entry can be ``True``.
        """
        outcomes: list[bool] = []
        for _ in range(1 + self._max_retries):
            try:
                sender.send(address, message)
            except DeliveryError:
                outcomes.append(False)
            else:
                outcomes.append(True)
                break
        return outcomes

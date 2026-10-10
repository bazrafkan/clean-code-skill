"""Delivery of rendered messages through a user's preferred channels."""

from collections.abc import Mapping
from typing import Protocol

from .errors import DeliveryError
from .report import Attempt, DeliveryReport
from .templates import TemplateStore
from .user import User


class Sender(Protocol):
    """Anything that can deliver a message to an address on one channel."""

    def send(self, address: str, message: str) -> None:
        """Deliver ``message``, or raise ``DeliveryError`` on failure."""


class NotificationService:
    """Sends templated messages with per-channel retries and fallback."""

    def __init__(
        self,
        senders: Mapping[str, Sender],
        templates: TemplateStore,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        self._senders = dict(senders)
        self._templates = templates
        self._max_retries = max_retries

    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
        """Render ``template_name`` and deliver it to ``user``.

        Channels are tried in the user's preference order. A channel is
        skipped, without an attempt, when it has no sender or the user has
        no address for it. A ``DeliveryError`` triggers up to
        ``max_retries`` extra attempts on the same channel before falling
        back to the next one. Delivery stops at the first success.

        ``user`` and ``template_name`` are positional-only so that template
        parameters may use those names.

        Raises:
            KeyError, ValueError: the template is unknown or a parameter is
                missing; nothing is sent.
            Exception: anything a sender raises other than ``DeliveryError``.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[Attempt] = []
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
        attempts: list[Attempt],
    ) -> bool:
        """Try one channel up to ``1 + max_retries`` times, recording each try."""
        for _ in range(1 + self._max_retries):
            try:
                sender.send(address, message)
            except DeliveryError:
                attempts.append((channel, False))
                continue
            attempts.append((channel, True))
            return True
        return False

"""Delivery of templated messages over a user's preferred channels."""

import logging
from collections.abc import Mapping

from notify.report import Attempt, DeliveryReport
from notify.senders import DeliveryError, Sender
from notify.templates import TemplateStore
from notify.user import User

_logger = logging.getLogger(__name__)


class NotificationService:
    """Sends a message through a user's preferred channels, with retries and fallback.

    Each channel is tried up to ``1 + max_retries`` times; when every attempt
    fails, the next preferred channel is tried. Delivery stops at the first
    successful send.
    """

    def __init__(
        self,
        senders: Mapping[str, Sender],
        templates: TemplateStore,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must not be negative, got {max_retries}")
        self._senders = dict(senders)
        self._templates = templates
        self._max_retries = max_retries

    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
        """Render ``template_name`` with ``params`` and deliver it to ``user``.

        ``user`` and ``template_name`` are positional-only so that templates
        may use ``{user}`` or ``{template_name}`` placeholders.

        Template errors propagate before anything is sent. A channel is skipped,
        with no attempt recorded, when it has no sender, the user has no address
        for it, or its name is unknown. Only DeliveryError triggers a retry or a
        fallback; any other exception from a sender propagates.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[Attempt] = []
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is None or address is None:
                continue
            channel_attempts = self._send_with_retries(channel, sender, address, message)
            attempts.extend(channel_attempts)
            if channel_attempts[-1].succeeded:
                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _send_with_retries(
        self, channel: str, sender: Sender, address: str, message: str
    ) -> list[Attempt]:
        """Send on one channel until it succeeds or the retries run out."""
        attempts: list[Attempt] = []
        for _ in range(1 + self._max_retries):
            try:
                sender.send(address, message)
            except DeliveryError as error:
                _logger.warning("Delivery via %s failed: %s", channel, error)
                attempts.append(Attempt(channel, succeeded=False))
            else:
                attempts.append(Attempt(channel, succeeded=True))
                break
        return attempts

"""Delivers a rendered template to a user, with retries and channel fallback."""

from collections.abc import Mapping
from typing import Protocol

from .errors import DeliveryError
from .report import DeliveryReport
from .templates import TemplateStore
from .user import User


class Sender(Protocol):
    def send(self, address: str, message: str) -> None:
        """Deliver `message` to `address`, raising DeliveryError on failure."""


class NotificationService:
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

    def notify(
        self, user: User, template_name: str, /, **params: object
    ) -> DeliveryReport:
        """Send the rendered template on the user's first channel that works.

        `user` and `template_name` are positional-only so templates may use
        placeholders with those names. Template errors are raised before
        anything is sent. A channel is
        skipped, with no attempt recorded, when it has no sender, the user
        has no address for it, or its name is unknown. Each usable channel
        gets one attempt plus up to `max_retries` retries on DeliveryError
        before falling back to the next one. Any other exception from a
        sender propagates.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[tuple[str, bool]] = []
        tried: set[str] = set()

        for channel in user.preferred_channels:
            # A repeated channel would exceed its retry budget, so try it once.
            if channel in tried:
                continue
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is None or address is None:
                continue
            tried.add(channel)

            if self._send_with_retries(sender, channel, address, message, attempts):
                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)

        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _send_with_retries(
        self,
        sender: Sender,
        channel: str,
        address: str,
        message: str,
        attempts: list[tuple[str, bool]],
    ) -> bool:
        """Try one channel, recording each attempt. Return True on success."""
        for _ in range(1 + self._max_retries):
            try:
                sender.send(address, message)
            except DeliveryError:
                attempts.append((channel, False))
            else:
                attempts.append((channel, True))
                return True
        return False

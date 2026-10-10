from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from notify.report import Attempt, DeliveryReport
from notify.sender import DeliveryError, Sender
from notify.templates import TemplateStore
from notify.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends a templated message to a user on the first of their preferred channels
    that accepts it, retrying each channel before falling back to the next."""

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
        self._attempts_per_channel = max_retries + 1

    def notify(
        self, user: User, template_name: str, /, **params: object
    ) -> DeliveryReport:
        """Render the template and deliver it to `user`.

        `user` and `template_name` are positional-only, so templates may use any
        placeholder name. Template errors (KeyError, ValueError) are raised before
        anything is sent. A DeliveryError from a sender counts as a failed attempt;
        any other exception from a sender propagates.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[Attempt] = []
        for route in self._routes_to(user):
            route_attempts = self._send_with_retries(route, message)
            attempts.extend(route_attempts)
            if route_attempts[-1].succeeded:
                return DeliveryReport(
                    delivered=True, channel=route.channel, attempts=attempts
                )
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _routes_to(self, user: User) -> Iterator[_Route]:
        """Yield the preferred channels that have a sender and an address, in order."""
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is not None and address is not None:
                yield _Route(channel, sender, address)

    def _send_with_retries(self, route: _Route, message: str) -> list[Attempt]:
        """Send on `route` until it succeeds or the attempts per channel run out.

        Never returns an empty list, because there is at least one attempt per channel.
        """
        attempts: list[Attempt] = []
        for _ in range(self._attempts_per_channel):
            succeeded = route.try_send(message)
            attempts.append(Attempt(route.channel, succeeded))
            if succeeded:
                break
        return attempts


@dataclass(frozen=True)
class _Route:
    """One way to reach a user: a channel, its sender and the user's address there."""

    channel: str
    sender: Sender
    address: str

    def try_send(self, message: str) -> bool:
        """Send `message` and tell whether it was delivered."""
        try:
            self.sender.send(self.address, message)
        except DeliveryError as error:
            logger.warning("Delivery via %s failed: %s", self.channel, error)
            return False
        return True

"""Delivery of a templated message over a user's preferred channels."""

import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from notify.senders import DeliveryError, Sender
from notify.templates import TemplateStore
from notify.user import User

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 2

type Attempt = tuple[str, bool]
"""One send: ``(channel, succeeded)``."""


@dataclass(frozen=True)
class DeliveryReport:
    """Outcome of one notification; ``channel`` is None when nothing was delivered.

    ``attempts`` lists every send in the order it happened.
    """

    delivered: bool
    channel: str | None
    attempts: list[Attempt]


@dataclass(frozen=True)
class _Route:
    """A preferred channel that can be used now: it has a sender and an address."""

    channel: str
    address: str
    sender: Sender


class NotificationService:
    """Sends a message over a user's channels, retrying each, then falling back."""

    def __init__(
        self,
        senders: Mapping[str, Sender],
        templates: TemplateStore,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be 0 or more, got {max_retries}")
        self._senders = dict(senders)
        self._templates = templates
        self._attempts_per_channel = 1 + max_retries

    def notify(
        self, user: User, template_name: str, /, **params: object
    ) -> DeliveryReport:
        """Render ``template_name`` with ``params`` and deliver it to ``user``.

        Template errors are raised before anything is sent. A DeliveryError from
        a sender is retried, then the next channel is tried; any other exception
        from a sender propagates.
        """
        # user and template_name are positional-only so templates may use
        # {user} or {template_name} placeholders.
        message = self._templates.render(template_name, **params)
        attempts: list[Attempt] = []
        for route in self._routes_to(user):
            route_attempts = self._send_with_retries(route, message)
            attempts.extend(route_attempts)
            if any(succeeded for _, succeeded in route_attempts):
                return DeliveryReport(
                    delivered=True, channel=route.channel, attempts=attempts
                )
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _routes_to(self, user: User) -> Iterator[_Route]:
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is not None and address is not None:
                yield _Route(channel, address, sender)

    def _send_with_retries(self, route: _Route, message: str) -> list[Attempt]:
        attempts: list[Attempt] = []
        for _ in range(self._attempts_per_channel):
            succeeded = _send_once(route, message)
            attempts.append((route.channel, succeeded))
            if succeeded:
                break
        return attempts


def _send_once(route: _Route, message: str) -> bool:
    try:
        route.sender.send(route.address, message)
    except DeliveryError as error:
        logger.warning("Delivery via %s failed: %s", route.channel, error)
        return False
    return True

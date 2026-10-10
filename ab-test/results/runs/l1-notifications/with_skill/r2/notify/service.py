import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from .report import Attempt, DeliveryReport
from .sender import DeliveryError, Sender
from .templates import TemplateStore
from .user import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Route:
    """A usable channel for one user: its sender and the user's address on it."""

    channel: str
    sender: Sender
    address: str


class NotificationService:
    """Sends templated messages over a user's preferred channels.

    A failing channel is retried, then the next preferred channel is tried.
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
        self._attempts_per_channel = max_retries + 1

    def notify(
        self, user: User, template_name: str, /, **params: object
    ) -> DeliveryReport:
        """Render the template and deliver it on the first preferred channel that works.

        Each channel gets 1 + max_retries attempts before the next one is tried.
        Channels without a sender or without a user address are skipped unrecorded.
        Template errors are raised before anything is sent. Sender exceptions other
        than DeliveryError propagate.
        """
        message = self._templates.render(template_name, **params)
        attempts: list[Attempt] = []
        for route in self._routes_to(user):
            channel_attempts = self._send_with_retries(route, message)
            attempts.extend(channel_attempts)
            if channel_attempts[-1].succeeded:
                return DeliveryReport(
                    delivered=True, channel=route.channel, attempts=attempts
                )
        return DeliveryReport(delivered=False, channel=None, attempts=attempts)

    def _routes_to(self, user: User) -> Iterator[_Route]:
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is not None and address is not None:
                yield _Route(channel, sender, address)

    def _send_with_retries(self, route: _Route, message: str) -> list[Attempt]:
        """Send until the first success or until the channel's attempts run out."""
        attempts: list[Attempt] = []
        for _ in range(self._attempts_per_channel):
            succeeded = _try_send(route, message)
            attempts.append(Attempt(route.channel, succeeded))
            if succeeded:
                break
        return attempts


def _try_send(route: _Route, message: str) -> bool:
    try:
        route.sender.send(route.address, message)
    except DeliveryError as error:
        # Recorded as a failed attempt by the caller; logged so the cause isn't lost.
        logger.warning("Delivery via %s failed: %s", route.channel, error)
        return False
    return True

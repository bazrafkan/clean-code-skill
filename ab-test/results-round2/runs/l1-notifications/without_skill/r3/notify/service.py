"""Delivery of templated messages over a user's preferred channels."""

from collections.abc import Mapping

from notify.delivery import DeliveryError, DeliveryReport, Sender
from notify.templates import TemplateStore
from notify.user import User


class NotificationService:
    """Sends a rendered template to a user, retrying each channel and falling back.

    ``senders`` maps channel name to sender. Each usable channel gets one attempt
    plus up to ``max_retries`` retries before the next channel is tried.
    """

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
        """Render ``template_name`` and send it to ``user``; stop at the first success.

        ``user`` and ``template_name`` are positional-only, so templates may use
        placeholders with those names.

        A channel is skipped, with no attempt recorded, when it has no configured
        sender or the user has no address for it (this includes unknown names).
        Template errors propagate before anything is sent, and exceptions other
        than DeliveryError propagate from the sender.
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
        """Try one channel up to ``1 + max_retries`` times, appending each attempt.

        Returns True as soon as a send succeeds, False once every attempt failed.
        """
        for _ in range(1 + self._max_retries):
            try:
                sender.send(address, message)
            except DeliveryError:
                attempts.append((channel, False))
            else:
                attempts.append((channel, True))
                return True
        return False

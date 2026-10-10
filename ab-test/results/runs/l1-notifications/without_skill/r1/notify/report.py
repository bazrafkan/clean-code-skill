"""The outcome of a single notification request."""

from dataclasses import dataclass, field

Attempt = tuple[str, bool]


@dataclass(frozen=True)
class DeliveryReport:
    """What happened when a notification was sent.

    Attributes:
        delivered: whether any channel accepted the message.
        channel: the channel that succeeded, or ``None``.
        attempts: ``(channel, succeeded)`` for every send, in order.
    """

    delivered: bool
    channel: str | None = None
    attempts: list[Attempt] = field(default_factory=list)

"""The outcome of a single notify() call."""

from dataclasses import dataclass, field


@dataclass
class DeliveryReport:
    delivered: bool
    # The channel that delivered the message, or None if none did.
    channel: str | None
    # One (channel, succeeded) entry per send attempt, in the order made.
    attempts: list[tuple[str, bool]] = field(default_factory=list)

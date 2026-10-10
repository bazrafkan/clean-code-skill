from dataclasses import dataclass
from typing import NamedTuple


class Attempt(NamedTuple):
    """One send on one channel. It is a plain `(channel, succeeded)` tuple."""

    channel: str
    succeeded: bool


@dataclass(frozen=True)
class DeliveryReport:
    """Whether a notification was delivered, on which channel, and each attempt made."""

    delivered: bool
    channel: str | None
    attempts: list[Attempt]

    def __post_init__(self) -> None:
        names_channel = self.channel is not None
        if self.delivered != names_channel:
            raise ValueError(
                "a report names a channel exactly when the message was delivered, "
                f"got delivered={self.delivered} and channel={self.channel!r}"
            )

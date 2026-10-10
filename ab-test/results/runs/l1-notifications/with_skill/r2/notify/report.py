from dataclasses import dataclass
from typing import NamedTuple


class Attempt(NamedTuple):
    """One send on one channel. Equal to a plain `(channel, succeeded)` tuple."""

    channel: str
    succeeded: bool


@dataclass(frozen=True)
class DeliveryReport:
    """Whether and where a notification was delivered, with every attempt in order."""

    delivered: bool
    channel: str | None
    attempts: list[Attempt]

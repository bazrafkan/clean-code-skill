"""The outcome of a notification."""

from dataclasses import dataclass
from typing import NamedTuple


class Attempt(NamedTuple):
    """One send attempt; a plain ``(channel, succeeded)`` tuple with names."""

    channel: str
    succeeded: bool


@dataclass(frozen=True)
class DeliveryReport:
    """Whether a notification was delivered, on which channel, and every attempt made."""

    delivered: bool
    channel: str | None
    attempts: list[Attempt]

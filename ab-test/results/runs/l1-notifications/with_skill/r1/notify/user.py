"""Notification recipients and the channels they can be reached on."""

from dataclasses import dataclass
from enum import StrEnum


class Channel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


DEFAULT_PREFERRED_CHANNELS = (Channel.EMAIL,)


@dataclass(init=False)
class User:
    """A recipient: one address per channel and channels in order of preference."""

    id: str
    email: str | None
    phone: str | None
    push_token: str | None
    preferred_channels: list[str]

    # Hand-written so that an explicit preferred_channels=None also gets the default.
    def __init__(
        self,
        id: str,
        email: str | None = None,
        phone: str | None = None,
        push_token: str | None = None,
        preferred_channels: list[str] | None = None,
    ) -> None:
        self.id = id
        self.email = email
        self.phone = phone
        self.push_token = push_token
        self.preferred_channels = list(
            DEFAULT_PREFERRED_CHANNELS
            if preferred_channels is None
            else preferred_channels
        )

    def address_for(self, channel: str) -> str | None:
        """Return the address on ``channel``, or None if there is none.

        None also covers an unknown channel name and an empty address.
        """
        addresses: dict[str, str | None] = {
            Channel.EMAIL: self.email,
            Channel.SMS: self.phone,
            Channel.PUSH: self.push_token,
        }
        return addresses.get(channel) or None

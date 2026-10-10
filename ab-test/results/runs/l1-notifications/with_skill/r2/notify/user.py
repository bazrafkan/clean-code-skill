from collections.abc import Sequence
from enum import StrEnum


class Channel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


DEFAULT_PREFERRED_CHANNELS: tuple[str, ...] = (Channel.EMAIL.value,)


class User:
    """A notification recipient: an address per channel and the order to try them in.

    `preferred_channels` may name unknown channels; the user has no address there.
    """

    def __init__(
        self,
        id: str,
        email: str | None = None,
        phone: str | None = None,
        push_token: str | None = None,
        preferred_channels: Sequence[str] | None = None,
    ) -> None:
        self.id = id
        self.email = email
        self.phone = phone
        self.push_token = push_token
        self.preferred_channels: list[str] = list(
            DEFAULT_PREFERRED_CHANNELS
            if preferred_channels is None
            else preferred_channels
        )

    def address_for(self, channel: str) -> str | None:
        """Return the user's address on `channel`, or None if they have none there."""
        addresses: dict[str, str | None] = {
            Channel.EMAIL: self.email,
            Channel.SMS: self.phone,
            Channel.PUSH: self.push_token,
        }
        return addresses.get(channel)

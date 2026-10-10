"""The recipient of a notification."""

from dataclasses import dataclass
from typing import Any

# Each supported channel and the User attribute that holds its address.
CHANNEL_ADDRESS_FIELDS = {
    "email": "email",
    "sms": "phone",
    "push": "push_token",
}

DEFAULT_CHANNELS = ("email",)


@dataclass
class User:
    """A user with optional addresses and an ordered list of preferred channels."""

    id: Any
    email: str | None = None
    phone: str | None = None
    push_token: str | None = None
    preferred_channels: list[str] | None = None

    def __post_init__(self) -> None:
        if self.preferred_channels is None:
            self.preferred_channels = list(DEFAULT_CHANNELS)
        elif isinstance(self.preferred_channels, str):
            # A bare string would be iterated letter by letter and silently
            # match no channel, so reject it outright.
            raise TypeError("preferred_channels must be a list of channel names, not a string")
        else:
            self.preferred_channels = list(self.preferred_channels)

    def address_for(self, channel: str) -> str | None:
        """Return this user's address for `channel`, or None if there is none.

        Unknown channel names and empty addresses both count as no address.
        """
        field_name = CHANNEL_ADDRESS_FIELDS.get(channel)
        if field_name is None:
            return None
        return getattr(self, field_name) or None

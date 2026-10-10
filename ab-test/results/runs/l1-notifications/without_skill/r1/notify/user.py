"""The notification recipient and the addresses it exposes per channel."""

from dataclasses import dataclass
from typing import Any

DEFAULT_CHANNELS = ("email",)

# Which User attribute holds the address for each known channel.
_ADDRESS_FIELD_BY_CHANNEL = {
    "email": "email",
    "sms": "phone",
    "push": "push_token",
}


@dataclass
class User:
    """A recipient with optional addresses and an ordered channel preference."""

    id: Any
    email: str | None = None
    phone: str | None = None
    push_token: str | None = None
    preferred_channels: list[str] | None = None

    def __post_init__(self) -> None:
        # Copy so later changes to the caller's list do not leak into the user.
        if self.preferred_channels is None:
            self.preferred_channels = list(DEFAULT_CHANNELS)
        else:
            self.preferred_channels = list(self.preferred_channels)

    def address_for(self, channel: str) -> str | None:
        """Return this user's address for ``channel``.

        Returns ``None`` when the channel is unknown or the user has no
        address for it (an empty string counts as no address).
        """
        field_name = _ADDRESS_FIELD_BY_CHANNEL.get(channel)
        if field_name is None:
            return None
        return getattr(self, field_name) or None

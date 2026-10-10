"""The recipient of a notification and the channels they can be reached on."""

from dataclasses import dataclass

# Each known channel and the User attribute that holds its address.
CHANNEL_ADDRESS_FIELDS = {
    "email": "email",
    "sms": "phone",
    "push": "push_token",
}

DEFAULT_CHANNELS = ("email",)


@dataclass
class User:
    id: str
    email: str | None = None
    phone: str | None = None
    push_token: str | None = None
    # Ordered from most to least preferred. None means DEFAULT_CHANNELS.
    preferred_channels: list[str] | None = None

    def __post_init__(self) -> None:
        if self.preferred_channels is None:
            self.preferred_channels = list(DEFAULT_CHANNELS)
        else:
            # Copy so later changes to the caller's list do not leak in.
            self.preferred_channels = list(self.preferred_channels)

    def address_for(self, channel: str) -> str | None:
        """Return the address for `channel`, or None if it is unknown or unset."""
        field_name = CHANNEL_ADDRESS_FIELDS.get(channel)
        if field_name is None:
            return None
        return getattr(self, field_name) or None

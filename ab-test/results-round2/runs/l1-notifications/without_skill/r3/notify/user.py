"""Notification recipients and their per-channel addresses."""

from dataclasses import dataclass

# Each supported channel and the User attribute that holds its address.
CHANNEL_ADDRESS_ATTRIBUTES = {
    "email": "email",
    "sms": "phone",
    "push": "push_token",
}

DEFAULT_CHANNELS = ("email",)


@dataclass
class User:
    """A recipient with an address per channel and an ordered channel preference.

    ``preferred_channels`` defaults to ``["email"]``. The list given is copied,
    so later changes to the caller's list do not affect the user.
    """

    id: object
    email: str | None = None
    phone: str | None = None
    push_token: str | None = None
    preferred_channels: list[str] | None = None

    def __post_init__(self) -> None:
        if self.preferred_channels is None:
            self.preferred_channels = list(DEFAULT_CHANNELS)
        else:
            self.preferred_channels = list(self.preferred_channels)

    def address_for(self, channel: str) -> str | None:
        """Return this user's address on ``channel``.

        Returns None when the channel is unknown or the address is unset or empty.
        """
        attribute = CHANNEL_ADDRESS_ATTRIBUTES.get(channel)
        if attribute is None:
            return None
        return getattr(self, attribute) or None

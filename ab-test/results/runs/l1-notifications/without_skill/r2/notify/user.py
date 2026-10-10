"""The recipient of a notification."""

from dataclasses import dataclass

_DEFAULT_CHANNELS = ("email",)


@dataclass
class User:
    """A user and the addresses at which they can be reached.

    ``preferred_channels`` lists channel names in order of preference;
    omitting it (or passing None) means ``["email"]``. The list is copied,
    so later changes to the caller's list do not affect the user.
    """

    id: object
    email: str | None = None
    phone: str | None = None
    push_token: str | None = None
    preferred_channels: list[str] | None = None

    def __post_init__(self) -> None:
        channels = self.preferred_channels
        self.preferred_channels = list(_DEFAULT_CHANNELS if channels is None else channels)

    def address_for(self, channel: str) -> str | None:
        """Return the user's address on ``channel``.

        Returns None when the channel name is unknown or the user has no
        (or an empty) address for it.
        """
        addresses = {"email": self.email, "sms": self.phone, "push": self.push_token}
        return addresses.get(channel) or None

from enum import StrEnum


class Channel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class User:
    """A notification recipient: their addresses and preferred channels, in order."""

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
        self.preferred_channels: list[str] = (
            [Channel.EMAIL] if preferred_channels is None else list(preferred_channels)
        )

    def address_for(self, channel: str) -> str | None:
        """Return the user's address on `channel`.

        Returns None when the user has no address there or the channel is unknown.
        """
        addresses: dict[str, str | None] = {
            Channel.EMAIL: self.email,
            Channel.SMS: self.phone,
            Channel.PUSH: self.push_token,
        }
        return addresses.get(channel)

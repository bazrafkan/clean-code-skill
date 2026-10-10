from dataclasses import dataclass


@dataclass
class User:
    id: str
    email: str | None = None
    phone: str | None = None
    push_token: str | None = None
    preferred_channels: list[str] | None = None

    def __post_init__(self) -> None:
        if self.preferred_channels is None:
            self.preferred_channels = ["email"]

    def address_for(self, channel: str) -> str | None:
        """Returns None when the channel is unknown or the user has no address for it."""
        addresses = {"email": self.email, "sms": self.phone, "push": self.push_token}
        return addresses.get(channel)

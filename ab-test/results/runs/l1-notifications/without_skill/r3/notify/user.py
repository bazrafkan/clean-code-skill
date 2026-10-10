"""The recipient of a notification and the addresses it can be reached at."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_CHANNELS = ("email",)

# Channel name -> name of the User attribute holding the address for it.
_ADDRESS_FIELD_BY_CHANNEL = {
    "email": "email",
    "sms": "phone",
    "push": "push_token",
}


@dataclass
class User:
    """A user who can be notified on one or more channels.

    ``preferred_channels`` is the ordered list of channels to try. It defaults
    to ``["email"]`` and is copied, so later changes to the list passed in do
    not affect the user.
    """

    id: Any
    email: Optional[str] = None
    phone: Optional[str] = None
    push_token: Optional[str] = None
    preferred_channels: Optional[list[str]] = None

    def __post_init__(self) -> None:
        if self.preferred_channels is None:
            self.preferred_channels = list(DEFAULT_CHANNELS)
        elif isinstance(self.preferred_channels, str):
            raise TypeError(
                "preferred_channels must be a list of channel names, "
                f"not the string {self.preferred_channels!r}"
            )
        else:
            self.preferred_channels = list(self.preferred_channels)

    def address_for(self, channel: str) -> Optional[str]:
        """Return the user's address for ``channel``.

        Returns ``None`` when the channel name is unknown or when the user has
        no (or an empty) address for it.
        """
        field_name = _ADDRESS_FIELD_BY_CHANNEL.get(channel)
        if field_name is None:
            return None
        return getattr(self, field_name) or None

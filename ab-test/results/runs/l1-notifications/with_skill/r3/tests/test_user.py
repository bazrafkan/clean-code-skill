from typing import Any

import pytest

from notify import User


@pytest.mark.parametrize("channels_kwarg", [{}, {"preferred_channels": None}])
def test_preferred_channels_default_to_email(channels_kwarg: dict[str, Any]) -> None:
    user = User("u1", **channels_kwarg)

    assert user.preferred_channels == ["email"]


def test_empty_preferred_channels_stay_empty() -> None:
    user = User("u1", preferred_channels=[])

    assert user.preferred_channels == []


def test_preferred_channels_are_not_shared_with_the_caller() -> None:
    channels = ["sms"]
    user = User("u1", preferred_channels=channels)

    channels.append("push")

    assert user.preferred_channels == ["sms"]


@pytest.mark.parametrize(
    ("channel", "expected_address"),
    [("email", "alice@example.com"), ("sms", "+390351234567"), ("push", "token-1")],
)
def test_address_for_returns_the_address_of_each_channel(
    channel: str, expected_address: str
) -> None:
    user = User(
        "u1", email="alice@example.com", phone="+390351234567", push_token="token-1"
    )

    assert user.address_for(channel) == expected_address


def test_address_for_returns_none_when_the_user_has_no_address_there() -> None:
    user = User("u1", email="alice@example.com")

    assert user.address_for("sms") is None


def test_address_for_returns_none_for_an_unknown_channel() -> None:
    user = User("u1", email="alice@example.com")

    assert user.address_for("fax") is None

import pytest

from notify import User


def test_preferred_channels_default_to_email() -> None:
    user = User("alice", email="alice@example.com")

    assert user.preferred_channels == ["email"]
    assert repr(user.preferred_channels) == "['email']"


def test_explicit_none_preferred_channels_default_to_email() -> None:
    user = User("alice", preferred_channels=None)

    assert user.preferred_channels == ["email"]


def test_empty_preferred_channels_stay_empty() -> None:
    user = User("alice", preferred_channels=[])

    assert user.preferred_channels == []


def test_preferred_channels_keep_their_order() -> None:
    user = User("alice", preferred_channels=["push", "sms", "email"])

    assert user.preferred_channels == ["push", "sms", "email"]


def test_preferred_channels_are_isolated_from_the_callers_list() -> None:
    channels = ["sms"]
    user = User("alice", preferred_channels=channels)

    channels.append("email")

    assert user.preferred_channels == ["sms"]


@pytest.mark.parametrize(
    ("channel", "expected_address"),
    [("email", "alice@example.com"), ("sms", "+390351234567"), ("push", "token-1")],
)
def test_address_for_returns_the_channels_address(
    channel: str, expected_address: str
) -> None:
    user = User(
        "alice", email="alice@example.com", phone="+390351234567", push_token="token-1"
    )

    assert user.address_for(channel) == expected_address


def test_address_for_a_channel_the_user_has_no_address_for_is_none() -> None:
    user = User("alice", email="alice@example.com")

    assert user.address_for("sms") is None


def test_address_for_an_unknown_channel_is_none() -> None:
    user = User("alice", email="alice@example.com")

    assert user.address_for("fax") is None

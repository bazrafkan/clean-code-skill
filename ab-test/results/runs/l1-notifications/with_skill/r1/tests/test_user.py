import pytest

from notify import User

EMAIL = "ada@example.com"
PHONE = "+39 035 123 4567"
PUSH_TOKEN = "push-token-ada"


def test_preferred_channels_default_to_email() -> None:
    assert User("ada").preferred_channels == ["email"]


def test_each_user_gets_its_own_default_channel_list() -> None:
    first, second = User("ada"), User("bob")

    first.preferred_channels.append("sms")

    assert second.preferred_channels == ["email"]


def test_explicitly_empty_preferred_channels_stay_empty() -> None:
    assert User("ada", preferred_channels=[]).preferred_channels == []


def test_preferred_channels_are_copied_from_the_caller() -> None:
    channels = ["sms"]
    user = User("ada", preferred_channels=channels)

    channels.append("push")

    assert user.preferred_channels == ["sms"]


@pytest.mark.parametrize(
    ("channel", "address"),
    [("email", EMAIL), ("sms", PHONE), ("push", PUSH_TOKEN)],
)
def test_address_for_returns_the_address_of_each_channel(
    channel: str, address: str
) -> None:
    user = User("ada", email=EMAIL, phone=PHONE, push_token=PUSH_TOKEN)

    assert user.address_for(channel) == address


def test_address_for_unknown_channel_is_none() -> None:
    user = User("ada", email=EMAIL)

    assert user.address_for("fax") is None


def test_address_for_channel_without_address_is_none() -> None:
    user = User("ada", email=EMAIL)

    assert user.address_for("sms") is None


def test_address_for_channel_with_empty_address_is_none() -> None:
    user = User("ada", email="")

    assert user.address_for("email") is None

import pytest

from notify import User


def test_preferred_channels_default_to_email():
    assert User("u1").preferred_channels == ["email"]


def test_default_preferred_channels_are_not_shared_between_users():
    first, second = User("u1"), User("u2")

    first.preferred_channels.append("sms")

    assert second.preferred_channels == ["email"]


@pytest.mark.parametrize(
    "channel, address",
    [("email", "ann@example.com"), ("sms", "+390000000"), ("push", "device-1")],
)
def test_address_for_returns_the_channels_address(channel, address):
    user = User("u1", email="ann@example.com", phone="+390000000", push_token="device-1")

    assert user.address_for(channel) == address


def test_address_for_is_none_when_user_has_no_address_for_channel():
    assert User("u1", email="ann@example.com").address_for("sms") is None


def test_address_for_is_none_for_unknown_channel():
    assert User("u1", email="ann@example.com").address_for("fax") is None

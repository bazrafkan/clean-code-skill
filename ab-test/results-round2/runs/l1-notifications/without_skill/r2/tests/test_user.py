import pytest

from notify import User


def test_preferred_channels_default_to_email():
    assert User(1).preferred_channels == ["email"]
    assert User(1, preferred_channels=None).preferred_channels == ["email"]


def test_default_channels_are_not_shared_between_users():
    first, second = User(1), User(2)
    first.preferred_channels.append("sms")
    assert second.preferred_channels == ["email"]


def test_preferred_channels_are_copied():
    channels = ["sms", "email"]
    user = User(1, preferred_channels=channels)
    channels.append("push")
    assert user.preferred_channels == ["sms", "email"]


def test_preferred_channels_as_string_is_rejected():
    with pytest.raises(TypeError):
        User(1, preferred_channels="email")


def test_address_for_maps_each_channel_to_its_field():
    user = User(1, email="a@example.com", phone="+39123", push_token="tok")
    assert user.address_for("email") == "a@example.com"
    assert user.address_for("sms") == "+39123"
    assert user.address_for("push") == "tok"


def test_address_for_missing_empty_or_unknown_is_none():
    user = User(1, email="", phone=None)
    assert user.address_for("email") is None
    assert user.address_for("sms") is None
    assert user.address_for("fax") is None

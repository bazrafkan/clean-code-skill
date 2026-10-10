import pytest

from notify import User


def test_preferred_channels_default_to_email():
    assert User(id=1).preferred_channels == ["email"]


def test_default_channels_are_not_shared_between_users():
    first, second = User(id=1), User(id=2)
    first.preferred_channels.append("sms")
    assert second.preferred_channels == ["email"]


def test_preferred_channels_are_copied():
    channels = ["sms", "email"]
    user = User(id=1, preferred_channels=channels)
    channels.append("push")
    assert user.preferred_channels == ["sms", "email"]


def test_a_bare_string_is_rejected_as_preferred_channels():
    with pytest.raises(TypeError):
        User(id=1, preferred_channels="email")


@pytest.mark.parametrize(
    ("channel", "expected"),
    [("email", "a@b.c"), ("sms", "+39123"), ("push", "tok-1")],
)
def test_address_for_known_channels(channel, expected):
    user = User(id=1, email="a@b.c", phone="+39123", push_token="tok-1")
    assert user.address_for(channel) == expected


@pytest.mark.parametrize("channel", ["email", "sms", "push", "fax"])
def test_address_for_returns_none_when_missing_or_unknown(channel):
    assert User(id=1).address_for(channel) is None


def test_empty_address_counts_as_missing():
    assert User(id=1, email="").address_for("email") is None

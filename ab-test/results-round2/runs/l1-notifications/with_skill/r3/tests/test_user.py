import pytest

from notify import User


def test_preferred_channels_default_to_email():
    assert User(id="u1").preferred_channels == ["email"]


@pytest.mark.parametrize(
    ("channel", "expected_address"),
    [("email", "ada@example.com"), ("sms", "+39021234567"), ("push", "token-1")],
)
def test_address_for_returns_the_address_matching_the_channel(channel, expected_address):
    user = User(id="u1", email="ada@example.com", phone="+39021234567", push_token="token-1")

    assert user.address_for(channel) == expected_address


def test_address_for_returns_none_when_the_user_has_no_address_for_the_channel():
    assert User(id="u1", email="ada@example.com").address_for("sms") is None


def test_address_for_returns_none_for_an_unknown_channel():
    assert User(id="u1", email="ada@example.com").address_for("fax") is None

from notify import User


def test_preferred_channels_default_to_email():
    assert User(id="u1").preferred_channels == ["email"]


def test_address_for_maps_each_channel_to_its_address():
    user = User(id="u1", email="ada@example.com", phone="+39 000", push_token="tok")

    assert user.address_for("email") == "ada@example.com"
    assert user.address_for("sms") == "+39 000"
    assert user.address_for("push") == "tok"


def test_address_for_unknown_channel_is_none():
    assert User(id="u1", email="ada@example.com").address_for("fax") is None

from notify import User


def test_preferred_channels_default_to_email():
    assert User(id=1).preferred_channels == ["email"]


def test_default_channels_are_not_shared_between_users():
    first, second = User(id=1), User(id=2)

    first.preferred_channels.append("sms")

    assert second.preferred_channels == ["email"]


def test_preferred_channels_are_copied_from_the_caller():
    channels = ["sms", "email"]
    user = User(id=1, preferred_channels=channels)

    channels.append("push")

    assert user.preferred_channels == ["sms", "email"]


def test_address_for_maps_each_channel_to_its_address():
    user = User(id=1, email="a@example.com", phone="+391234", push_token="tok")

    assert user.address_for("email") == "a@example.com"
    assert user.address_for("sms") == "+391234"
    assert user.address_for("push") == "tok"


def test_address_for_is_none_for_missing_empty_or_unknown():
    user = User(id=1, email="", phone=None)

    assert user.address_for("email") is None
    assert user.address_for("sms") is None
    assert user.address_for("fax") is None

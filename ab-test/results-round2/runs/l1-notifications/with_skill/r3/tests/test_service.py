import math

import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class FakeSender:
    """Raises DeliveryError for the first `failures` sends, then succeeds. Records every call."""

    def __init__(self, failures=0):
        self._failures_left = failures
        self.calls = []

    def send(self, address, message):
        self.calls.append((address, message))
        if self._failures_left > 0:
            self._failures_left -= 1
            raise DeliveryError(f"simulated failure sending to {address}")


class CrashingSender:
    def send(self, address, message):
        raise RuntimeError("sender bug")


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("welcome", "Hello {name}!")
    return store


def make_user(preferred_channels):
    return User(
        id="u1",
        email="ada@example.com",
        phone="+39021234567",
        push_token="token-1",
        preferred_channels=preferred_channels,
    )


def test_rejects_negative_max_retries(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_sends_the_rendered_message_to_the_address_of_the_first_preferred_channel(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(make_user(["email"]), "welcome", name="Ada")

    assert email.calls == [("ada@example.com", "Hello Ada!")]
    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])


def test_accepts_template_parameters_named_like_its_own_arguments(templates):
    templates.add("mention", "{user} used {template_name}")
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    service.notify(make_user(["email"]), "mention", user="Ada", template_name="welcome")

    assert email.calls == [("ada@example.com", "Ada used welcome")]


def test_retries_the_same_channel_until_it_succeeds(templates):
    service = NotificationService({"sms": FakeSender(failures=2)}, templates, max_retries=2)

    report = service.notify(make_user(["sms"]), "welcome", name="Ada")

    assert report == DeliveryReport(
        delivered=True,
        channel="sms",
        attempts=[("sms", False), ("sms", False), ("sms", True)],
    )


def test_retries_twice_by_default(templates):
    service = NotificationService({"email": FakeSender(failures=math.inf)}, templates)

    report = service.notify(make_user(["email"]), "welcome", name="Ada")

    assert report.attempts == [("email", False)] * 3


def test_falls_back_to_the_next_channel_after_retries_are_exhausted(templates):
    senders = {"email": FakeSender(failures=math.inf), "push": FakeSender()}
    service = NotificationService(senders, templates, max_retries=1)

    report = service.notify(make_user(["email", "push"]), "welcome", name="Ada")

    assert report == DeliveryReport(
        delivered=True,
        channel="push",
        attempts=[("email", False), ("email", False), ("push", True)],
    )


def test_makes_a_single_attempt_per_channel_when_max_retries_is_zero(templates):
    senders = {"email": FakeSender(failures=math.inf), "sms": FakeSender()}
    service = NotificationService(senders, templates, max_retries=0)

    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")

    assert report.attempts == [("email", False), ("sms", True)]


def test_reports_failure_when_every_channel_fails(templates):
    senders = {"email": FakeSender(failures=math.inf), "sms": FakeSender(failures=math.inf)}
    service = NotificationService(senders, templates, max_retries=0)

    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")

    assert report == DeliveryReport(
        delivered=False, channel=None, attempts=[("email", False), ("sms", False)]
    )


def test_stops_at_the_first_successful_send(templates):
    sms = FakeSender()
    service = NotificationService({"email": FakeSender(), "sms": sms}, templates)

    service.notify(make_user(["email", "sms"]), "welcome", name="Ada")

    assert sms.calls == []


def test_skips_a_channel_without_a_sender_and_records_no_attempt(templates):
    service = NotificationService({"sms": FakeSender()}, templates)

    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")

    assert report.attempts == [("sms", True)]


def test_skips_a_channel_the_user_has_no_address_for(templates):
    email = FakeSender()
    service = NotificationService({"email": email, "sms": FakeSender()}, templates)
    user = User(id="u1", phone="+39021234567", preferred_channels=["email", "sms"])

    report = service.notify(user, "welcome", name="Ada")

    assert email.calls == []
    assert report.attempts == [("sms", True)]


def test_skips_an_unknown_channel(templates):
    fax = FakeSender()
    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)

    report = service.notify(make_user(["fax", "email"]), "welcome", name="Ada")

    assert fax.calls == []
    assert report.attempts == [("email", True)]


def test_reports_no_attempts_when_no_channel_is_reachable(templates):
    service = NotificationService({}, templates)

    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")

    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])


def test_unknown_template_propagates_before_anything_is_sent(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(KeyError):
        service.notify(make_user(["email"]), "goodbye", name="Ada")
    assert email.calls == []


def test_missing_template_parameter_propagates_before_anything_is_sent(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(ValueError):
        service.notify(make_user(["email"]), "welcome")
    assert email.calls == []


def test_errors_other_than_delivery_error_propagate_without_fallback(templates):
    sms = FakeSender()
    service = NotificationService({"email": CrashingSender(), "sms": sms}, templates)

    with pytest.raises(RuntimeError):
        service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
    assert sms.calls == []

import math

import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class ScriptedSender:
    """Fails the first ``failures`` sends, then succeeds; records every call."""

    def __init__(self, failures=0):
        self._failures_left = failures
        self.calls = []

    def send(self, address, message):
        self.calls.append((address, message))
        if self._failures_left > 0:
            self._failures_left -= 1
            raise DeliveryError("simulated failure")


def failing_sender():
    return ScriptedSender(failures=math.inf)


class CrashingSender:
    def send(self, address, message):
        raise RuntimeError("bug in sender")


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("hello", "Hello {name}")
    return store


def make_user(channels=None):
    return User(
        id=1,
        email="ada@example.com",
        phone="+391234",
        push_token="tok",
        preferred_channels=channels,
    )


def test_delivers_rendered_message_to_first_preferred_channel(templates):
    email = ScriptedSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(make_user(), "hello", name="Ada")

    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
    assert email.calls == [("ada@example.com", "Hello Ada")]


def test_sends_to_the_address_of_each_channel(templates):
    sms, push = failing_sender(), ScriptedSender()
    service = NotificationService({"sms": sms, "push": push}, templates, max_retries=0)

    service.notify(make_user(["sms", "push"]), "hello", name="Ada")

    assert sms.calls == [("+391234", "Hello Ada")]
    assert push.calls == [("tok", "Hello Ada")]


def test_retries_same_channel_until_it_succeeds(templates):
    email = ScriptedSender(failures=2)
    service = NotificationService({"email": email}, templates, max_retries=2)

    report = service.notify(make_user(), "hello", name="Ada")

    assert report.delivered
    assert report.channel == "email"
    assert report.attempts == [("email", False), ("email", False), ("email", True)]


def test_falls_back_to_next_channel_after_retries_run_out(templates):
    service = NotificationService(
        {"email": failing_sender(), "sms": ScriptedSender()}, templates, max_retries=1
    )

    report = service.notify(make_user(["email", "sms"]), "hello", name="Ada")

    assert report.channel == "sms"
    assert report.attempts == [("email", False), ("email", False), ("sms", True)]


def test_default_max_retries_is_two(templates):
    service = NotificationService({"email": failing_sender()}, templates)

    report = service.notify(make_user(), "hello", name="Ada")

    assert report.attempts == [("email", False)] * 3


def test_zero_retries_means_one_attempt_per_channel(templates):
    service = NotificationService(
        {"email": failing_sender(), "push": failing_sender()}, templates, max_retries=0
    )

    report = service.notify(make_user(["email", "push"]), "hello", name="Ada")

    assert report.attempts == [("email", False), ("push", False)]


def test_reports_failure_when_every_channel_fails(templates):
    service = NotificationService(
        {"email": failing_sender(), "sms": failing_sender()}, templates, max_retries=0
    )

    report = service.notify(make_user(["email", "sms"]), "hello", name="Ada")

    assert report == DeliveryReport(
        delivered=False, channel=None, attempts=[("email", False), ("sms", False)]
    )


def test_stops_at_first_successful_send(templates):
    email, sms = ScriptedSender(), ScriptedSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    service.notify(make_user(["email", "sms"]), "hello", name="Ada")

    assert sms.calls == []


def test_skips_channel_without_a_sender(templates):
    service = NotificationService({"sms": ScriptedSender()}, templates)

    report = service.notify(make_user(["email", "sms"]), "hello", name="Ada")

    assert report.attempts == [("sms", True)]


def test_skips_channel_without_an_address(templates):
    email, sms = ScriptedSender(), ScriptedSender()
    service = NotificationService({"email": email, "sms": sms}, templates)
    user = User(id=1, phone="+391234", preferred_channels=["email", "sms"])

    report = service.notify(user, "hello", name="Ada")

    assert report.attempts == [("sms", True)]
    assert email.calls == []


def test_skips_unknown_channel_even_with_a_sender(templates):
    fax = ScriptedSender()
    service = NotificationService({"fax": fax, "email": ScriptedSender()}, templates)

    report = service.notify(make_user(["fax", "email"]), "hello", name="Ada")

    assert report.attempts == [("email", True)]
    assert fax.calls == []


def test_no_reachable_channel_reports_no_attempts(templates):
    service = NotificationService({"email": ScriptedSender()}, templates)

    report = service.notify(User(id=1), "hello", name="Ada")

    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])


def test_unknown_template_fails_before_sending(templates):
    email = ScriptedSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(KeyError):
        service.notify(make_user(), "missing")
    assert email.calls == []


def test_missing_parameter_fails_before_sending(templates):
    email = ScriptedSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(ValueError):
        service.notify(make_user(), "hello")
    assert email.calls == []


def test_non_delivery_errors_propagate(templates):
    service = NotificationService(
        {"email": CrashingSender(), "sms": ScriptedSender()}, templates
    )

    with pytest.raises(RuntimeError):
        service.notify(make_user(["email", "sms"]), "hello", name="Ada")


def test_template_params_may_share_names_with_notify_arguments(templates):
    templates.add("clash", "{user} used {template_name}")
    email = ScriptedSender()
    service = NotificationService({"email": email}, templates)

    service.notify(make_user(), "clash", user="Ada", template_name="clash")

    assert email.calls == [("ada@example.com", "Ada used clash")]


def test_negative_max_retries_is_rejected(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)

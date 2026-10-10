import math

import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class FakeSender:
    """Records every call; raises ``error`` on the first ``failures`` calls."""

    def __init__(self, failures=0, error=DeliveryError):
        self.calls = []
        self._failures = failures
        self._error = error

    def send(self, address, message):
        self.calls.append((address, message))
        if len(self.calls) <= self._failures:
            raise self._error("send failed")


def always_failing():
    return FakeSender(failures=math.inf)


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("greet", "Hi {name}")
    return store


@pytest.fixture
def user():
    return User(
        id=7,
        email="ada@example.com",
        phone="+39123",
        push_token="tok-1",
        preferred_channels=["email", "sms", "push"],
    )


def test_negative_max_retries_is_rejected(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_first_channel_success_sends_rendered_message_to_its_address(templates, user):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(user, "greet", name="Ada")

    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
    assert email.calls == [("ada@example.com", "Hi Ada")]


def test_retries_same_channel_until_it_succeeds(templates, user):
    email = FakeSender(failures=1)
    service = NotificationService({"email": email}, templates, max_retries=2)

    report = service.notify(user, "greet", name="Ada")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", False), ("email", True)]


def test_falls_back_after_exhausting_retries(templates, user):
    email, sms = always_failing(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=2)

    report = service.notify(user, "greet", name="Ada")

    assert report.channel == "sms"
    assert report.attempts == [("email", False)] * 3 + [("sms", True)]
    assert sms.calls == [("+39123", "Hi Ada")]


def test_zero_retries_means_one_attempt_per_channel(templates, user):
    email, sms = always_failing(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=0)

    report = service.notify(user, "greet", name="Ada")

    assert report.attempts == [("email", False), ("sms", True)]


def test_stops_at_first_success(templates, user):
    email, sms = FakeSender(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    service.notify(user, "greet", name="Ada")

    assert sms.calls == []


def test_all_channels_failing_reports_not_delivered(templates, user):
    senders = {"email": always_failing(), "sms": always_failing(), "push": always_failing()}
    service = NotificationService(senders, templates, max_retries=1)

    report = service.notify(user, "greet", name="Ada")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == [
        ("email", False), ("email", False),
        ("sms", False), ("sms", False),
        ("push", False), ("push", False),
    ]


def test_skips_channels_without_sender_address_or_known_name(templates):
    push = FakeSender()
    user = User(id=1, email="a@example.com", push_token="tok",
                preferred_channels=["fax", "email", "sms", "push"])
    # "fax" is unknown, "email" has no sender, "sms" has no address.
    service = NotificationService({"fax": FakeSender(), "sms": FakeSender(), "push": push},
                                  templates)

    report = service.notify(user, "greet", name="Ada")

    assert report == DeliveryReport(delivered=True, channel="push", attempts=[("push", True)])


def test_no_usable_channel_reports_not_delivered_without_attempts(templates):
    user = User(id=1)  # prefers email but has no email address
    service = NotificationService({"email": FakeSender()}, templates)

    report = service.notify(user, "greet", name="Ada")

    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])


@pytest.mark.parametrize(
    ("template_name", "params", "error"),
    [("unknown", {"name": "Ada"}, KeyError), ("greet", {}, ValueError)],
)
def test_template_errors_propagate_before_sending(templates, user, template_name, params, error):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(error):
        service.notify(user, template_name, **params)

    assert email.calls == []


def test_other_exceptions_propagate_without_retry(templates, user):
    email = FakeSender(failures=1, error=RuntimeError)
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    with pytest.raises(RuntimeError):
        service.notify(user, "greet", name="Ada")

    assert len(email.calls) == 1
    assert sms.calls == []


def test_delivery_error_subclasses_are_retried(templates, user):
    class Timeout(DeliveryError):
        pass

    service = NotificationService({"email": FakeSender(failures=1, error=Timeout)}, templates)

    report = service.notify(user, "greet", name="Ada")

    assert report.attempts == [("email", False), ("email", True)]


def test_templates_may_use_user_and_template_name_placeholders(templates, user):
    templates.add("meta", "{user} got {template_name}")
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    service.notify(user, "meta", user="Ada", template_name="news")

    assert email.calls == [("ada@example.com", "Ada got news")]

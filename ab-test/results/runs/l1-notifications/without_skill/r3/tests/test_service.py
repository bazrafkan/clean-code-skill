import pytest

from notify import (
    DeliveryError,
    DeliveryReport,
    NotificationService,
    TemplateStore,
    User,
)


class FakeSender:
    """Records calls; fails the first ``failures`` sends with DeliveryError."""

    def __init__(self, failures=0):
        self.failures = failures
        self.calls = []

    def send(self, address, message):
        self.calls.append((address, message))
        if len(self.calls) <= self.failures:
            raise DeliveryError(f"send #{len(self.calls)} failed")


class AlwaysFails(FakeSender):
    def __init__(self):
        super().__init__(failures=float("inf"))


class Explodes:
    def send(self, address, message):
        raise RuntimeError("bug in sender")


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("hi", "Hi {name}")
    return store


def full_user(channels):
    return User(
        id=7,
        email="u@example.com",
        phone="+39000",
        push_token="tok",
        preferred_channels=channels,
    )


def test_max_retries_must_not_be_negative(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_zero_retries_is_allowed(templates):
    NotificationService({}, templates, max_retries=0)


def test_delivers_on_first_channel(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(User(id=1, email="u@example.com"), "hi", name="Ada")

    assert report == DeliveryReport(
        delivered=True, channel="email", attempts=[("email", True)]
    )
    assert email.calls == [("u@example.com", "Hi Ada")]


def test_sends_to_the_address_of_each_channel(templates):
    sms, push = AlwaysFails(), FakeSender()
    service = NotificationService({"sms": sms, "push": push}, templates, max_retries=0)

    service.notify(full_user(["sms", "push"]), "hi", name="Ada")

    assert sms.calls == [("+39000", "Hi Ada")]
    assert push.calls == [("tok", "Hi Ada")]


def test_retries_same_channel_until_success(templates):
    email = FakeSender(failures=2)
    service = NotificationService({"email": email}, templates, max_retries=2)

    report = service.notify(full_user(["email", "sms"]), "hi", name="Ada")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", False), ("email", False), ("email", True)]


def test_falls_back_after_retries_are_exhausted(templates):
    email, sms = AlwaysFails(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)

    report = service.notify(full_user(["email", "sms"]), "hi", name="Ada")

    assert report == DeliveryReport(
        delivered=True,
        channel="sms",
        attempts=[("email", False), ("email", False), ("sms", True)],
    )
    assert len(email.calls) == 2


def test_default_max_retries_is_two(templates):
    email = AlwaysFails()
    service = NotificationService({"email": email}, templates)

    report = service.notify(full_user(["email"]), "hi", name="Ada")

    assert len(email.calls) == 3
    assert report.attempts == [("email", False)] * 3


def test_reports_failure_when_every_channel_fails(templates):
    service = NotificationService(
        {"email": AlwaysFails(), "push": AlwaysFails()}, templates, max_retries=0
    )

    report = service.notify(full_user(["email", "push"]), "hi", name="Ada")

    assert report == DeliveryReport(
        delivered=False,
        channel=None,
        attempts=[("email", False), ("push", False)],
    )


def test_stops_at_first_success(templates):
    email, sms = FakeSender(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    service.notify(full_user(["email", "sms"]), "hi", name="Ada")

    assert sms.calls == []


def test_follows_preferred_channel_order(templates):
    email, push = FakeSender(), FakeSender()
    service = NotificationService({"email": email, "push": push}, templates)

    report = service.notify(full_user(["push", "email"]), "hi", name="Ada")

    assert report.channel == "push"
    assert email.calls == []


def test_skips_channel_without_sender(templates):
    service = NotificationService({"email": FakeSender()}, templates)

    report = service.notify(full_user(["sms", "email"]), "hi", name="Ada")

    assert report.attempts == [("email", True)]


def test_skips_channel_without_address(templates):
    sms = FakeSender()
    service = NotificationService({"sms": sms, "email": FakeSender()}, templates)
    user = User(id=1, email="u@example.com", preferred_channels=["sms", "email"])

    report = service.notify(user, "hi", name="Ada")

    assert report.attempts == [("email", True)]
    assert sms.calls == []


def test_skips_unknown_channel_even_with_a_sender(templates):
    fax = FakeSender()
    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)

    report = service.notify(full_user(["fax", "email"]), "hi", name="Ada")

    assert report.attempts == [("email", True)]
    assert fax.calls == []


def test_no_usable_channel_gives_empty_failed_report(templates):
    service = NotificationService({}, templates)

    report = service.notify(full_user(["email", "sms"]), "hi", name="Ada")

    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])


def test_unknown_template_propagates_before_sending(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(KeyError):
        service.notify(full_user(["email"]), "nope")
    assert email.calls == []


def test_missing_parameter_propagates_before_sending(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(ValueError):
        service.notify(full_user(["email"]), "hi")
    assert email.calls == []


def test_template_errors_raise_even_with_no_usable_channel(templates):
    service = NotificationService({}, templates)

    with pytest.raises(ValueError):
        service.notify(User(id=1), "hi")


def test_other_sender_exceptions_propagate_without_retry(templates):
    sms = FakeSender()
    service = NotificationService({"email": Explodes(), "sms": sms}, templates)

    with pytest.raises(RuntimeError):
        service.notify(full_user(["email", "sms"]), "hi", name="Ada")
    assert sms.calls == []


def test_delivery_error_subclasses_are_retried(templates):
    class Timeout(DeliveryError):
        pass

    class FlakySender:
        def __init__(self):
            self.calls = 0

        def send(self, address, message):
            self.calls += 1
            if self.calls == 1:
                raise Timeout()

    service = NotificationService({"email": FlakySender()}, templates)

    report = service.notify(full_user(["email"]), "hi", name="Ada")

    assert report.attempts == [("email", False), ("email", True)]


def test_templates_may_use_user_and_template_name_placeholders(templates):
    templates.add("meta", "{user} got {template_name}")
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    service.notify(full_user(["email"]), "meta", user="Ada", template_name="meta")

    assert email.calls == [("u@example.com", "Ada got meta")]


def test_each_notify_call_gets_its_own_report(templates):
    service = NotificationService({"email": FakeSender()}, templates)
    user = full_user(["email"])

    first = service.notify(user, "hi", name="Ada")
    second = service.notify(user, "hi", name="Bob")

    assert first.attempts == [("email", True)]
    assert second.attempts == [("email", True)]
    assert first.attempts is not second.attempts

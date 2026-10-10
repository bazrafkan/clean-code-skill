import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class FakeSender:
    """Records calls; fails with DeliveryError for the first `failures` sends."""

    def __init__(self, failures=0, error=None):
        self.failures = failures
        self.error = error
        self.calls = []

    def send(self, address, message):
        self.calls.append((address, message))
        if self.error is not None:
            raise self.error
        if len(self.calls) <= self.failures:
            raise DeliveryError("down")


ALWAYS_FAILS = 10**6


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("welcome", "Hello {name}")
    return store


def full_user(channels):
    return User(
        1,
        email="a@example.com",
        phone="+39123",
        push_token="tok",
        preferred_channels=channels,
    )


def test_negative_max_retries_is_rejected(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_delivers_on_first_preferred_channel(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(User(1, email="a@example.com"), "welcome", name="Ann")

    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
    assert email.calls == [("a@example.com", "Hello Ann")]


def test_retries_same_channel_until_success(templates):
    email = FakeSender(failures=2)
    service = NotificationService({"email": email}, templates, max_retries=2)

    report = service.notify(User(1, email="a@example.com"), "welcome", name="Ann")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", False), ("email", False), ("email", True)]


def test_falls_back_after_retries_are_exhausted(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=2)

    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ann")

    assert report.channel == "sms"
    assert report.attempts == [("email", False)] * 3 + [("sms", True)]
    assert sms.calls == [("+39123", "Hello Ann")]


def test_zero_retries_means_one_attempt_per_channel(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    push = FakeSender()
    service = NotificationService({"email": email, "push": push}, templates, max_retries=0)

    report = service.notify(full_user(["email", "push"]), "welcome", name="Ann")

    assert report.attempts == [("email", False), ("push", True)]
    assert push.calls == [("tok", "Hello Ann")]


def test_stops_at_first_success(templates):
    email, sms = FakeSender(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    service.notify(full_user(["email", "sms"]), "welcome", name="Ann")

    assert sms.calls == []


def test_all_channels_failing_is_reported(templates):
    senders = {"email": FakeSender(failures=ALWAYS_FAILS), "sms": FakeSender(failures=ALWAYS_FAILS)}
    service = NotificationService(senders, templates, max_retries=1)

    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ann")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == [("email", False), ("email", False), ("sms", False), ("sms", False)]


def test_skips_channels_without_sender_address_or_known_name(templates):
    push = FakeSender()
    fax = FakeSender()
    service = NotificationService({"push": push, "fax": fax, "email": FakeSender()}, templates)
    user = User(1, phone="+39123", push_token="tok", preferred_channels=["fax", "sms", "email", "push"])

    report = service.notify(user, "welcome", name="Ann")

    # fax: unknown name; sms: no sender; email: no address.
    assert report.attempts == [("push", True)]
    assert fax.calls == []


def test_no_usable_channel_gives_empty_report(templates):
    service = NotificationService({}, templates)

    report = service.notify(User(1, email="a@example.com"), "welcome", name="Ann")

    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])


@pytest.mark.parametrize(
    "template_name, params, error",
    [("missing", {"name": "Ann"}, KeyError), ("welcome", {}, ValueError)],
)
def test_template_errors_propagate_before_sending(templates, template_name, params, error):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(error):
        service.notify(User(1, email="a@example.com"), template_name, **params)

    assert email.calls == []


def test_non_delivery_errors_propagate(templates):
    email = FakeSender(error=RuntimeError("bug"))
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    with pytest.raises(RuntimeError):
        service.notify(full_user(["email", "sms"]), "welcome", name="Ann")

    assert len(email.calls) == 1
    assert sms.calls == []


def test_template_may_use_user_and_template_name_placeholders():
    store = TemplateStore()
    store.add("t", "{user} got {template_name}")
    email = FakeSender()
    service = NotificationService({"email": email}, store)

    service.notify(User(1, email="a@example.com"), "t", user="Ann", template_name="news")

    assert email.calls == [("a@example.com", "Ann got news")]

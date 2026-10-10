import pytest

from notify import DeliveryError, NotificationService, TemplateStore, User


class FakeSender:
    """Fails the first `failures` sends with DeliveryError, then succeeds."""

    def __init__(self, failures: int = 0) -> None:
        self.failures_left = failures
        self.calls: list[tuple[str, str]] = []

    def send(self, address: str, message: str) -> None:
        self.calls.append((address, message))
        if self.failures_left > 0:
            self.failures_left -= 1
            raise DeliveryError(f"could not reach {address}")


class BrokenSender:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, address: str, message: str) -> None:
        self.calls += 1
        raise DeliveryError(f"could not reach {address}")


@pytest.fixture
def templates() -> TemplateStore:
    templates = TemplateStore()
    templates.add("greeting", "Hello {name}")
    return templates


def make_user(preferred_channels=None) -> User:
    return User(
        id="u1",
        email="ada@example.com",
        phone="+39 000",
        push_token="tok",
        preferred_channels=preferred_channels,
    )


def test_negative_max_retries_raises_value_error(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_delivers_rendered_message_to_first_preferred_channel(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(make_user(), "greeting", name="Ada")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", True)]
    assert email.calls == [("ada@example.com", "Hello Ada")]


def test_template_parameters_may_reuse_notify_argument_names(templates):
    templates.add("handover", "{user} passes {template_name} on")
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    service.notify(make_user(), "handover", user="Ada", template_name="the baton")

    assert email.calls == [("ada@example.com", "Ada passes the baton on")]


def test_user_without_preferences_is_notified_by_email(templates):
    email, sms = FakeSender(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    report = service.notify(make_user(), "greeting", name="Ada")

    assert report.channel == "email"
    assert sms.calls == []


def test_retries_same_channel_until_it_succeeds(templates):
    sms = FakeSender(failures=2)
    service = NotificationService({"sms": sms}, templates, max_retries=2)

    report = service.notify(make_user(["sms"]), "greeting", name="Ada")

    assert report.delivered is True
    assert report.attempts == [("sms", False), ("sms", False), ("sms", True)]


def test_falls_back_to_next_channel_after_retries_are_exhausted(templates):
    service = NotificationService({"email": BrokenSender(), "sms": FakeSender()}, templates, max_retries=1)

    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")

    assert report.delivered is True
    assert report.channel == "sms"
    assert report.attempts == [("email", False), ("email", False), ("sms", True)]


def test_default_max_retries_allows_two_retries(templates):
    email = BrokenSender()
    service = NotificationService({"email": email}, templates)

    service.notify(make_user(), "greeting", name="Ada")

    assert email.calls == 3


def test_zero_max_retries_tries_each_channel_once(templates):
    service = NotificationService({"email": BrokenSender(), "push": BrokenSender()}, templates, max_retries=0)

    report = service.notify(make_user(["email", "push"]), "greeting", name="Ada")

    assert report.attempts == [("email", False), ("push", False)]


def test_stops_at_first_successful_send(templates):
    push = FakeSender()
    service = NotificationService({"sms": FakeSender(), "push": push}, templates)

    service.notify(make_user(["sms", "push"]), "greeting", name="Ada")

    assert push.calls == []


def test_reports_failure_when_every_channel_fails(templates):
    service = NotificationService({"email": BrokenSender(), "sms": BrokenSender()}, templates, max_retries=0)

    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == [("email", False), ("sms", False)]


def test_skips_channel_without_configured_sender(templates):
    service = NotificationService({"sms": FakeSender()}, templates)

    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")

    assert report.attempts == [("sms", True)]


def test_skips_channel_where_user_has_no_address(templates):
    email = FakeSender()
    service = NotificationService({"sms": FakeSender(), "email": email}, templates)
    user = User(id="u1", email="ada@example.com", preferred_channels=["sms", "email"])

    report = service.notify(user, "greeting", name="Ada")

    assert report.attempts == [("email", True)]


def test_skips_unknown_channel_even_with_a_sender(templates):
    fax = FakeSender()
    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)

    report = service.notify(make_user(["fax", "email"]), "greeting", name="Ada")

    assert report.attempts == [("email", True)]
    assert fax.calls == []


def test_no_reachable_channel_reports_failure_without_attempts(templates):
    service = NotificationService({}, templates)

    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == []


@pytest.mark.parametrize(
    ("template_name", "params", "error"),
    [
        ("unknown", {"name": "Ada"}, KeyError),
        ("greeting", {}, ValueError),
    ],
)
def test_template_errors_propagate_before_sending(templates, template_name, params, error):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(error):
        service.notify(make_user(), template_name, **params)

    assert email.calls == []


def test_errors_other_than_delivery_error_propagate(templates):
    class CrashingSender:
        def send(self, address: str, message: str) -> None:
            raise RuntimeError("sender bug")

    sms = FakeSender()
    service = NotificationService({"email": CrashingSender(), "sms": sms}, templates)

    with pytest.raises(RuntimeError, match="sender bug"):
        service.notify(make_user(["email", "sms"]), "greeting", name="Ada")

    assert sms.calls == []

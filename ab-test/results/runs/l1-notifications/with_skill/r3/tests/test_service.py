from typing import Any

import pytest
from fakes import CrashingSender, FakeSender

from notify import NotificationService, TemplateStore, User

EMAIL = "alice@example.com"
PHONE = "+390351234567"
PUSH_TOKEN = "token-1"


@pytest.fixture
def templates() -> TemplateStore:
    store = TemplateStore()
    store.add("welcome", "Hi {name}!")
    return store


def reachable_user(*preferred_channels: str) -> User:
    """A user with an address on every channel."""
    return User(
        "u1",
        email=EMAIL,
        phone=PHONE,
        push_token=PUSH_TOKEN,
        preferred_channels=list(preferred_channels),
    )


def test_rejects_negative_max_retries(templates: TemplateStore) -> None:
    with pytest.raises(ValueError, match="max_retries"):
        NotificationService({}, templates, max_retries=-1)


def test_delivers_on_the_first_preferred_channel(templates: TemplateStore) -> None:
    service = NotificationService(
        {"email": FakeSender(), "sms": FakeSender()}, templates
    )

    report = service.notify(reachable_user("sms", "email"), "welcome", name="Alice")

    assert report.delivered is True
    assert report.channel == "sms"
    assert report.attempts == [("sms", True)]


def test_sends_the_rendered_message_to_the_channel_address(
    templates: TemplateStore,
) -> None:
    sms = FakeSender()
    service = NotificationService({"sms": sms}, templates)

    service.notify(reachable_user("sms"), "welcome", name="Alice")

    assert sms.calls == [(PHONE, "Hi Alice!")]


def test_accepts_placeholders_named_like_its_own_parameters() -> None:
    store = TemplateStore()
    store.add("greeting", "{user} sent you {template_name}")
    email = FakeSender()
    service = NotificationService({"email": email}, store)

    service.notify(
        reachable_user("email"), "greeting", user="Bob", template_name="a card"
    )

    assert email.calls == [(EMAIL, "Bob sent you a card")]


def test_retries_a_failing_channel_until_it_succeeds(templates: TemplateStore) -> None:
    service = NotificationService(
        {"email": FakeSender(failures=2)}, templates, max_retries=2
    )

    report = service.notify(reachable_user("email"), "welcome", name="Alice")

    assert report.delivered is True
    assert report.attempts == [("email", False), ("email", False), ("email", True)]


def test_falls_back_to_the_next_channel_once_retries_run_out(
    templates: TemplateStore,
) -> None:
    senders = {"email": FakeSender.broken(), "push": FakeSender()}
    service = NotificationService(senders, templates, max_retries=1)

    report = service.notify(reachable_user("email", "push"), "welcome", name="Alice")

    assert report.channel == "push"
    assert report.attempts == [("email", False), ("email", False), ("push", True)]


def test_allows_two_retries_by_default(templates: TemplateStore) -> None:
    service = NotificationService({"email": FakeSender.broken()}, templates)

    report = service.notify(reachable_user("email"), "welcome", name="Alice")

    assert report.attempts == [("email", False)] * 3


def test_zero_retries_tries_each_channel_once(templates: TemplateStore) -> None:
    senders = {"email": FakeSender.broken(), "sms": FakeSender.broken()}
    service = NotificationService(senders, templates, max_retries=0)

    report = service.notify(reachable_user("email", "sms"), "welcome", name="Alice")

    assert report.attempts == [("email", False), ("sms", False)]


def test_stops_at_the_first_successful_send(templates: TemplateStore) -> None:
    sms = FakeSender()
    service = NotificationService(
        {"email": FakeSender(failures=1), "sms": sms}, templates
    )

    service.notify(reachable_user("email", "sms"), "welcome", name="Alice")

    assert sms.calls == []


def test_reports_failure_when_every_channel_fails(templates: TemplateStore) -> None:
    senders = {"email": FakeSender.broken(), "sms": FakeSender.broken()}
    service = NotificationService(senders, templates, max_retries=0)

    report = service.notify(reachable_user("email", "sms"), "welcome", name="Alice")

    assert report.delivered is False
    assert report.channel is None


def test_skips_a_channel_without_a_sender(templates: TemplateStore) -> None:
    service = NotificationService({"email": FakeSender()}, templates)

    report = service.notify(reachable_user("sms", "email"), "welcome", name="Alice")

    assert report.attempts == [("email", True)]


def test_skips_a_channel_the_user_has_no_address_for(templates: TemplateStore) -> None:
    sms = FakeSender()
    service = NotificationService({"sms": sms, "email": FakeSender()}, templates)
    user = User("u1", email=EMAIL, preferred_channels=["sms", "email"])

    report = service.notify(user, "welcome", name="Alice")

    assert report.attempts == [("email", True)]
    assert sms.calls == []


def test_skips_a_channel_with_an_unknown_name(templates: TemplateStore) -> None:
    fax = FakeSender()
    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)

    report = service.notify(reachable_user("fax", "email"), "welcome", name="Alice")

    assert report.attempts == [("email", True)]
    assert fax.calls == []


def test_reports_no_attempts_when_no_channel_is_usable(
    templates: TemplateStore,
) -> None:
    service = NotificationService({"email": FakeSender()}, templates)

    report = service.notify(User("u1"), "welcome", name="Alice")

    assert report.delivered is False
    assert report.attempts == []


@pytest.mark.parametrize(
    ("template_name", "params", "expected_error"),
    [("unknown", {"name": "Alice"}, KeyError), ("welcome", {}, ValueError)],
)
def test_raises_template_errors_before_sending(
    templates: TemplateStore,
    template_name: str,
    params: dict[str, Any],
    expected_error: type[Exception],
) -> None:
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(expected_error):
        service.notify(reachable_user("email"), template_name, **params)
    assert email.calls == []


def test_propagates_sender_errors_other_than_delivery_error(
    templates: TemplateStore,
) -> None:
    crashing = CrashingSender()
    service = NotificationService({"email": crashing, "sms": FakeSender()}, templates)

    with pytest.raises(RuntimeError, match="sender bug"):
        service.notify(reachable_user("email", "sms"), "welcome", name="Alice")
    assert crashing.calls == 1


def test_logs_why_a_delivery_attempt_failed(
    templates: TemplateStore, caplog: pytest.LogCaptureFixture
) -> None:
    service = NotificationService({"email": FakeSender(failures=1)}, templates)

    service.notify(reachable_user("email"), "welcome", name="Alice")

    assert "Delivery via email failed: simulated outage" in caplog.messages

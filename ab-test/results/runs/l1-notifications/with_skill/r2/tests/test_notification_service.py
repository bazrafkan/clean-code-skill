import logging
import math

import pytest

from notify import DeliveryError, NotificationService, TemplateStore, User

EMAIL = "alice@example.com"
PHONE = "+390351234567"
PUSH_TOKEN = "push-token-1"
NEVER_SUCCEEDS = math.inf


class FakeSender:
    """Records every send call and fails the first `failures` of them."""

    def __init__(self, failures: float = 0) -> None:
        self._failures_left = failures
        self.send_calls: list[tuple[str, str]] = []

    def send(self, address: str, message: str) -> None:
        self.send_calls.append((address, message))
        if self._failures_left > 0:
            self._failures_left -= 1
            raise DeliveryError(f"simulated outage on {address}")


class BuggySender:
    def __init__(self) -> None:
        self.send_calls = 0

    def send(self, address: str, message: str) -> None:
        self.send_calls += 1
        raise RuntimeError("bug in sender")


@pytest.fixture
def templates() -> TemplateStore:
    store = TemplateStore()
    store.add("welcome", "Hello {name}")
    return store


def user_preferring(*channels: str) -> User:
    return User(
        "alice",
        email=EMAIL,
        phone=PHONE,
        push_token=PUSH_TOKEN,
        preferred_channels=list(channels),
    )


def test_negative_max_retries_is_rejected(templates: TemplateStore) -> None:
    with pytest.raises(ValueError, match="max_retries"):
        NotificationService({}, templates, max_retries=-1)


def test_sends_rendered_message_to_users_address_on_first_preferred_channel(
    templates: TemplateStore,
) -> None:
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    service.notify(user_preferring("email"), "welcome", name="Alice")

    assert email.send_calls == [(EMAIL, "Hello Alice")]


def test_successful_first_send_is_reported(templates: TemplateStore) -> None:
    service = NotificationService({"email": FakeSender()}, templates)

    report = service.notify(user_preferring("email"), "welcome", name="Alice")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", True)]


def test_later_channels_are_not_used_after_a_success(templates: TemplateStore) -> None:
    sms = FakeSender()
    service = NotificationService({"email": FakeSender(), "sms": sms}, templates)

    service.notify(user_preferring("email", "sms"), "welcome", name="Alice")

    assert sms.send_calls == []


def test_failed_channel_is_retried_until_it_succeeds(templates: TemplateStore) -> None:
    service = NotificationService(
        {"email": FakeSender(failures=1)}, templates, max_retries=2
    )

    report = service.notify(user_preferring("email"), "welcome", name="Alice")

    assert report.delivered is True
    assert report.attempts == [("email", False), ("email", True)]


def test_falls_back_to_next_channel_once_retries_are_exhausted(
    templates: TemplateStore,
) -> None:
    sms = FakeSender()
    service = NotificationService(
        {"email": FakeSender(failures=NEVER_SUCCEEDS), "sms": sms},
        templates,
        max_retries=2,
    )

    report = service.notify(user_preferring("email", "sms"), "welcome", name="Alice")

    assert report.channel == "sms"
    assert report.attempts == [
        ("email", False),
        ("email", False),
        ("email", False),
        ("sms", True),
    ]
    assert sms.send_calls == [(PHONE, "Hello Alice")]


def test_default_max_retries_is_two(templates: TemplateStore) -> None:
    email = FakeSender(failures=NEVER_SUCCEEDS)
    service = NotificationService({"email": email}, templates)

    service.notify(user_preferring("email"), "welcome", name="Alice")

    assert len(email.send_calls) == 3


def test_zero_max_retries_falls_back_after_a_single_attempt(
    templates: TemplateStore,
) -> None:
    service = NotificationService(
        {"email": FakeSender(failures=1), "push": FakeSender()},
        templates,
        max_retries=0,
    )

    report = service.notify(user_preferring("email", "push"), "welcome", name="Alice")

    assert report.channel == "push"
    assert report.attempts == [("email", False), ("push", True)]


def test_undelivered_report_when_every_channel_fails(templates: TemplateStore) -> None:
    service = NotificationService(
        {
            "email": FakeSender(failures=NEVER_SUCCEEDS),
            "sms": FakeSender(failures=NEVER_SUCCEEDS),
        },
        templates,
        max_retries=1,
    )

    report = service.notify(user_preferring("email", "sms"), "welcome", name="Alice")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == [
        ("email", False),
        ("email", False),
        ("sms", False),
        ("sms", False),
    ]


def test_channel_without_configured_sender_is_skipped_without_attempt(
    templates: TemplateStore,
) -> None:
    service = NotificationService({"email": FakeSender()}, templates)

    report = service.notify(user_preferring("sms", "email"), "welcome", name="Alice")

    assert report.attempts == [("email", True)]


def test_channel_the_user_has_no_address_for_is_skipped_without_attempt(
    templates: TemplateStore,
) -> None:
    sms = FakeSender()
    service = NotificationService({"sms": sms, "email": FakeSender()}, templates)
    user_without_phone = User("bob", email=EMAIL, preferred_channels=["sms", "email"])

    report = service.notify(user_without_phone, "welcome", name="Bob")

    assert report.attempts == [("email", True)]
    assert sms.send_calls == []


def test_unknown_channel_is_skipped_even_with_a_sender_for_it(
    templates: TemplateStore,
) -> None:
    fax = FakeSender()
    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)

    report = service.notify(user_preferring("fax", "email"), "welcome", name="Alice")

    assert report.attempts == [("email", True)]
    assert fax.send_calls == []


def test_undelivered_report_without_attempts_when_no_channel_is_usable(
    templates: TemplateStore,
) -> None:
    service = NotificationService({}, templates)

    report = service.notify(user_preferring("email", "sms"), "welcome", name="Alice")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == []


@pytest.mark.parametrize(
    ("template_name", "params", "expected_error"),
    [("missing", {"name": "Alice"}, KeyError), ("welcome", {}, ValueError)],
)
def test_template_errors_propagate_before_anything_is_sent(
    templates: TemplateStore,
    template_name: str,
    params: dict[str, object],
    expected_error: type[Exception],
) -> None:
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(expected_error):
        service.notify(user_preferring("email"), template_name, **params)

    assert email.send_calls == []


def test_errors_other_than_delivery_error_propagate_without_retry(
    templates: TemplateStore,
) -> None:
    buggy = BuggySender()
    service = NotificationService({"email": buggy}, templates, max_retries=2)

    with pytest.raises(RuntimeError, match="bug in sender"):
        service.notify(user_preferring("email"), "welcome", name="Alice")

    assert buggy.send_calls == 1


def test_template_may_use_a_placeholder_called_user(
    templates: TemplateStore,
) -> None:
    templates.add("greeting", "Hi {user}")
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    service.notify(user_preferring("email"), "greeting", user="Alice")

    assert email.send_calls == [(EMAIL, "Hi Alice")]


def test_failed_attempt_is_logged_with_channel_and_cause(
    templates: TemplateStore, caplog: pytest.LogCaptureFixture
) -> None:
    service = NotificationService({"email": FakeSender(failures=1)}, templates)

    with caplog.at_level(logging.WARNING, logger="notify"):
        service.notify(user_preferring("email"), "welcome", name="Alice")

    assert "email" in caplog.text
    assert "simulated outage" in caplog.text

import logging
import sys

import pytest

from notify import (
    DeliveryError,
    DeliveryReport,
    NotificationService,
    TemplateStore,
    User,
)

EMAIL = "ada@example.com"
PHONE = "+39 035 123 4567"
PUSH_TOKEN = "push-token-ada"
MESSAGE = "Your code is 1234"


class FakeSender:
    """Records every send and fails the first ``failures`` of them."""

    def __init__(self, failures: int = 0) -> None:
        self.calls: list[tuple[str, str]] = []
        self._failures_left = failures

    def send(self, address: str, message: str) -> None:
        self.calls.append((address, message))
        if self._failures_left > 0:
            self._failures_left -= 1
            raise DeliveryError("simulated outage")


def broken_sender() -> FakeSender:
    return FakeSender(failures=sys.maxsize)


class CrashingSender:
    """Fails with a bug rather than a delivery failure."""

    def __init__(self) -> None:
        self.call_count = 0

    def send(self, address: str, message: str) -> None:
        self.call_count += 1
        raise RuntimeError("sender bug")


@pytest.fixture
def templates() -> TemplateStore:
    store = TemplateStore()
    store.add("code", "Your code is {code}")
    return store


def reachable_user(*preferred_channels: str) -> User:
    return User(
        "ada",
        email=EMAIL,
        phone=PHONE,
        push_token=PUSH_TOKEN,
        preferred_channels=list(preferred_channels),
    )


def send_code(service: NotificationService, user: User) -> DeliveryReport:
    return service.notify(user, "code", code="1234")


def test_negative_max_retries_is_rejected(templates: TemplateStore) -> None:
    with pytest.raises(ValueError, match="max_retries"):
        NotificationService({}, templates, max_retries=-1)


class TestTemplateErrors:
    def test_unknown_template_raises_before_sending(
        self, templates: TemplateStore
    ) -> None:
        sender = FakeSender()
        service = NotificationService({"email": sender}, templates)

        with pytest.raises(KeyError):
            service.notify(reachable_user("email"), "missing")

        assert sender.calls == []

    def test_missing_parameter_raises_before_sending(
        self, templates: TemplateStore
    ) -> None:
        sender = FakeSender()
        service = NotificationService({"email": sender}, templates)

        with pytest.raises(ValueError):
            service.notify(reachable_user("email"), "code")

        assert sender.calls == []


class TestDelivery:
    @pytest.mark.parametrize(
        ("channel", "address"),
        [("email", EMAIL), ("sms", PHONE), ("push", PUSH_TOKEN)],
    )
    def test_sends_rendered_message_to_the_channel_address(
        self, templates: TemplateStore, channel: str, address: str
    ) -> None:
        sender = FakeSender()
        service = NotificationService({channel: sender}, templates)

        send_code(service, reachable_user(channel))

        assert sender.calls == [(address, MESSAGE)]

    def test_accepts_template_parameters_named_like_notify_arguments(
        self, templates: TemplateStore
    ) -> None:
        templates.add("signed", "{template_name} for {user}")
        sender = FakeSender()
        service = NotificationService({"email": sender}, templates)

        service.notify(
            reachable_user("email"), "signed", user="Ada", template_name="Invite"
        )

        assert sender.calls == [(EMAIL, "Invite for Ada")]

    def test_reports_delivery_on_first_preferred_channel(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"email": FakeSender(), "sms": FakeSender()}, templates
        )

        report = send_code(service, reachable_user("sms", "email"))

        assert report == DeliveryReport(
            delivered=True, channel="sms", attempts=[("sms", True)]
        )

    def test_uses_email_when_user_states_no_preference(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"email": FakeSender(), "sms": FakeSender()}, templates
        )

        report = send_code(service, User("ada", email=EMAIL, phone=PHONE))

        assert report.channel == "email"

    def test_does_not_use_later_channels_after_a_success(
        self, templates: TemplateStore
    ) -> None:
        sms = FakeSender()
        service = NotificationService(
            {"email": FakeSender(failures=1), "sms": sms}, templates
        )

        send_code(service, reachable_user("email", "sms"))

        assert sms.calls == []


class TestRetriesAndFallback:
    def test_retries_a_failing_channel_until_it_succeeds(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"sms": FakeSender(failures=2)}, templates, max_retries=2
        )

        report = send_code(service, reachable_user("sms"))

        assert report == DeliveryReport(
            delivered=True,
            channel="sms",
            attempts=[("sms", False), ("sms", False), ("sms", True)],
        )

    def test_falls_back_to_next_channel_when_retries_are_exhausted(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"email": broken_sender(), "sms": FakeSender()}, templates, max_retries=1
        )

        report = send_code(service, reachable_user("email", "sms"))

        assert report == DeliveryReport(
            delivered=True,
            channel="sms",
            attempts=[("email", False), ("email", False), ("sms", True)],
        )

    def test_zero_max_retries_means_one_attempt_per_channel(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"email": broken_sender(), "sms": FakeSender()}, templates, max_retries=0
        )

        report = send_code(service, reachable_user("email", "sms"))

        assert report.attempts == [("email", False), ("sms", True)]

    def test_default_max_retries_is_two(self, templates: TemplateStore) -> None:
        sender = broken_sender()
        service = NotificationService({"email": sender}, templates)

        send_code(service, reachable_user("email"))

        assert len(sender.calls) == 3

    def test_reports_failure_when_every_channel_fails(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"email": broken_sender(), "push": broken_sender()},
            templates,
            max_retries=1,
        )

        report = send_code(service, reachable_user("email", "push"))

        assert report == DeliveryReport(
            delivered=False,
            channel=None,
            attempts=[
                ("email", False),
                ("email", False),
                ("push", False),
                ("push", False),
            ],
        )

    def test_logs_why_an_attempt_failed(
        self, templates: TemplateStore, caplog: pytest.LogCaptureFixture
    ) -> None:
        service = NotificationService({"email": FakeSender(failures=1)}, templates)

        with caplog.at_level(logging.WARNING, logger="notify"):
            send_code(service, reachable_user("email"))

        assert "simulated outage" in caplog.text

    def test_other_sender_errors_propagate_without_retry(
        self, templates: TemplateStore
    ) -> None:
        sender = CrashingSender()
        service = NotificationService({"email": sender, "sms": FakeSender()}, templates)

        with pytest.raises(RuntimeError):
            send_code(service, reachable_user("email", "sms"))

        assert sender.call_count == 1


class TestSkippedChannels:
    def test_skips_channel_without_a_sender(self, templates: TemplateStore) -> None:
        service = NotificationService({"sms": FakeSender()}, templates)

        report = send_code(service, reachable_user("email", "sms"))

        assert report.attempts == [("sms", True)]

    def test_skips_channel_the_user_has_no_address_for(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"email": FakeSender(), "sms": FakeSender()}, templates
        )
        user = User("ada", phone=PHONE, preferred_channels=["email", "sms"])

        report = send_code(service, user)

        assert report.attempts == [("sms", True)]

    def test_skips_unknown_channel_even_when_it_has_a_sender(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService(
            {"fax": FakeSender(), "sms": FakeSender()}, templates
        )

        report = send_code(service, reachable_user("fax", "sms"))

        assert report.attempts == [("sms", True)]

    def test_reports_nothing_delivered_when_no_channel_is_reachable(
        self, templates: TemplateStore
    ) -> None:
        service = NotificationService({"email": FakeSender()}, templates)

        report = send_code(service, User("ada", phone=PHONE))

        assert report == DeliveryReport(delivered=False, channel=None, attempts=[])

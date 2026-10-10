import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User

EMAIL = "ann@example.com"
PHONE = "+390000000"
PUSH_TOKEN = "device-1"


class FakeSender:
    """Records every send and raises DeliveryError on the first `failures` of them."""

    def __init__(self, failures: int = 0) -> None:
        self.sent: list[tuple[str, str]] = []
        self._failures_left = failures

    def send(self, address: str, message: str) -> None:
        self.sent.append((address, message))
        if self._failures_left > 0:
            self._failures_left -= 1
            raise DeliveryError(f"simulated failure sending to {address}")


class FailingSender:
    """Records every send and raises `error` on each of them."""

    def __init__(self, error: Exception) -> None:
        self.sent: list[tuple[str, str]] = []
        self._error = error

    def send(self, address: str, message: str) -> None:
        self.sent.append((address, message))
        raise self._error


def make_templates() -> TemplateStore:
    templates = TemplateStore()
    templates.add("welcome", "Hello {name}")
    return templates


def reachable_user(*channels: str) -> User:
    return User("u1", email=EMAIL, phone=PHONE, push_token=PUSH_TOKEN, preferred_channels=list(channels))


def unavailable() -> FailingSender:
    return FailingSender(DeliveryError("provider unavailable"))


def test_rejects_negative_max_retries():
    with pytest.raises(ValueError):
        NotificationService({}, make_templates(), max_retries=-1)


def test_sends_rendered_message_to_first_preferred_channel():
    email = FakeSender()
    service = NotificationService({"email": email}, make_templates())

    report = service.notify(reachable_user("email"), "welcome", name="Ann")

    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
    assert email.sent == [(EMAIL, "Hello Ann")]


def test_retries_same_channel_after_delivery_error():
    email = FakeSender(failures=2)
    service = NotificationService({"email": email}, make_templates(), max_retries=2)

    report = service.notify(reachable_user("email"), "welcome", name="Ann")

    assert report == DeliveryReport(
        delivered=True,
        channel="email",
        attempts=[("email", False), ("email", False), ("email", True)],
    )


def test_falls_back_to_next_channel_after_two_retries_by_default():
    email, sms = unavailable(), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, make_templates())

    report = service.notify(reachable_user("email", "sms"), "welcome", name="Ann")

    assert report == DeliveryReport(
        delivered=True,
        channel="sms",
        attempts=[("email", False), ("email", False), ("email", False), ("sms", True)],
    )
    assert sms.sent == [(PHONE, "Hello Ann")]


def test_zero_retries_tries_each_channel_once():
    service = NotificationService({"email": unavailable(), "sms": FakeSender()}, make_templates(), max_retries=0)

    report = service.notify(reachable_user("email", "sms"), "welcome", name="Ann")

    assert report.attempts == [("email", False), ("sms", True)]


def test_stops_at_first_successful_send():
    email, push = FakeSender(), FakeSender()
    service = NotificationService({"email": email, "push": push}, make_templates())

    service.notify(reachable_user("email", "push"), "welcome", name="Ann")

    assert push.sent == []


def test_reports_failure_when_every_channel_fails():
    service = NotificationService({"email": unavailable(), "push": unavailable()}, make_templates(), max_retries=1)

    report = service.notify(reachable_user("email", "push"), "welcome", name="Ann")

    assert report == DeliveryReport(
        delivered=False,
        channel=None,
        attempts=[("email", False), ("email", False), ("push", False), ("push", False)],
    )


def test_skips_channel_without_sender():
    service = NotificationService({"push": FakeSender()}, make_templates())

    report = service.notify(reachable_user("sms", "push"), "welcome", name="Ann")

    assert report == DeliveryReport(delivered=True, channel="push", attempts=[("push", True)])


def test_skips_channel_the_user_has_no_address_for():
    sms, push = FakeSender(), FakeSender()
    service = NotificationService({"sms": sms, "push": push}, make_templates())
    user = User("u1", push_token=PUSH_TOKEN, preferred_channels=["sms", "push"])

    report = service.notify(user, "welcome", name="Ann")

    assert report == DeliveryReport(delivered=True, channel="push", attempts=[("push", True)])
    assert sms.sent == []


def test_skips_unknown_channel_even_when_it_has_a_sender():
    fax = FakeSender()
    service = NotificationService({"fax": fax, "email": FakeSender()}, make_templates())

    report = service.notify(reachable_user("fax", "email"), "welcome", name="Ann")

    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
    assert fax.sent == []


def test_reports_no_attempts_when_no_channel_is_usable():
    service = NotificationService({"email": FakeSender()}, make_templates())

    report = service.notify(User("u1", phone=PHONE, preferred_channels=["email", "sms"]), "welcome", name="Ann")

    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])


@pytest.mark.parametrize(
    "template_name, params, error",
    [("missing", {"name": "Ann"}, KeyError), ("welcome", {}, ValueError)],
)
def test_template_errors_propagate_before_anything_is_sent(template_name, params, error):
    email = FakeSender()
    service = NotificationService({"email": email}, make_templates())

    with pytest.raises(error):
        service.notify(reachable_user("email"), template_name, **params)

    assert email.sent == []


def test_errors_other_than_delivery_error_propagate_without_retry_or_fallback():
    email, sms = FailingSender(RuntimeError("sender bug")), FakeSender()
    service = NotificationService({"email": email, "sms": sms}, make_templates())

    with pytest.raises(RuntimeError, match="sender bug"):
        service.notify(reachable_user("email", "sms"), "welcome", name="Ann")

    assert len(email.sent) == 1
    assert sms.sent == []


def test_template_parameters_may_share_names_with_notify_arguments():
    email = FakeSender()
    templates = TemplateStore()
    templates.add("digest", "{user} has {template_name}")
    service = NotificationService({"email": email}, templates)

    service.notify(reachable_user("email"), "digest", user="Ann", template_name="news")

    assert email.sent == [(EMAIL, "Ann has news")]

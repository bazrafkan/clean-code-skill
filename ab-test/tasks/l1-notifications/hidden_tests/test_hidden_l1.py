import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class FakeSender:
    def __init__(self, failures=0, error=None):
        self.failures = failures
        self.error = error
        self.calls = []

    def send(self, address, message):
        self.calls.append((address, message))
        if self.error is not None:
            raise self.error
        if self.failures > 0:
            self.failures -= 1
            raise DeliveryError("temporary failure")


def make_templates():
    store = TemplateStore()
    store.add("welcome", "Hello {who}, welcome to {app}!")
    store.add("plain", "Ping")
    return store


def make_user(**overrides):
    data = dict(id="u1", email="a@x.io", phone="+391234", push_token="tok", preferred_channels=["push", "sms", "email"])
    data.update(overrides)
    return User(**data)


def test_template_render():
    assert make_templates().render("welcome", who="Ada", app="Shop") == "Hello Ada, welcome to Shop!"


def test_unknown_template_raises_key_error():
    with pytest.raises(KeyError):
        make_templates().render("nope")


def test_missing_param_raises_value_error():
    with pytest.raises(ValueError):
        make_templates().render("welcome", who="Ada")


def test_default_preferred_channels_is_email():
    assert list(User(id="u2", email="b@x.io").preferred_channels) == ["email"]


def test_first_channel_success():
    push, sms, email = FakeSender(), FakeSender(), FakeSender()
    service = NotificationService({"push": push, "sms": sms, "email": email}, make_templates())
    report = service.notify(make_user(), "welcome", who="Ada", app="Shop")
    assert isinstance(report, DeliveryReport)
    assert report.delivered is True
    assert report.channel == "push"
    assert list(report.attempts) == [("push", True)]
    assert push.calls == [("tok", "Hello Ada, welcome to Shop!")]
    assert sms.calls == [] and email.calls == []


def test_retries_then_succeeds_on_same_channel():
    push = FakeSender(failures=2)
    service = NotificationService({"push": push}, make_templates(), max_retries=2)
    report = service.notify(make_user(), "plain")
    assert report.delivered and report.channel == "push"
    assert list(report.attempts) == [("push", False), ("push", False), ("push", True)]


def test_falls_back_after_retries_exhausted():
    push = FakeSender(failures=10)
    sms = FakeSender()
    service = NotificationService({"push": push, "sms": sms}, make_templates(), max_retries=1)
    report = service.notify(make_user(), "plain")
    assert report.delivered and report.channel == "sms"
    assert list(report.attempts) == [("push", False), ("push", False), ("sms", True)]
    assert sms.calls == [("+391234", "Ping")]


def test_zero_retries():
    push = FakeSender(failures=1)
    email = FakeSender()
    service = NotificationService({"push": push, "email": email}, make_templates(), max_retries=0)
    report = service.notify(make_user(preferred_channels=["push", "email"]), "plain")
    assert list(report.attempts) == [("push", False), ("email", True)]


def test_skips_channels_without_sender_or_address_or_unknown():
    email = FakeSender()
    service = NotificationService({"email": email, "sms": FakeSender()}, make_templates())
    user = make_user(phone=None, preferred_channels=["fax", "push", "sms", "email"])
    report = service.notify(user, "plain")
    assert report.channel == "email"
    assert list(report.attempts) == [("email", True)]


def test_all_channels_fail():
    service = NotificationService({"push": FakeSender(failures=99), "email": FakeSender(failures=99)}, make_templates(), max_retries=1)
    report = service.notify(make_user(preferred_channels=["push", "email"]), "plain")
    assert report.delivered is False
    assert report.channel is None
    assert list(report.attempts) == [("push", False), ("push", False), ("email", False), ("email", False)]


def test_no_usable_channel():
    service = NotificationService({}, make_templates())
    report = service.notify(make_user(), "plain")
    assert report.delivered is False and report.channel is None and list(report.attempts) == []


def test_template_error_before_sending():
    push = FakeSender()
    service = NotificationService({"push": push}, make_templates())
    with pytest.raises(ValueError):
        service.notify(make_user(), "welcome", who="Ada")
    with pytest.raises(KeyError):
        service.notify(make_user(), "missing")
    assert push.calls == []


def test_other_exceptions_propagate():
    service = NotificationService({"push": FakeSender(error=RuntimeError("boom"))}, make_templates())
    with pytest.raises(RuntimeError):
        service.notify(make_user(), "plain")


def test_negative_max_retries():
    with pytest.raises(ValueError):
        NotificationService({}, make_templates(), max_retries=-1)


def test_delivery_error_is_exception():
    assert issubclass(DeliveryError, Exception)

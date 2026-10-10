import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class FakeSender:
    """Records every send and fails the first ``failures`` of them."""

    def __init__(self, failures=0, error=None):
        self.failures = failures
        self.error = error
        self.calls = []

    def send(self, address, message):
        self.calls.append((address, message))
        if self.error is not None:
            raise self.error
        if len(self.calls) <= self.failures:
            raise DeliveryError("temporary failure")


ALWAYS_FAILS = 10**6


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("welcome", "Hello {name}!")
    return store


def full_user(channels):
    return User(
        id=1,
        email="a@example.com",
        phone="+391234",
        push_token="tok",
        preferred_channels=channels,
    )


# --- User -------------------------------------------------------------------


def test_user_defaults_to_email_channel():
    assert User(id=1).preferred_channels == ["email"]


def test_user_default_channels_are_not_shared_between_instances():
    first = User(id=1)
    first.preferred_channels.append("sms")
    assert User(id=2).preferred_channels == ["email"]


def test_user_copies_given_channel_list():
    channels = ["sms"]
    user = User(id=1, preferred_channels=channels)
    channels.append("push")
    assert user.preferred_channels == ["sms"]


def test_user_address_for_maps_channels_to_fields():
    user = full_user(["email"])
    assert user.address_for("email") == "a@example.com"
    assert user.address_for("sms") == "+391234"
    assert user.address_for("push") == "tok"
    assert user.address_for("fax") is None


# --- TemplateStore ----------------------------------------------------------


def test_render_fills_placeholders(templates):
    assert templates.render("welcome", name="Ana") == "Hello Ana!"


def test_render_unknown_template_raises_key_error(templates):
    with pytest.raises(KeyError):
        templates.render("nope")


def test_render_missing_parameter_raises_value_error(templates):
    with pytest.raises(ValueError):
        templates.render("welcome")


def test_render_missing_positional_placeholder_raises_value_error():
    store = TemplateStore()
    store.add("pos", "Hi {0}")
    with pytest.raises(ValueError):
        store.render("pos")


def test_add_replaces_existing_template(templates):
    templates.add("welcome", "Hi {name}")
    assert templates.render("welcome", name="Bo") == "Hi Bo"


# --- NotificationService: construction --------------------------------------


def test_negative_max_retries_raises(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_zero_max_retries_is_allowed(templates):
    NotificationService({}, templates, max_retries=0)


# --- NotificationService: notify --------------------------------------------


def test_delivers_on_first_preferred_channel(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(full_user(["email"]), "welcome", name="Ana")

    assert report == DeliveryReport(True, "email", [("email", True)])
    assert email.calls == [("a@example.com", "Hello Ana!")]


def test_template_errors_propagate_before_sending(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    with pytest.raises(KeyError):
        service.notify(full_user(["email"]), "missing")
    with pytest.raises(ValueError):
        service.notify(full_user(["email"]), "welcome")
    assert email.calls == []


def test_retries_same_channel_then_succeeds(templates):
    email = FakeSender(failures=2)
    service = NotificationService({"email": email}, templates, max_retries=2)

    report = service.notify(full_user(["email"]), "welcome", name="Ana")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", False), ("email", False), ("email", True)]


def test_falls_back_after_exhausting_retries(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)

    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ana")

    assert report.channel == "sms"
    assert report.attempts == [("email", False), ("email", False), ("sms", True)]
    assert sms.calls == [("+391234", "Hello Ana!")]


def test_zero_retries_means_one_attempt_per_channel(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    push = FakeSender()
    service = NotificationService({"email": email, "push": push}, templates, max_retries=0)

    report = service.notify(full_user(["email", "push"]), "welcome", name="Ana")

    assert report.attempts == [("email", False), ("push", True)]


def test_all_channels_fail(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    sms = FakeSender(failures=ALWAYS_FAILS)
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)

    report = service.notify(full_user(["sms", "email"]), "welcome", name="Ana")

    assert report == DeliveryReport(
        False,
        None,
        [("sms", False), ("sms", False), ("email", False), ("email", False)],
    )


def test_stops_at_first_success(templates):
    email = FakeSender()
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    service.notify(full_user(["email", "sms"]), "welcome", name="Ana")

    assert sms.calls == []


def test_skips_channel_without_sender(templates):
    sms = FakeSender()
    service = NotificationService({"sms": sms}, templates)

    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ana")

    assert report.attempts == [("sms", True)]


def test_skips_channel_without_user_address(templates):
    email = FakeSender()
    push = FakeSender()
    service = NotificationService({"email": email, "push": push}, templates)
    user = User(id=1, push_token="tok", preferred_channels=["email", "push"])

    report = service.notify(user, "welcome", name="Ana")

    assert report.attempts == [("push", True)]
    assert email.calls == []


def test_skips_unknown_channel_even_with_sender(templates):
    fax = FakeSender()
    email = FakeSender()
    service = NotificationService({"fax": fax, "email": email}, templates)

    report = service.notify(full_user(["fax", "email"]), "welcome", name="Ana")

    assert report.attempts == [("email", True)]
    assert fax.calls == []


def test_nothing_usable_returns_undelivered_with_no_attempts(templates):
    service = NotificationService({}, templates)

    report = service.notify(User(id=1), "welcome", name="Ana")

    assert report == DeliveryReport(False, None, [])


def test_non_delivery_errors_propagate(templates):
    email = FakeSender(error=RuntimeError("bug"))
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    with pytest.raises(RuntimeError):
        service.notify(full_user(["email", "sms"]), "welcome", name="Ana")
    assert len(email.calls) == 1
    assert sms.calls == []


def test_delivery_error_subclasses_are_retried(templates):
    class Timeout(DeliveryError):
        pass

    email = FakeSender(error=Timeout())
    service = NotificationService({"email": email}, templates, max_retries=1)

    report = service.notify(full_user(["email"]), "welcome", name="Ana")

    assert report.attempts == [("email", False), ("email", False)]


def test_template_params_may_use_reserved_argument_names():
    store = TemplateStore()
    store.add("t", "{user} {template_name} {name}")
    email = FakeSender()
    service = NotificationService({"email": email}, store)

    service.notify(full_user(["email"]), "t", user="u", template_name="n", name="x")

    assert email.calls == [("a@example.com", "u n x")]

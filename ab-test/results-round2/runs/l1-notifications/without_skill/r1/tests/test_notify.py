import pytest

from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User


class FakeSender:
    """Fails the first `failures` sends with DeliveryError, then succeeds."""

    def __init__(self, failures=0, error=None):
        self.failures = failures
        self.error = error
        self.sent = []

    def send(self, address, message):
        self.sent.append((address, message))
        if self.error is not None:
            raise self.error
        if len(self.sent) <= self.failures:
            raise DeliveryError("boom")


ALWAYS_FAILS = 10**6


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("welcome", "Hi {name}!")
    return store


def full_user(channels):
    return User(
        id="u1",
        email="a@example.com",
        phone="+391234",
        push_token="tok",
        preferred_channels=channels,
    )


# --- User -------------------------------------------------------------------


def test_user_defaults_to_email_channel():
    assert User(id="u1").preferred_channels == ["email"]


def test_user_copies_preferred_channels():
    channels = ["sms"]
    user = User(id="u1", preferred_channels=channels)
    channels.append("push")
    assert user.preferred_channels == ["sms"]


def test_explicit_empty_channels_stay_empty():
    assert User(id="u1", preferred_channels=[]).preferred_channels == []


# --- TemplateStore ------------------------------------------------------------


def test_render_fills_placeholders(templates):
    assert templates.render("welcome", name="Ada") == "Hi Ada!"


def test_render_unknown_template_raises_key_error(templates):
    with pytest.raises(KeyError):
        templates.render("nope")


def test_render_missing_param_raises_value_error(templates):
    with pytest.raises(ValueError, match="name"):
        templates.render("welcome")


def test_render_missing_param_is_not_a_key_error(templates):
    with pytest.raises(ValueError) as info:
        templates.render("welcome")
    assert not isinstance(info.value, KeyError)


def test_add_replaces_existing_template(templates):
    templates.add("welcome", "Hello {name}")
    assert templates.render("welcome", name="Ada") == "Hello Ada"


# --- NotificationService construction -------------------------------------------


def test_negative_max_retries_rejected(templates):
    with pytest.raises(ValueError):
        NotificationService({}, templates, max_retries=-1)


def test_zero_max_retries_allowed(templates):
    NotificationService({}, templates, max_retries=0)


# --- notify -----------------------------------------------------------------------


def test_delivers_on_first_channel(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(User(id="u1", email="a@example.com"), "welcome", name="Ada")

    assert report == DeliveryReport(True, "email", [("email", True)])
    assert email.sent == [("a@example.com", "Hi Ada!")]


def test_retries_same_channel_then_succeeds(templates):
    email = FakeSender(failures=2)
    service = NotificationService({"email": email}, templates, max_retries=2)

    report = service.notify(full_user(["email"]), "welcome", name="Ada")

    assert report.delivered is True
    assert report.channel == "email"
    assert report.attempts == [("email", False), ("email", False), ("email", True)]


def test_falls_back_after_retries_exhausted(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)

    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ada")

    assert report.channel == "sms"
    assert report.attempts == [("email", False), ("email", False), ("sms", True)]
    assert sms.sent == [("+391234", "Hi Ada!")]


def test_zero_retries_means_single_attempt_per_channel(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    push = FakeSender(failures=ALWAYS_FAILS)
    service = NotificationService({"email": email, "push": push}, templates, max_retries=0)

    report = service.notify(full_user(["email", "push"]), "welcome", name="Ada")

    assert report == DeliveryReport(False, None, [("email", False), ("push", False)])


def test_all_channels_fail(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    service = NotificationService({"email": email}, templates)

    report = service.notify(full_user(["email"]), "welcome", name="Ada")

    assert report.delivered is False
    assert report.channel is None
    assert report.attempts == [("email", False)] * 3


def test_stops_at_first_success(templates):
    email = FakeSender()
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    service.notify(full_user(["email", "sms"]), "welcome", name="Ada")

    assert sms.sent == []


def test_follows_preferred_order(templates):
    email = FakeSender()
    push = FakeSender()
    service = NotificationService({"email": email, "push": push}, templates)

    report = service.notify(full_user(["push", "email"]), "welcome", name="Ada")

    assert report.channel == "push"
    assert push.sent == [("tok", "Hi Ada!")]
    assert email.sent == []


@pytest.mark.parametrize(
    "senders_keys, user_kwargs, channels",
    [
        # no sender configured for sms
        (["email"], {"phone": "+391234"}, ["sms", "email"]),
        # user has no phone number
        (["sms", "email"], {}, ["sms", "email"]),
        # unknown channel name, even with a sender registered under it
        (["fax", "email"], {}, ["fax", "email"]),
    ],
)
def test_unusable_channels_are_skipped_without_attempt(
    templates, senders_keys, user_kwargs, channels
):
    senders = {name: FakeSender() for name in senders_keys}
    user = User(id="u1", email="a@example.com", preferred_channels=channels, **user_kwargs)
    service = NotificationService(senders, templates)

    report = service.notify(user, "welcome", name="Ada")

    assert report == DeliveryReport(True, "email", [("email", True)])
    for name, sender in senders.items():
        if name != "email":
            assert sender.sent == []


def test_empty_address_counts_as_missing(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)

    report = service.notify(User(id="u1", email=""), "welcome", name="Ada")

    assert report == DeliveryReport(False, None, [])
    assert email.sent == []


def test_no_usable_channel_gives_empty_report(templates):
    service = NotificationService({}, templates)

    report = service.notify(full_user(["email", "sms", "push"]), "welcome", name="Ada")

    assert report == DeliveryReport(False, None, [])


def test_repeated_channel_is_not_retried_again(templates):
    email = FakeSender(failures=ALWAYS_FAILS)
    service = NotificationService({"email": email}, templates, max_retries=1)

    report = service.notify(full_user(["email", "email"]), "welcome", name="Ada")

    assert report.attempts == [("email", False), ("email", False)]


def test_template_errors_raised_before_sending(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)
    user = full_user(["email"])

    with pytest.raises(KeyError):
        service.notify(user, "missing-template")
    with pytest.raises(ValueError):
        service.notify(user, "welcome")
    assert email.sent == []


def test_other_exceptions_propagate_without_retry(templates):
    email = FakeSender(error=RuntimeError("bug"))
    sms = FakeSender()
    service = NotificationService({"email": email, "sms": sms}, templates)

    with pytest.raises(RuntimeError):
        service.notify(full_user(["email", "sms"]), "welcome", name="Ada")
    assert len(email.sent) == 1
    assert sms.sent == []


def test_delivery_error_subclass_is_retried(templates):
    class Timeout(DeliveryError):
        pass

    email = FakeSender(error=Timeout("slow"))
    service = NotificationService({"email": email}, templates, max_retries=1)

    report = service.notify(full_user(["email"]), "welcome", name="Ada")

    assert report.attempts == [("email", False), ("email", False)]


def test_placeholders_may_share_names_with_method_parameters():
    store = TemplateStore()
    store.add("t", "{name}/{user}/{template_name}")
    email = FakeSender()
    service = NotificationService({"email": email}, store)

    service.notify(full_user(["email"]), "t", name="n", user="u", template_name="tn")

    assert email.sent == [("a@example.com", "n/u/tn")]


def test_each_call_gets_a_fresh_report(templates):
    email = FakeSender()
    service = NotificationService({"email": email}, templates)
    user = full_user(["email"])

    first = service.notify(user, "welcome", name="Ada")
    second = service.notify(user, "welcome", name="Bob")

    assert first.attempts == [("email", True)]
    assert second.attempts == [("email", True)]
    assert first.attempts is not second.attempts

You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{"pairs": [{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}, ...]}

Read only this packet file. Do not look at any other file or directory, and do not write any files.


## Task given to both developers

Build a `notify` package that sends a message to a user through their preferred channels, with retries and fallback. Real email, SMS and push providers are out of scope: senders are injected.

Everything below must be importable from the package root: `from notify import User, TemplateStore, NotificationService, DeliveryReport, DeliveryError`.

**User**
- `User(id, email=None, phone=None, push_token=None, preferred_channels=None)`.
- `preferred_channels` is an ordered list of channel names. If omitted, it is `["email"]`.
- The channels are `"email"`, `"sms"` and `"push"`. Their addresses are `email`, `phone` and `push_token` respectively.

**TemplateStore**
- `add(name, text)` stores a template that uses `{param}` placeholders (`str.format` style).
- `render(name, **params) -> str` fills the template.
- An unknown template name raises `KeyError`. A missing parameter raises `ValueError`.

**Senders and errors**
- A sender is any object with `send(address, message) -> None`.
- A sender raises `DeliveryError` (defined by you, in the package) when delivery fails.

**NotificationService**
- `NotificationService(senders, templates, max_retries=2)`.
  - `senders` maps channel name to sender.
  - `max_retries < 0` raises `ValueError`.
- `notify(user, template_name, **params) -> DeliveryReport`:
  1. Render the message first. Template errors propagate before anything is sent.
  2. Go through `user.preferred_channels` in order. Skip a channel, without recording an attempt, if it has no configured sender, the user has no address for it, or its name is unknown.
  3. Send to the user's address for that channel. If the sender raises `DeliveryError`, retry the same channel, up to `max_retries` extra attempts. After that, fall back to the next channel.
  4. Stop at the first successful send.
  5. Exceptions other than `DeliveryError` propagate.

**DeliveryReport**
- `delivered: bool`.
- `channel`: the channel name that succeeded, or `None`.
- `attempts`: a list of `(channel, succeeded)` tuples, in the order the attempts happened.

## Pair 1

### Implementation 1

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,14 @@
+"""Send a message to a user through their preferred channels, with retries and fallback."""
+
+from notify.senders import DeliveryError
+from notify.service import DeliveryReport, NotificationService
+from notify.templates import TemplateStore
+from notify.user import User
+
+__all__ = [
+    "DeliveryError",
+    "DeliveryReport",
+    "NotificationService",
+    "TemplateStore",
+    "User",
+]
diff -ruN before/notify/senders.py after/notify/senders.py
--- before/notify/senders.py
+++ after/notify/senders.py
@@ -0,0 +1,12 @@
+"""The contract that channel senders (email, SMS, push...) implement."""
+
+from typing import Protocol
+
+
+class DeliveryError(Exception):
+    """A sender could not deliver a message; the service retries or falls back."""
+
+
+class Sender(Protocol):
+    def send(self, address: str, message: str) -> None:
+        """Deliver ``message`` to ``address``, raising DeliveryError on failure."""
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,100 @@
+"""Delivery of a templated message over a user's preferred channels."""
+
+import logging
+from collections.abc import Iterator, Mapping
+from dataclasses import dataclass
+
+from notify.senders import DeliveryError, Sender
+from notify.templates import TemplateStore
+from notify.user import User
+
+logger = logging.getLogger(__name__)
+
+DEFAULT_MAX_RETRIES = 2
+
+type Attempt = tuple[str, bool]
+"""One send: ``(channel, succeeded)``."""
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """Outcome of one notification; ``channel`` is None when nothing was delivered.
+
+    ``attempts`` lists every send in the order it happened.
+    """
+
+    delivered: bool
+    channel: str | None
+    attempts: list[Attempt]
+
+
+@dataclass(frozen=True)
+class _Route:
+    """A preferred channel that can be used now: it has a sender and an address."""
+
+    channel: str
+    address: str
+    sender: Sender
+
+
+class NotificationService:
+    """Sends a message over a user's channels, retrying each, then falling back."""
+
+    def __init__(
+        self,
+        senders: Mapping[str, Sender],
+        templates: TemplateStore,
+        max_retries: int = DEFAULT_MAX_RETRIES,
+    ) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must be 0 or more, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._attempts_per_channel = 1 + max_retries
+
+    def notify(
+        self, user: User, template_name: str, /, **params: object
+    ) -> DeliveryReport:
+        """Render ``template_name`` with ``params`` and deliver it to ``user``.
+
+        Template errors are raised before anything is sent. A DeliveryError from
+        a sender is retried, then the next channel is tried; any other exception
+        from a sender propagates.
+        """
+        # user and template_name are positional-only so templates may use
+        # {user} or {template_name} placeholders.
+        message = self._templates.render(template_name, **params)
+        attempts: list[Attempt] = []
+        for route in self._routes_to(user):
+            route_attempts = self._send_with_retries(route, message)
+            attempts.extend(route_attempts)
+            if any(succeeded for _, succeeded in route_attempts):
+                return DeliveryReport(
+                    delivered=True, channel=route.channel, attempts=attempts
+                )
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _routes_to(self, user: User) -> Iterator[_Route]:
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is not None and address is not None:
+                yield _Route(channel, address, sender)
+
+    def _send_with_retries(self, route: _Route, message: str) -> list[Attempt]:
+        attempts: list[Attempt] = []
+        for _ in range(self._attempts_per_channel):
+            succeeded = _send_once(route, message)
+            attempts.append((route.channel, succeeded))
+            if succeeded:
+                break
+        return attempts
+
+
+def _send_once(route: _Route, message: str) -> bool:
+    try:
+        route.sender.send(route.address, message)
+    except DeliveryError as error:
+        logger.warning("Delivery via %s failed: %s", route.channel, error)
+        return False
+    return True
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,29 @@
+"""Named message templates with ``str.format``-style ``{param}`` placeholders."""
+
+
+class TemplateStore:
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store ``text`` under ``name``, replacing any template of that name."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill template ``name`` with ``params``.
+
+        Raises KeyError for an unknown template, ValueError for a missing parameter.
+        """
+        # name is positional-only so templates may use a {name} placeholder.
+        template = self._template(name)
+        try:
+            return template.format(**params)
+        except KeyError as error:
+            raise ValueError(
+                f"template {name!r} is missing parameter {error}"
+            ) from error
+
+    def _template(self, name: str) -> str:
+        if name not in self._templates:
+            raise KeyError(f"unknown template {name!r}")
+        return self._templates[name]
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,55 @@
+"""Notification recipients and the channels they can be reached on."""
+
+from dataclasses import dataclass
+from enum import StrEnum
+
+
+class Channel(StrEnum):
+    EMAIL = "email"
+    SMS = "sms"
+    PUSH = "push"
+
+
+DEFAULT_PREFERRED_CHANNELS = (Channel.EMAIL,)
+
+
+@dataclass(init=False)
+class User:
+    """A recipient: one address per channel and channels in order of preference."""
+
+    id: str
+    email: str | None
+    phone: str | None
+    push_token: str | None
+    preferred_channels: list[str]
+
+    # Hand-written so that an explicit preferred_channels=None also gets the default.
+    def __init__(
+        self,
+        id: str,
+        email: str | None = None,
+        phone: str | None = None,
+        push_token: str | None = None,
+        preferred_channels: list[str] | None = None,
+    ) -> None:
+        self.id = id
+        self.email = email
+        self.phone = phone
+        self.push_token = push_token
+        self.preferred_channels = list(
+            DEFAULT_PREFERRED_CHANNELS
+            if preferred_channels is None
+            else preferred_channels
+        )
+
+    def address_for(self, channel: str) -> str | None:
+        """Return the address on ``channel``, or None if there is none.
+
+        None also covers an unknown channel name and an empty address.
+        """
+        addresses: dict[str, str | None] = {
+            Channel.EMAIL: self.email,
+            Channel.SMS: self.phone,
+            Channel.PUSH: self.push_token,
+        }
+        return addresses.get(channel) or None
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,296 @@
+import logging
+import sys
+
+import pytest
+
+from notify import (
+    DeliveryError,
+    DeliveryReport,
+    NotificationService,
+    TemplateStore,
+    User,
+)
+
+EMAIL = "ada@example.com"
+PHONE = "+39 035 123 4567"
+PUSH_TOKEN = "push-token-ada"
+MESSAGE = "Your code is 1234"
+
+
+class FakeSender:
+    """Records every send and fails the first ``failures`` of them."""
+
+    def __init__(self, failures: int = 0) -> None:
+        self.calls: list[tuple[str, str]] = []
+        self._failures_left = failures
+
+    def send(self, address: str, message: str) -> None:
+        self.calls.append((address, message))
+        if self._failures_left > 0:
+            self._failures_left -= 1
+            raise DeliveryError("simulated outage")
+
+
+def broken_sender() -> FakeSender:
+    return FakeSender(failures=sys.maxsize)
+
+
+class CrashingSender:
+    """Fails with a bug rather than a delivery failure."""
+
+    def __init__(self) -> None:
+        self.call_count = 0
+
+    def send(self, address: str, message: str) -> None:
+        self.call_count += 1
+        raise RuntimeError("sender bug")
+
+
+@pytest.fixture
+def templates() -> TemplateStore:
+    store = TemplateStore()
+    store.add("code", "Your code is {code}")
+    return store
+
+
+def reachable_user(*preferred_channels: str) -> User:
+    return User(
+        "ada",
+        email=EMAIL,
+        phone=PHONE,
+        push_token=PUSH_TOKEN,
+        preferred_channels=list(preferred_channels),
+    )
+
+
+def send_code(service: NotificationService, user: User) -> DeliveryReport:
+    return service.notify(user, "code", code="1234")
+
+
+def test_negative_max_retries_is_rejected(templates: TemplateStore) -> None:
+    with pytest.raises(ValueError, match="max_retries"):
+        NotificationService({}, templates, max_retries=-1)
+
+
+class TestTemplateErrors:
+    def test_unknown_template_raises_before_sending(
+        self, templates: TemplateStore
+    ) -> None:
+        sender = FakeSender()
+        service = NotificationService({"email": sender}, templates)
+
+        with pytest.raises(KeyError):
+            service.notify(reachable_user("email"), "missing")
+
+        assert sender.calls == []
+
+    def test_missing_parameter_raises_before_sending(
+        self, templates: TemplateStore
+    ) -> None:
+        sender = FakeSender()
+        service = NotificationService({"email": sender}, templates)
+
+        with pytest.raises(ValueError):
+            service.notify(reachable_user("email"), "code")
+
+        assert sender.calls == []
+
+
+class TestDelivery:
+    @pytest.mark.parametrize(
+        ("channel", "address"),
+        [("email", EMAIL), ("sms", PHONE), ("push", PUSH_TOKEN)],
+    )
+    def test_sends_rendered_message_to_the_channel_address(
+        self, templates: TemplateStore, channel: str, address: str
+    ) -> None:
+        sender = FakeSender()
+        service = NotificationService({channel: sender}, templates)
+
+        send_code(service, reachable_user(channel))
+
+        assert sender.calls == [(address, MESSAGE)]
+
+    def test_accepts_template_parameters_named_like_notify_arguments(
+        self, templates: TemplateStore
+    ) -> None:
+        templates.add("signed", "{template_name} for {user}")
+        sender = FakeSender()
+        service = NotificationService({"email": sender}, templates)
+
+        service.notify(
+            reachable_user("email"), "signed", user="Ada", template_name="Invite"
+        )
+
+        assert sender.calls == [(EMAIL, "Invite for Ada")]
+
+    def test_reports_delivery_on_first_preferred_channel(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"email": FakeSender(), "sms": FakeSender()}, templates
+        )
+
+        report = send_code(service, reachable_user("sms", "email"))
+
+        assert report == DeliveryReport(
+            delivered=True, channel="sms", attempts=[("sms", True)]
+        )
+
+    def test_uses_email_when_user_states_no_preference(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"email": FakeSender(), "sms": FakeSender()}, templates
+        )
+
+        report = send_code(service, User("ada", email=EMAIL, phone=PHONE))
+
+        assert report.channel == "email"
+
+    def test_does_not_use_later_channels_after_a_success(
+        self, templates: TemplateStore
+    ) -> None:
+        sms = FakeSender()
+        service = NotificationService(
+            {"email": FakeSender(failures=1), "sms": sms}, templates
+        )
+
+        send_code(service, reachable_user("email", "sms"))
+
+        assert sms.calls == []
+
+
+class TestRetriesAndFallback:
+    def test_retries_a_failing_channel_until_it_succeeds(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"sms": FakeSender(failures=2)}, templates, max_retries=2
+        )
+
+        report = send_code(service, reachable_user("sms"))
+
+        assert report == DeliveryReport(
+            delivered=True,
+            channel="sms",
+            attempts=[("sms", False), ("sms", False), ("sms", True)],
+        )
+
+    def test_falls_back_to_next_channel_when_retries_are_exhausted(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"email": broken_sender(), "sms": FakeSender()}, templates, max_retries=1
+        )
+
+        report = send_code(service, reachable_user("email", "sms"))
+
+        assert report == DeliveryReport(
+            delivered=True,
+            channel="sms",
+            attempts=[("email", False), ("email", False), ("sms", True)],
+        )
+
+    def test_zero_max_retries_means_one_attempt_per_channel(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"email": broken_sender(), "sms": FakeSender()}, templates, max_retries=0
+        )
+
+        report = send_code(service, reachable_user("email", "sms"))
+
+        assert report.attempts == [("email", False), ("sms", True)]
+
+    def test_default_max_retries_is_two(self, templates: TemplateStore) -> None:
+        sender = broken_sender()
+        service = NotificationService({"email": sender}, templates)
+
+        send_code(service, reachable_user("email"))
+
+        assert len(sender.calls) == 3
+
+    def test_reports_failure_when_every_channel_fails(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"email": broken_sender(), "push": broken_sender()},
+            templates,
+            max_retries=1,
+        )
+
+        report = send_code(service, reachable_user("email", "push"))
+
+        assert report == DeliveryReport(
+            delivered=False,
+            channel=None,
+            attempts=[
+                ("email", False),
+                ("email", False),
+                ("push", False),
+                ("push", False),
+            ],
+        )
+
+    def test_logs_why_an_attempt_failed(
+        self, templates: TemplateStore, caplog: pytest.LogCaptureFixture
+    ) -> None:
+        service = NotificationService({"email": FakeSender(failures=1)}, templates)
+
+        with caplog.at_level(logging.WARNING, logger="notify"):
+            send_code(service, reachable_user("email"))
+
+        assert "simulated outage" in caplog.text
+
+    def test_other_sender_errors_propagate_without_retry(
+        self, templates: TemplateStore
+    ) -> None:
+        sender = CrashingSender()
+        service = NotificationService({"email": sender, "sms": FakeSender()}, templates)
+
+        with pytest.raises(RuntimeError):
+            send_code(service, reachable_user("email", "sms"))
+
+        assert sender.call_count == 1
+
+
+class TestSkippedChannels:
+    def test_skips_channel_without_a_sender(self, templates: TemplateStore) -> None:
+        service = NotificationService({"sms": FakeSender()}, templates)
+
+        report = send_code(service, reachable_user("email", "sms"))
+
+        assert report.attempts == [("sms", True)]
+
+    def test_skips_channel_the_user_has_no_address_for(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"email": FakeSender(), "sms": FakeSender()}, templates
+        )
+        user = User("ada", phone=PHONE, preferred_channels=["email", "sms"])
+
+        report = send_code(service, user)
+
+        assert report.attempts == [("sms", True)]
+
+    def test_skips_unknown_channel_even_when_it_has_a_sender(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService(
+            {"fax": FakeSender(), "sms": FakeSender()}, templates
+        )
+
+        report = send_code(service, reachable_user("fax", "sms"))
+
+        assert report.attempts == [("sms", True)]
+
+    def test_reports_nothing_delivered_when_no_channel_is_reachable(
+        self, templates: TemplateStore
+    ) -> None:
+        service = NotificationService({"email": FakeSender()}, templates)
+
+        report = send_code(service, User("ada", phone=PHONE))
+
+        assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,41 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def store() -> TemplateStore:
+    store = TemplateStore()
+    store.add("welcome", "Hi {first_name}, welcome to {product}!")
+    return store
+
+
+def test_render_fills_every_placeholder(store: TemplateStore) -> None:
+    rendered = store.render("welcome", first_name="Ada", product="Notify")
+
+    assert rendered == "Hi Ada, welcome to Notify!"
+
+
+def test_render_accepts_a_parameter_called_name() -> None:
+    store = TemplateStore()
+    store.add("greeting", "Hello {name}")
+
+    assert store.render("greeting", name="Ada") == "Hello Ada"
+
+
+def test_add_replaces_a_template_with_the_same_name(store: TemplateStore) -> None:
+    store.add("welcome", "Welcome back, {first_name}")
+
+    assert store.render("welcome", first_name="Ada") == "Welcome back, Ada"
+
+
+def test_render_of_unknown_template_raises_key_error(store: TemplateStore) -> None:
+    with pytest.raises(KeyError, match="goodbye"):
+        store.render("goodbye")
+
+
+def test_render_with_missing_parameter_raises_value_error(
+    store: TemplateStore,
+) -> None:
+    with pytest.raises(ValueError, match="product"):
+        store.render("welcome", first_name="Ada")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,62 @@
+import pytest
+
+from notify import User
+
+EMAIL = "ada@example.com"
+PHONE = "+39 035 123 4567"
+PUSH_TOKEN = "push-token-ada"
+
+
+def test_preferred_channels_default_to_email() -> None:
+    assert User("ada").preferred_channels == ["email"]
+
+
+def test_each_user_gets_its_own_default_channel_list() -> None:
+    first, second = User("ada"), User("bob")
+
+    first.preferred_channels.append("sms")
+
+    assert second.preferred_channels == ["email"]
+
+
+def test_explicitly_empty_preferred_channels_stay_empty() -> None:
+    assert User("ada", preferred_channels=[]).preferred_channels == []
+
+
+def test_preferred_channels_are_copied_from_the_caller() -> None:
+    channels = ["sms"]
+    user = User("ada", preferred_channels=channels)
+
+    channels.append("push")
+
+    assert user.preferred_channels == ["sms"]
+
+
+@pytest.mark.parametrize(
+    ("channel", "address"),
+    [("email", EMAIL), ("sms", PHONE), ("push", PUSH_TOKEN)],
+)
+def test_address_for_returns_the_address_of_each_channel(
+    channel: str, address: str
+) -> None:
+    user = User("ada", email=EMAIL, phone=PHONE, push_token=PUSH_TOKEN)
+
+    assert user.address_for(channel) == address
+
+
+def test_address_for_unknown_channel_is_none() -> None:
+    user = User("ada", email=EMAIL)
+
+    assert user.address_for("fax") is None
+
+
+def test_address_for_channel_without_address_is_none() -> None:
+    user = User("ada", email=EMAIL)
+
+    assert user.address_for("sms") is None
+
+
+def test_address_for_channel_with_empty_address_is_none() -> None:
+    user = User("ada", email="")
+
+    assert user.address_for("email") is None
```

### Implementation 2

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,16 @@
+"""Send a templated message to a user through their preferred channels."""
+
+from .errors import DeliveryError
+from .report import DeliveryReport
+from .service import NotificationService, Sender
+from .templates import TemplateStore
+from .user import User
+
+__all__ = [
+    "DeliveryError",
+    "DeliveryReport",
+    "NotificationService",
+    "Sender",
+    "TemplateStore",
+    "User",
+]
diff -ruN before/notify/errors.py after/notify/errors.py
--- before/notify/errors.py
+++ after/notify/errors.py
@@ -0,0 +1,10 @@
+"""Exceptions raised by the notify package and by the senders it drives."""
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when a message could not be delivered.
+
+    The service treats this as a recoverable failure: it retries the same
+    channel and then falls back to the next one. Any other exception raised
+    by a sender is considered a bug and propagates to the caller.
+    """
diff -ruN before/notify/report.py after/notify/report.py
--- before/notify/report.py
+++ after/notify/report.py
@@ -0,0 +1,20 @@
+"""The outcome of a single notification request."""
+
+from dataclasses import dataclass, field
+
+Attempt = tuple[str, bool]
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """What happened when a notification was sent.
+
+    Attributes:
+        delivered: whether any channel accepted the message.
+        channel: the channel that succeeded, or ``None``.
+        attempts: ``(channel, succeeded)`` for every send, in order.
+    """
+
+    delivered: bool
+    channel: str | None = None
+    attempts: list[Attempt] = field(default_factory=list)
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,79 @@
+"""Delivery of rendered messages through a user's preferred channels."""
+
+from collections.abc import Mapping
+from typing import Protocol
+
+from .errors import DeliveryError
+from .report import Attempt, DeliveryReport
+from .templates import TemplateStore
+from .user import User
+
+
+class Sender(Protocol):
+    """Anything that can deliver a message to an address on one channel."""
+
+    def send(self, address: str, message: str) -> None:
+        """Deliver ``message``, or raise ``DeliveryError`` on failure."""
+
+
+class NotificationService:
+    """Sends templated messages with per-channel retries and fallback."""
+
+    def __init__(
+        self,
+        senders: Mapping[str, Sender],
+        templates: TemplateStore,
+        max_retries: int = 2,
+    ) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._max_retries = max_retries
+
+    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
+        """Render ``template_name`` and deliver it to ``user``.
+
+        Channels are tried in the user's preference order. A channel is
+        skipped, without an attempt, when it has no sender or the user has
+        no address for it. A ``DeliveryError`` triggers up to
+        ``max_retries`` extra attempts on the same channel before falling
+        back to the next one. Delivery stops at the first success.
+
+        ``user`` and ``template_name`` are positional-only so that template
+        parameters may use those names.
+
+        Raises:
+            KeyError, ValueError: the template is unknown or a parameter is
+                missing; nothing is sent.
+            Exception: anything a sender raises other than ``DeliveryError``.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[Attempt] = []
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is None or address is None:
+                continue
+            if self._send_with_retries(channel, sender, address, message, attempts):
+                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _send_with_retries(
+        self,
+        channel: str,
+        sender: Sender,
+        address: str,
+        message: str,
+        attempts: list[Attempt],
+    ) -> bool:
+        """Try one channel up to ``1 + max_retries`` times, recording each try."""
+        for _ in range(1 + self._max_retries):
+            try:
+                sender.send(address, message)
+            except DeliveryError:
+                attempts.append((channel, False))
+                continue
+            attempts.append((channel, True))
+            return True
+        return False
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,30 @@
+"""Named message templates using ``str.format`` placeholders."""
+
+
+class TemplateStore:
+    """Stores templates by name and renders them with keyword parameters."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store ``text`` under ``name``, replacing any existing template."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill the template ``name`` with ``params``.
+
+        ``name`` is positional-only so that a template may itself use a
+        ``{name}`` placeholder.
+
+        Raises:
+            KeyError: no template is stored under ``name``.
+            ValueError: the template needs a parameter that was not given.
+        """
+        text = self._templates[name]
+        try:
+            return text.format(**params)
+        except (KeyError, IndexError) as missing:
+            raise ValueError(
+                f"Template {name!r} is missing parameter {missing}"
+            ) from missing
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,42 @@
+"""The notification recipient and the addresses it exposes per channel."""
+
+from dataclasses import dataclass
+from typing import Any
+
+DEFAULT_CHANNELS = ("email",)
+
+# Which User attribute holds the address for each known channel.
+_ADDRESS_FIELD_BY_CHANNEL = {
+    "email": "email",
+    "sms": "phone",
+    "push": "push_token",
+}
+
+
+@dataclass
+class User:
+    """A recipient with optional addresses and an ordered channel preference."""
+
+    id: Any
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        # Copy so later changes to the caller's list do not leak into the user.
+        if self.preferred_channels is None:
+            self.preferred_channels = list(DEFAULT_CHANNELS)
+        else:
+            self.preferred_channels = list(self.preferred_channels)
+
+    def address_for(self, channel: str) -> str | None:
+        """Return this user's address for ``channel``.
+
+        Returns ``None`` when the channel is unknown or the user has no
+        address for it (an empty string counts as no address).
+        """
+        field_name = _ADDRESS_FIELD_BY_CHANNEL.get(channel)
+        if field_name is None:
+            return None
+        return getattr(self, field_name) or None
diff -ruN before/tests/test_notify.py after/tests/test_notify.py
--- before/tests/test_notify.py
+++ after/tests/test_notify.py
@@ -0,0 +1,263 @@
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+
+class FakeSender:
+    """Records every send and fails the first ``failures`` of them."""
+
+    def __init__(self, failures=0, error=None):
+        self.failures = failures
+        self.error = error
+        self.calls = []
+
+    def send(self, address, message):
+        self.calls.append((address, message))
+        if self.error is not None:
+            raise self.error
+        if len(self.calls) <= self.failures:
+            raise DeliveryError("temporary failure")
+
+
+ALWAYS_FAILS = 10**6
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}!")
+    return store
+
+
+def full_user(channels):
+    return User(
+        id=1,
+        email="a@example.com",
+        phone="+391234",
+        push_token="tok",
+        preferred_channels=channels,
+    )
+
+
+# --- User -------------------------------------------------------------------
+
+
+def test_user_defaults_to_email_channel():
+    assert User(id=1).preferred_channels == ["email"]
+
+
+def test_user_default_channels_are_not_shared_between_instances():
+    first = User(id=1)
+    first.preferred_channels.append("sms")
+    assert User(id=2).preferred_channels == ["email"]
+
+
+def test_user_copies_given_channel_list():
+    channels = ["sms"]
+    user = User(id=1, preferred_channels=channels)
+    channels.append("push")
+    assert user.preferred_channels == ["sms"]
+
+
+def test_user_address_for_maps_channels_to_fields():
+    user = full_user(["email"])
+    assert user.address_for("email") == "a@example.com"
+    assert user.address_for("sms") == "+391234"
+    assert user.address_for("push") == "tok"
+    assert user.address_for("fax") is None
+
+
+# --- TemplateStore ----------------------------------------------------------
+
+
+def test_render_fills_placeholders(templates):
+    assert templates.render("welcome", name="Ana") == "Hello Ana!"
+
+
+def test_render_unknown_template_raises_key_error(templates):
+    with pytest.raises(KeyError):
+        templates.render("nope")
+
+
+def test_render_missing_parameter_raises_value_error(templates):
+    with pytest.raises(ValueError):
+        templates.render("welcome")
+
+
+def test_render_missing_positional_placeholder_raises_value_error():
+    store = TemplateStore()
+    store.add("pos", "Hi {0}")
+    with pytest.raises(ValueError):
+        store.render("pos")
+
+
+def test_add_replaces_existing_template(templates):
+    templates.add("welcome", "Hi {name}")
+    assert templates.render("welcome", name="Bo") == "Hi Bo"
+
+
+# --- NotificationService: construction --------------------------------------
+
+
+def test_negative_max_retries_raises(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_zero_max_retries_is_allowed(templates):
+    NotificationService({}, templates, max_retries=0)
+
+
+# --- NotificationService: notify --------------------------------------------
+
+
+def test_delivers_on_first_preferred_channel(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(full_user(["email"]), "welcome", name="Ana")
+
+    assert report == DeliveryReport(True, "email", [("email", True)])
+    assert email.calls == [("a@example.com", "Hello Ana!")]
+
+
+def test_template_errors_propagate_before_sending(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(KeyError):
+        service.notify(full_user(["email"]), "missing")
+    with pytest.raises(ValueError):
+        service.notify(full_user(["email"]), "welcome")
+    assert email.calls == []
+
+
+def test_retries_same_channel_then_succeeds(templates):
+    email = FakeSender(failures=2)
+    service = NotificationService({"email": email}, templates, max_retries=2)
+
+    report = service.notify(full_user(["email"]), "welcome", name="Ana")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", False), ("email", False), ("email", True)]
+
+
+def test_falls_back_after_exhausting_retries(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)
+
+    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ana")
+
+    assert report.channel == "sms"
+    assert report.attempts == [("email", False), ("email", False), ("sms", True)]
+    assert sms.calls == [("+391234", "Hello Ana!")]
+
+
+def test_zero_retries_means_one_attempt_per_channel(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    push = FakeSender()
+    service = NotificationService({"email": email, "push": push}, templates, max_retries=0)
+
+    report = service.notify(full_user(["email", "push"]), "welcome", name="Ana")
+
+    assert report.attempts == [("email", False), ("push", True)]
+
+
+def test_all_channels_fail(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    sms = FakeSender(failures=ALWAYS_FAILS)
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)
+
+    report = service.notify(full_user(["sms", "email"]), "welcome", name="Ana")
+
+    assert report == DeliveryReport(
+        False,
+        None,
+        [("sms", False), ("sms", False), ("email", False), ("email", False)],
+    )
+
+
+def test_stops_at_first_success(templates):
+    email = FakeSender()
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    service.notify(full_user(["email", "sms"]), "welcome", name="Ana")
+
+    assert sms.calls == []
+
+
+def test_skips_channel_without_sender(templates):
+    sms = FakeSender()
+    service = NotificationService({"sms": sms}, templates)
+
+    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ana")
+
+    assert report.attempts == [("sms", True)]
+
+
+def test_skips_channel_without_user_address(templates):
+    email = FakeSender()
+    push = FakeSender()
+    service = NotificationService({"email": email, "push": push}, templates)
+    user = User(id=1, push_token="tok", preferred_channels=["email", "push"])
+
+    report = service.notify(user, "welcome", name="Ana")
+
+    assert report.attempts == [("push", True)]
+    assert email.calls == []
+
+
+def test_skips_unknown_channel_even_with_sender(templates):
+    fax = FakeSender()
+    email = FakeSender()
+    service = NotificationService({"fax": fax, "email": email}, templates)
+
+    report = service.notify(full_user(["fax", "email"]), "welcome", name="Ana")
+
+    assert report.attempts == [("email", True)]
+    assert fax.calls == []
+
+
+def test_nothing_usable_returns_undelivered_with_no_attempts(templates):
+    service = NotificationService({}, templates)
+
+    report = service.notify(User(id=1), "welcome", name="Ana")
+
+    assert report == DeliveryReport(False, None, [])
+
+
+def test_non_delivery_errors_propagate(templates):
+    email = FakeSender(error=RuntimeError("bug"))
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError):
+        service.notify(full_user(["email", "sms"]), "welcome", name="Ana")
+    assert len(email.calls) == 1
+    assert sms.calls == []
+
+
+def test_delivery_error_subclasses_are_retried(templates):
+    class Timeout(DeliveryError):
+        pass
+
+    email = FakeSender(error=Timeout())
+    service = NotificationService({"email": email}, templates, max_retries=1)
+
+    report = service.notify(full_user(["email"]), "welcome", name="Ana")
+
+    assert report.attempts == [("email", False), ("email", False)]
+
+
+def test_template_params_may_use_reserved_argument_names():
+    store = TemplateStore()
+    store.add("t", "{user} {template_name} {name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, store)
+
+    service.notify(full_user(["email"]), "t", user="u", template_name="n", name="x")
+
+    assert email.calls == [("a@example.com", "u n x")]
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,17 @@
+"""Send a templated message to a user over their preferred channels, with retries and fallback."""
+
+from notify.report import Attempt, DeliveryReport
+from notify.senders import DeliveryError, Sender
+from notify.service import NotificationService
+from notify.templates import TemplateStore
+from notify.user import User
+
+__all__ = [
+    "Attempt",
+    "DeliveryError",
+    "DeliveryReport",
+    "NotificationService",
+    "Sender",
+    "TemplateStore",
+    "User",
+]
diff -ruN before/notify/report.py after/notify/report.py
--- before/notify/report.py
+++ after/notify/report.py
@@ -0,0 +1,20 @@
+"""The outcome of a notification."""
+
+from dataclasses import dataclass
+from typing import NamedTuple
+
+
+class Attempt(NamedTuple):
+    """One send attempt; a plain ``(channel, succeeded)`` tuple with names."""
+
+    channel: str
+    succeeded: bool
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """Whether a notification was delivered, on which channel, and every attempt made."""
+
+    delivered: bool
+    channel: str | None
+    attempts: list[Attempt]
diff -ruN before/notify/senders.py after/notify/senders.py
--- before/notify/senders.py
+++ after/notify/senders.py
@@ -0,0 +1,15 @@
+"""The contract between the notification service and channel senders."""
+
+from typing import Protocol
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it could not deliver a message."""
+
+
+class Sender(Protocol):
+    """Delivers a message to an address on one channel (email, SMS, push...)."""
+
+    def send(self, address: str, message: str) -> None:
+        """Deliver ``message`` to ``address``; raise DeliveryError on failure."""
+        ...
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,72 @@
+"""Delivery of templated messages over a user's preferred channels."""
+
+import logging
+from collections.abc import Mapping
+
+from notify.report import Attempt, DeliveryReport
+from notify.senders import DeliveryError, Sender
+from notify.templates import TemplateStore
+from notify.user import User
+
+_logger = logging.getLogger(__name__)
+
+
+class NotificationService:
+    """Sends a message through a user's preferred channels, with retries and fallback.
+
+    Each channel is tried up to ``1 + max_retries`` times; when every attempt
+    fails, the next preferred channel is tried. Delivery stops at the first
+    successful send.
+    """
+
+    def __init__(
+        self,
+        senders: Mapping[str, Sender],
+        templates: TemplateStore,
+        max_retries: int = 2,
+    ) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must not be negative, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._max_retries = max_retries
+
+    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
+        """Render ``template_name`` with ``params`` and deliver it to ``user``.
+
+        ``user`` and ``template_name`` are positional-only so that templates
+        may use ``{user}`` or ``{template_name}`` placeholders.
+
+        Template errors propagate before anything is sent. A channel is skipped,
+        with no attempt recorded, when it has no sender, the user has no address
+        for it, or its name is unknown. Only DeliveryError triggers a retry or a
+        fallback; any other exception from a sender propagates.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[Attempt] = []
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is None or address is None:
+                continue
+            channel_attempts = self._send_with_retries(channel, sender, address, message)
+            attempts.extend(channel_attempts)
+            if channel_attempts[-1].succeeded:
+                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _send_with_retries(
+        self, channel: str, sender: Sender, address: str, message: str
+    ) -> list[Attempt]:
+        """Send on one channel until it succeeds or the retries run out."""
+        attempts: list[Attempt] = []
+        for _ in range(1 + self._max_retries):
+            try:
+                sender.send(address, message)
+            except DeliveryError as error:
+                _logger.warning("Delivery via %s failed: %s", channel, error)
+                attempts.append(Attempt(channel, succeeded=False))
+            else:
+                attempts.append(Attempt(channel, succeeded=True))
+                break
+        return attempts
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,30 @@
+"""Named message templates."""
+
+
+class TemplateStore:
+    """Stores templates that use ``str.format``-style ``{param}`` placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store ``text`` under ``name``, replacing any template with that name."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill the template ``name`` with ``params``.
+
+        ``name`` is positional-only so that templates may use ``{name}``.
+        Raises KeyError if no template has that name, and ValueError if a
+        placeholder has no matching parameter.
+        """
+        try:
+            text = self._templates[name]
+        except KeyError:
+            raise KeyError(f"unknown template: {name!r}") from None
+        try:
+            return text.format(**params)
+        except (KeyError, IndexError) as error:
+            # IndexError comes from positional placeholders ("{}", "{0}"),
+            # which can never be filled because only keyword params are accepted.
+            raise ValueError(f"template {name!r} is missing a parameter: {error}") from error
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,34 @@
+"""The recipient of a notification."""
+
+from dataclasses import dataclass
+
+_DEFAULT_CHANNELS = ("email",)
+
+
+@dataclass
+class User:
+    """A user and the addresses at which they can be reached.
+
+    ``preferred_channels`` lists channel names in order of preference;
+    omitting it (or passing None) means ``["email"]``. The list is copied,
+    so later changes to the caller's list do not affect the user.
+    """
+
+    id: object
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        channels = self.preferred_channels
+        self.preferred_channels = list(_DEFAULT_CHANNELS if channels is None else channels)
+
+    def address_for(self, channel: str) -> str | None:
+        """Return the user's address on ``channel``.
+
+        Returns None when the channel name is unknown or the user has no
+        (or an empty) address for it.
+        """
+        addresses = {"email": self.email, "sms": self.phone, "push": self.push_token}
+        return addresses.get(channel) or None
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,205 @@
+import math
+
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+
+class ScriptedSender:
+    """Fails the first ``failures`` sends, then succeeds; records every call."""
+
+    def __init__(self, failures=0):
+        self._failures_left = failures
+        self.calls = []
+
+    def send(self, address, message):
+        self.calls.append((address, message))
+        if self._failures_left > 0:
+            self._failures_left -= 1
+            raise DeliveryError("simulated failure")
+
+
+def failing_sender():
+    return ScriptedSender(failures=math.inf)
+
+
+class CrashingSender:
+    def send(self, address, message):
+        raise RuntimeError("bug in sender")
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("hello", "Hello {name}")
+    return store
+
+
+def make_user(channels=None):
+    return User(
+        id=1,
+        email="ada@example.com",
+        phone="+391234",
+        push_token="tok",
+        preferred_channels=channels,
+    )
+
+
+def test_delivers_rendered_message_to_first_preferred_channel(templates):
+    email = ScriptedSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(make_user(), "hello", name="Ada")
+
+    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
+    assert email.calls == [("ada@example.com", "Hello Ada")]
+
+
+def test_sends_to_the_address_of_each_channel(templates):
+    sms, push = failing_sender(), ScriptedSender()
+    service = NotificationService({"sms": sms, "push": push}, templates, max_retries=0)
+
+    service.notify(make_user(["sms", "push"]), "hello", name="Ada")
+
+    assert sms.calls == [("+391234", "Hello Ada")]
+    assert push.calls == [("tok", "Hello Ada")]
+
+
+def test_retries_same_channel_until_it_succeeds(templates):
+    email = ScriptedSender(failures=2)
+    service = NotificationService({"email": email}, templates, max_retries=2)
+
+    report = service.notify(make_user(), "hello", name="Ada")
+
+    assert report.delivered
+    assert report.channel == "email"
+    assert report.attempts == [("email", False), ("email", False), ("email", True)]
+
+
+def test_falls_back_to_next_channel_after_retries_run_out(templates):
+    service = NotificationService(
+        {"email": failing_sender(), "sms": ScriptedSender()}, templates, max_retries=1
+    )
+
+    report = service.notify(make_user(["email", "sms"]), "hello", name="Ada")
+
+    assert report.channel == "sms"
+    assert report.attempts == [("email", False), ("email", False), ("sms", True)]
+
+
+def test_default_max_retries_is_two(templates):
+    service = NotificationService({"email": failing_sender()}, templates)
+
+    report = service.notify(make_user(), "hello", name="Ada")
+
+    assert report.attempts == [("email", False)] * 3
+
+
+def test_zero_retries_means_one_attempt_per_channel(templates):
+    service = NotificationService(
+        {"email": failing_sender(), "push": failing_sender()}, templates, max_retries=0
+    )
+
+    report = service.notify(make_user(["email", "push"]), "hello", name="Ada")
+
+    assert report.attempts == [("email", False), ("push", False)]
+
+
+def test_reports_failure_when_every_channel_fails(templates):
+    service = NotificationService(
+        {"email": failing_sender(), "sms": failing_sender()}, templates, max_retries=0
+    )
+
+    report = service.notify(make_user(["email", "sms"]), "hello", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=False, channel=None, attempts=[("email", False), ("sms", False)]
+    )
+
+
+def test_stops_at_first_successful_send(templates):
+    email, sms = ScriptedSender(), ScriptedSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    service.notify(make_user(["email", "sms"]), "hello", name="Ada")
+
+    assert sms.calls == []
+
+
+def test_skips_channel_without_a_sender(templates):
+    service = NotificationService({"sms": ScriptedSender()}, templates)
+
+    report = service.notify(make_user(["email", "sms"]), "hello", name="Ada")
+
+    assert report.attempts == [("sms", True)]
+
+
+def test_skips_channel_without_an_address(templates):
+    email, sms = ScriptedSender(), ScriptedSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+    user = User(id=1, phone="+391234", preferred_channels=["email", "sms"])
+
+    report = service.notify(user, "hello", name="Ada")
+
+    assert report.attempts == [("sms", True)]
+    assert email.calls == []
+
+
+def test_skips_unknown_channel_even_with_a_sender(templates):
+    fax = ScriptedSender()
+    service = NotificationService({"fax": fax, "email": ScriptedSender()}, templates)
+
+    report = service.notify(make_user(["fax", "email"]), "hello", name="Ada")
+
+    assert report.attempts == [("email", True)]
+    assert fax.calls == []
+
+
+def test_no_reachable_channel_reports_no_attempts(templates):
+    service = NotificationService({"email": ScriptedSender()}, templates)
+
+    report = service.notify(User(id=1), "hello", name="Ada")
+
+    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
+
+
+def test_unknown_template_fails_before_sending(templates):
+    email = ScriptedSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(KeyError):
+        service.notify(make_user(), "missing")
+    assert email.calls == []
+
+
+def test_missing_parameter_fails_before_sending(templates):
+    email = ScriptedSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(ValueError):
+        service.notify(make_user(), "hello")
+    assert email.calls == []
+
+
+def test_non_delivery_errors_propagate(templates):
+    service = NotificationService(
+        {"email": CrashingSender(), "sms": ScriptedSender()}, templates
+    )
+
+    with pytest.raises(RuntimeError):
+        service.notify(make_user(["email", "sms"]), "hello", name="Ada")
+
+
+def test_template_params_may_share_names_with_notify_arguments(templates):
+    templates.add("clash", "{user} used {template_name}")
+    email = ScriptedSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(make_user(), "clash", user="Ada", template_name="clash")
+
+    assert email.calls == [("ada@example.com", "Ada used clash")]
+
+
+def test_negative_max_retries_is_rejected(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,38 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def store():
+    templates = TemplateStore()
+    templates.add("welcome", "Hi {name}, welcome to {product}!")
+    return templates
+
+
+def test_render_fills_placeholders(store):
+    assert store.render("welcome", name="Ada", product="Notify") == "Hi Ada, welcome to Notify!"
+
+
+def test_add_replaces_existing_template(store):
+    store.add("welcome", "Hello {name}")
+
+    assert store.render("welcome", name="Ada") == "Hello Ada"
+
+
+def test_unknown_template_raises_key_error(store):
+    with pytest.raises(KeyError):
+        store.render("missing")
+
+
+def test_missing_parameter_raises_value_error(store):
+    with pytest.raises(ValueError, match="name"):
+        store.render("welcome", product="Notify")
+
+
+def test_positional_placeholder_raises_value_error():
+    store = TemplateStore()
+    store.add("positional", "Code: {}")
+
+    with pytest.raises(ValueError):
+        store.render("positional")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,38 @@
+from notify import User
+
+
+def test_preferred_channels_default_to_email():
+    assert User(id=1).preferred_channels == ["email"]
+
+
+def test_default_channels_are_not_shared_between_users():
+    first, second = User(id=1), User(id=2)
+
+    first.preferred_channels.append("sms")
+
+    assert second.preferred_channels == ["email"]
+
+
+def test_preferred_channels_are_copied_from_the_caller():
+    channels = ["sms", "email"]
+    user = User(id=1, preferred_channels=channels)
+
+    channels.append("push")
+
+    assert user.preferred_channels == ["sms", "email"]
+
+
+def test_address_for_maps_each_channel_to_its_address():
+    user = User(id=1, email="a@example.com", phone="+391234", push_token="tok")
+
+    assert user.address_for("email") == "a@example.com"
+    assert user.address_for("sms") == "+391234"
+    assert user.address_for("push") == "tok"
+
+
+def test_address_for_is_none_for_missing_empty_or_unknown():
+    user = User(id=1, email="", phone=None)
+
+    assert user.address_for("email") is None
+    assert user.address_for("sms") is None
+    assert user.address_for("fax") is None
```

### Implementation 2

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,15 @@
+"""Send a message to a user over their preferred channels, with retries and fallback."""
+
+from .report import DeliveryReport
+from .sender import DeliveryError
+from .service import NotificationService
+from .templates import TemplateStore
+from .user import User
+
+__all__ = [
+    "DeliveryError",
+    "DeliveryReport",
+    "NotificationService",
+    "TemplateStore",
+    "User",
+]
diff -ruN before/notify/report.py after/notify/report.py
--- before/notify/report.py
+++ after/notify/report.py
@@ -0,0 +1,18 @@
+from dataclasses import dataclass
+from typing import NamedTuple
+
+
+class Attempt(NamedTuple):
+    """One send on one channel. Equal to a plain `(channel, succeeded)` tuple."""
+
+    channel: str
+    succeeded: bool
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """Whether and where a notification was delivered, with every attempt in order."""
+
+    delivered: bool
+    channel: str | None
+    attempts: list[Attempt]
diff -ruN before/notify/sender.py after/notify/sender.py
--- before/notify/sender.py
+++ after/notify/sender.py
@@ -0,0 +1,16 @@
+from typing import Protocol
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when a message could not be delivered.
+
+    The notification service treats it as a failed attempt and retries or falls back.
+    """
+
+
+class Sender(Protocol):
+    """Delivers messages on one channel, such as email, SMS or push."""
+
+    def send(self, address: str, message: str) -> None:
+        """Deliver `message` to `address`, raising DeliveryError if delivery fails."""
+        ...
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,86 @@
+import logging
+from collections.abc import Iterator, Mapping
+from dataclasses import dataclass
+
+from .report import Attempt, DeliveryReport
+from .sender import DeliveryError, Sender
+from .templates import TemplateStore
+from .user import User
+
+logger = logging.getLogger(__name__)
+
+
+@dataclass(frozen=True)
+class _Route:
+    """A usable channel for one user: its sender and the user's address on it."""
+
+    channel: str
+    sender: Sender
+    address: str
+
+
+class NotificationService:
+    """Sends templated messages over a user's preferred channels.
+
+    A failing channel is retried, then the next preferred channel is tried.
+    """
+
+    def __init__(
+        self,
+        senders: Mapping[str, Sender],
+        templates: TemplateStore,
+        max_retries: int = 2,
+    ) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must not be negative, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._attempts_per_channel = max_retries + 1
+
+    def notify(
+        self, user: User, template_name: str, /, **params: object
+    ) -> DeliveryReport:
+        """Render the template and deliver it on the first preferred channel that works.
+
+        Each channel gets 1 + max_retries attempts before the next one is tried.
+        Channels without a sender or without a user address are skipped unrecorded.
+        Template errors are raised before anything is sent. Sender exceptions other
+        than DeliveryError propagate.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[Attempt] = []
+        for route in self._routes_to(user):
+            channel_attempts = self._send_with_retries(route, message)
+            attempts.extend(channel_attempts)
+            if channel_attempts[-1].succeeded:
+                return DeliveryReport(
+                    delivered=True, channel=route.channel, attempts=attempts
+                )
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _routes_to(self, user: User) -> Iterator[_Route]:
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is not None and address is not None:
+                yield _Route(channel, sender, address)
+
+    def _send_with_retries(self, route: _Route, message: str) -> list[Attempt]:
+        """Send until the first success or until the channel's attempts run out."""
+        attempts: list[Attempt] = []
+        for _ in range(self._attempts_per_channel):
+            succeeded = _try_send(route, message)
+            attempts.append(Attempt(route.channel, succeeded))
+            if succeeded:
+                break
+        return attempts
+
+
+def _try_send(route: _Route, message: str) -> bool:
+    try:
+        route.sender.send(route.address, message)
+    except DeliveryError as error:
+        # Recorded as a failed attempt by the caller; logged so the cause isn't lost.
+        logger.warning("Delivery via %s failed: %s", route.channel, error)
+        return False
+    return True
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,25 @@
+class TemplateStore:
+    """Named message templates with `str.format`-style `{param}` placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store `text` as template `name`, replacing any template of that name."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill template `name` with `params`.
+
+        Raises KeyError for an unknown template and ValueError for a placeholder
+        without a matching parameter.
+        """
+        if name not in self._templates:
+            raise KeyError(f"Unknown template {name!r}")
+        try:
+            return self._templates[name].format(**params)
+        except KeyError as error:
+            missing_param = error.args[0]
+            raise ValueError(
+                f"Template {name!r} needs parameter {missing_param!r}"
+            ) from error
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,45 @@
+from collections.abc import Sequence
+from enum import StrEnum
+
+
+class Channel(StrEnum):
+    EMAIL = "email"
+    SMS = "sms"
+    PUSH = "push"
+
+
+DEFAULT_PREFERRED_CHANNELS: tuple[str, ...] = (Channel.EMAIL.value,)
+
+
+class User:
+    """A notification recipient: an address per channel and the order to try them in.
+
+    `preferred_channels` may name unknown channels; the user has no address there.
+    """
+
+    def __init__(
+        self,
+        id: str,
+        email: str | None = None,
+        phone: str | None = None,
+        push_token: str | None = None,
+        preferred_channels: Sequence[str] | None = None,
+    ) -> None:
+        self.id = id
+        self.email = email
+        self.phone = phone
+        self.push_token = push_token
+        self.preferred_channels: list[str] = list(
+            DEFAULT_PREFERRED_CHANNELS
+            if preferred_channels is None
+            else preferred_channels
+        )
+
+    def address_for(self, channel: str) -> str | None:
+        """Return the user's address on `channel`, or None if they have none there."""
+        addresses: dict[str, str | None] = {
+            Channel.EMAIL: self.email,
+            Channel.SMS: self.phone,
+            Channel.PUSH: self.push_token,
+        }
+        return addresses.get(channel)
diff -ruN before/tests/test_notification_service.py after/tests/test_notification_service.py
--- before/tests/test_notification_service.py
+++ after/tests/test_notification_service.py
@@ -0,0 +1,267 @@
+import logging
+import math
+
+import pytest
+
+from notify import DeliveryError, NotificationService, TemplateStore, User
+
+EMAIL = "alice@example.com"
+PHONE = "+390351234567"
+PUSH_TOKEN = "push-token-1"
+NEVER_SUCCEEDS = math.inf
+
+
+class FakeSender:
+    """Records every send call and fails the first `failures` of them."""
+
+    def __init__(self, failures: float = 0) -> None:
+        self._failures_left = failures
+        self.send_calls: list[tuple[str, str]] = []
+
+    def send(self, address: str, message: str) -> None:
+        self.send_calls.append((address, message))
+        if self._failures_left > 0:
+            self._failures_left -= 1
+            raise DeliveryError(f"simulated outage on {address}")
+
+
+class BuggySender:
+    def __init__(self) -> None:
+        self.send_calls = 0
+
+    def send(self, address: str, message: str) -> None:
+        self.send_calls += 1
+        raise RuntimeError("bug in sender")
+
+
+@pytest.fixture
+def templates() -> TemplateStore:
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}")
+    return store
+
+
+def user_preferring(*channels: str) -> User:
+    return User(
+        "alice",
+        email=EMAIL,
+        phone=PHONE,
+        push_token=PUSH_TOKEN,
+        preferred_channels=list(channels),
+    )
+
+
+def test_negative_max_retries_is_rejected(templates: TemplateStore) -> None:
+    with pytest.raises(ValueError, match="max_retries"):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_sends_rendered_message_to_users_address_on_first_preferred_channel(
+    templates: TemplateStore,
+) -> None:
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(user_preferring("email"), "welcome", name="Alice")
+
+    assert email.send_calls == [(EMAIL, "Hello Alice")]
+
+
+def test_successful_first_send_is_reported(templates: TemplateStore) -> None:
+    service = NotificationService({"email": FakeSender()}, templates)
+
+    report = service.notify(user_preferring("email"), "welcome", name="Alice")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", True)]
+
+
+def test_later_channels_are_not_used_after_a_success(templates: TemplateStore) -> None:
+    sms = FakeSender()
+    service = NotificationService({"email": FakeSender(), "sms": sms}, templates)
+
+    service.notify(user_preferring("email", "sms"), "welcome", name="Alice")
+
+    assert sms.send_calls == []
+
+
+def test_failed_channel_is_retried_until_it_succeeds(templates: TemplateStore) -> None:
+    service = NotificationService(
+        {"email": FakeSender(failures=1)}, templates, max_retries=2
+    )
+
+    report = service.notify(user_preferring("email"), "welcome", name="Alice")
+
+    assert report.delivered is True
+    assert report.attempts == [("email", False), ("email", True)]
+
+
+def test_falls_back_to_next_channel_once_retries_are_exhausted(
+    templates: TemplateStore,
+) -> None:
+    sms = FakeSender()
+    service = NotificationService(
+        {"email": FakeSender(failures=NEVER_SUCCEEDS), "sms": sms},
+        templates,
+        max_retries=2,
+    )
+
+    report = service.notify(user_preferring("email", "sms"), "welcome", name="Alice")
+
+    assert report.channel == "sms"
+    assert report.attempts == [
+        ("email", False),
+        ("email", False),
+        ("email", False),
+        ("sms", True),
+    ]
+    assert sms.send_calls == [(PHONE, "Hello Alice")]
+
+
+def test_default_max_retries_is_two(templates: TemplateStore) -> None:
+    email = FakeSender(failures=NEVER_SUCCEEDS)
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(user_preferring("email"), "welcome", name="Alice")
+
+    assert len(email.send_calls) == 3
+
+
+def test_zero_max_retries_falls_back_after_a_single_attempt(
+    templates: TemplateStore,
+) -> None:
+    service = NotificationService(
+        {"email": FakeSender(failures=1), "push": FakeSender()},
+        templates,
+        max_retries=0,
+    )
+
+    report = service.notify(user_preferring("email", "push"), "welcome", name="Alice")
+
+    assert report.channel == "push"
+    assert report.attempts == [("email", False), ("push", True)]
+
+
+def test_undelivered_report_when_every_channel_fails(templates: TemplateStore) -> None:
+    service = NotificationService(
+        {
+            "email": FakeSender(failures=NEVER_SUCCEEDS),
+            "sms": FakeSender(failures=NEVER_SUCCEEDS),
+        },
+        templates,
+        max_retries=1,
+    )
+
+    report = service.notify(user_preferring("email", "sms"), "welcome", name="Alice")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == [
+        ("email", False),
+        ("email", False),
+        ("sms", False),
+        ("sms", False),
+    ]
+
+
+def test_channel_without_configured_sender_is_skipped_without_attempt(
+    templates: TemplateStore,
+) -> None:
+    service = NotificationService({"email": FakeSender()}, templates)
+
+    report = service.notify(user_preferring("sms", "email"), "welcome", name="Alice")
+
+    assert report.attempts == [("email", True)]
+
+
+def test_channel_the_user_has_no_address_for_is_skipped_without_attempt(
+    templates: TemplateStore,
+) -> None:
+    sms = FakeSender()
+    service = NotificationService({"sms": sms, "email": FakeSender()}, templates)
+    user_without_phone = User("bob", email=EMAIL, preferred_channels=["sms", "email"])
+
+    report = service.notify(user_without_phone, "welcome", name="Bob")
+
+    assert report.attempts == [("email", True)]
+    assert sms.send_calls == []
+
+
+def test_unknown_channel_is_skipped_even_with_a_sender_for_it(
+    templates: TemplateStore,
+) -> None:
+    fax = FakeSender()
+    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)
+
+    report = service.notify(user_preferring("fax", "email"), "welcome", name="Alice")
+
+    assert report.attempts == [("email", True)]
+    assert fax.send_calls == []
+
+
+def test_undelivered_report_without_attempts_when_no_channel_is_usable(
+    templates: TemplateStore,
+) -> None:
+    service = NotificationService({}, templates)
+
+    report = service.notify(user_preferring("email", "sms"), "welcome", name="Alice")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == []
+
+
+@pytest.mark.parametrize(
+    ("template_name", "params", "expected_error"),
+    [("missing", {"name": "Alice"}, KeyError), ("welcome", {}, ValueError)],
+)
+def test_template_errors_propagate_before_anything_is_sent(
+    templates: TemplateStore,
+    template_name: str,
+    params: dict[str, object],
+    expected_error: type[Exception],
+) -> None:
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(expected_error):
+        service.notify(user_preferring("email"), template_name, **params)
+
+    assert email.send_calls == []
+
+
+def test_errors_other_than_delivery_error_propagate_without_retry(
+    templates: TemplateStore,
+) -> None:
+    buggy = BuggySender()
+    service = NotificationService({"email": buggy}, templates, max_retries=2)
+
+    with pytest.raises(RuntimeError, match="bug in sender"):
+        service.notify(user_preferring("email"), "welcome", name="Alice")
+
+    assert buggy.send_calls == 1
+
+
+def test_template_may_use_a_placeholder_called_user(
+    templates: TemplateStore,
+) -> None:
+    templates.add("greeting", "Hi {user}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(user_preferring("email"), "greeting", user="Alice")
+
+    assert email.send_calls == [(EMAIL, "Hi Alice")]
+
+
+def test_failed_attempt_is_logged_with_channel_and_cause(
+    templates: TemplateStore, caplog: pytest.LogCaptureFixture
+) -> None:
+    service = NotificationService({"email": FakeSender(failures=1)}, templates)
+
+    with caplog.at_level(logging.WARNING, logger="notify"):
+        service.notify(user_preferring("email"), "welcome", name="Alice")
+
+    assert "email" in caplog.text
+    assert "simulated outage" in caplog.text
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,40 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def templates() -> TemplateStore:
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}, welcome to {place}!")
+    return store
+
+
+def test_render_fills_the_placeholders(templates: TemplateStore) -> None:
+    message = templates.render("welcome", name="Alice", place="Bergamo")
+
+    assert message == "Hello Alice, welcome to Bergamo!"
+
+
+def test_render_ignores_extra_parameters(templates: TemplateStore) -> None:
+    message = templates.render("welcome", name="Alice", place="Bergamo", unused=1)
+
+    assert message == "Hello Alice, welcome to Bergamo!"
+
+
+def test_add_replaces_a_template_with_the_same_name(templates: TemplateStore) -> None:
+    templates.add("welcome", "Hi {name}")
+
+    assert templates.render("welcome", name="Alice") == "Hi Alice"
+
+
+def test_render_unknown_template_raises_key_error(templates: TemplateStore) -> None:
+    with pytest.raises(KeyError, match="goodbye"):
+        templates.render("goodbye", name="Alice")
+
+
+def test_render_missing_parameter_raises_value_error_naming_it(
+    templates: TemplateStore,
+) -> None:
+    with pytest.raises(ValueError, match="place"):
+        templates.render("welcome", name="Alice")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,63 @@
+import pytest
+
+from notify import User
+
+
+def test_preferred_channels_default_to_email() -> None:
+    user = User("alice", email="alice@example.com")
+
+    assert user.preferred_channels == ["email"]
+    assert repr(user.preferred_channels) == "['email']"
+
+
+def test_explicit_none_preferred_channels_default_to_email() -> None:
+    user = User("alice", preferred_channels=None)
+
+    assert user.preferred_channels == ["email"]
+
+
+def test_empty_preferred_channels_stay_empty() -> None:
+    user = User("alice", preferred_channels=[])
+
+    assert user.preferred_channels == []
+
+
+def test_preferred_channels_keep_their_order() -> None:
+    user = User("alice", preferred_channels=["push", "sms", "email"])
+
+    assert user.preferred_channels == ["push", "sms", "email"]
+
+
+def test_preferred_channels_are_isolated_from_the_callers_list() -> None:
+    channels = ["sms"]
+    user = User("alice", preferred_channels=channels)
+
+    channels.append("email")
+
+    assert user.preferred_channels == ["sms"]
+
+
+@pytest.mark.parametrize(
+    ("channel", "expected_address"),
+    [("email", "alice@example.com"), ("sms", "+390351234567"), ("push", "token-1")],
+)
+def test_address_for_returns_the_channels_address(
+    channel: str, expected_address: str
+) -> None:
+    user = User(
+        "alice", email="alice@example.com", phone="+390351234567", push_token="token-1"
+    )
+
+    assert user.address_for(channel) == expected_address
+
+
+def test_address_for_a_channel_the_user_has_no_address_for_is_none() -> None:
+    user = User("alice", email="alice@example.com")
+
+    assert user.address_for("sms") is None
+
+
+def test_address_for_an_unknown_channel_is_none() -> None:
+    user = User("alice", email="alice@example.com")
+
+    assert user.address_for("fax") is None
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,15 @@
+"""Send a message to a user on their preferred channels, with retries and fallback."""
+
+from notify.report import DeliveryReport
+from notify.sender import DeliveryError
+from notify.service import NotificationService
+from notify.templates import TemplateStore
+from notify.user import User
+
+__all__ = [
+    "DeliveryError",
+    "DeliveryReport",
+    "NotificationService",
+    "TemplateStore",
+    "User",
+]
diff -ruN before/notify/report.py after/notify/report.py
--- before/notify/report.py
+++ after/notify/report.py
@@ -0,0 +1,26 @@
+from dataclasses import dataclass
+from typing import NamedTuple
+
+
+class Attempt(NamedTuple):
+    """One send on one channel. It is a plain `(channel, succeeded)` tuple."""
+
+    channel: str
+    succeeded: bool
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """Whether a notification was delivered, on which channel, and each attempt made."""
+
+    delivered: bool
+    channel: str | None
+    attempts: list[Attempt]
+
+    def __post_init__(self) -> None:
+        names_channel = self.channel is not None
+        if self.delivered != names_channel:
+            raise ValueError(
+                "a report names a channel exactly when the message was delivered, "
+                f"got delivered={self.delivered} and channel={self.channel!r}"
+            )
diff -ruN before/notify/sender.py after/notify/sender.py
--- before/notify/sender.py
+++ after/notify/sender.py
@@ -0,0 +1,12 @@
+from typing import Protocol
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it could not deliver a message."""
+
+
+class Sender(Protocol):
+    """Delivers messages on one channel, such as email, SMS or push."""
+
+    def send(self, address: str, message: str) -> None:
+        """Deliver `message` to `address`, or raise DeliveryError."""
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,89 @@
+from __future__ import annotations
+
+import logging
+from collections.abc import Iterator, Mapping
+from dataclasses import dataclass
+
+from notify.report import Attempt, DeliveryReport
+from notify.sender import DeliveryError, Sender
+from notify.templates import TemplateStore
+from notify.user import User
+
+logger = logging.getLogger(__name__)
+
+
+class NotificationService:
+    """Sends a templated message to a user on the first of their preferred channels
+    that accepts it, retrying each channel before falling back to the next."""
+
+    def __init__(
+        self,
+        senders: Mapping[str, Sender],
+        templates: TemplateStore,
+        max_retries: int = 2,
+    ) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must not be negative, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._attempts_per_channel = max_retries + 1
+
+    def notify(
+        self, user: User, template_name: str, /, **params: object
+    ) -> DeliveryReport:
+        """Render the template and deliver it to `user`.
+
+        `user` and `template_name` are positional-only, so templates may use any
+        placeholder name. Template errors (KeyError, ValueError) are raised before
+        anything is sent. A DeliveryError from a sender counts as a failed attempt;
+        any other exception from a sender propagates.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[Attempt] = []
+        for route in self._routes_to(user):
+            route_attempts = self._send_with_retries(route, message)
+            attempts.extend(route_attempts)
+            if route_attempts[-1].succeeded:
+                return DeliveryReport(
+                    delivered=True, channel=route.channel, attempts=attempts
+                )
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _routes_to(self, user: User) -> Iterator[_Route]:
+        """Yield the preferred channels that have a sender and an address, in order."""
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is not None and address is not None:
+                yield _Route(channel, sender, address)
+
+    def _send_with_retries(self, route: _Route, message: str) -> list[Attempt]:
+        """Send on `route` until it succeeds or the attempts per channel run out.
+
+        Never returns an empty list, because there is at least one attempt per channel.
+        """
+        attempts: list[Attempt] = []
+        for _ in range(self._attempts_per_channel):
+            succeeded = route.try_send(message)
+            attempts.append(Attempt(route.channel, succeeded))
+            if succeeded:
+                break
+        return attempts
+
+
+@dataclass(frozen=True)
+class _Route:
+    """One way to reach a user: a channel, its sender and the user's address there."""
+
+    channel: str
+    sender: Sender
+    address: str
+
+    def try_send(self, message: str) -> bool:
+        """Send `message` and tell whether it was delivered."""
+        try:
+            self.sender.send(self.address, message)
+        except DeliveryError as error:
+            logger.warning("Delivery via %s failed: %s", self.channel, error)
+            return False
+        return True
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,28 @@
+class TemplateStore:
+    """Named message templates with `str.format`-style `{param}` placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store `text` under `name`, replacing any template already stored there."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill the template called `name` with `params`.
+
+        `name` is positional-only, so a template may have a `{name}` placeholder.
+        Raises KeyError if no template has that name, and ValueError if the
+        template needs a parameter that was not given.
+        """
+        template = self._templates.get(name)
+        if template is None:
+            raise KeyError(f"unknown template {name!r}")
+        try:
+            return template.format(**params)
+        # A positional placeholder such as `{0}` raises IndexError: render() takes
+        # keyword parameters only, so that parameter can never be given.
+        except (KeyError, IndexError) as missing:
+            raise ValueError(
+                f"cannot render template {name!r}, a parameter is missing: {missing}"
+            ) from missing
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,39 @@
+from enum import StrEnum
+
+
+class Channel(StrEnum):
+    EMAIL = "email"
+    SMS = "sms"
+    PUSH = "push"
+
+
+class User:
+    """A notification recipient: their addresses and preferred channels, in order."""
+
+    def __init__(
+        self,
+        id: str,
+        email: str | None = None,
+        phone: str | None = None,
+        push_token: str | None = None,
+        preferred_channels: list[str] | None = None,
+    ) -> None:
+        self.id = id
+        self.email = email
+        self.phone = phone
+        self.push_token = push_token
+        self.preferred_channels: list[str] = (
+            [Channel.EMAIL] if preferred_channels is None else list(preferred_channels)
+        )
+
+    def address_for(self, channel: str) -> str | None:
+        """Return the user's address on `channel`.
+
+        Returns None when the user has no address there or the channel is unknown.
+        """
+        addresses: dict[str, str | None] = {
+            Channel.EMAIL: self.email,
+            Channel.SMS: self.phone,
+            Channel.PUSH: self.push_token,
+        }
+        return addresses.get(channel)
diff -ruN before/tests/fakes.py after/tests/fakes.py
--- before/tests/fakes.py
+++ after/tests/fakes.py
@@ -0,0 +1,33 @@
+import sys
+
+from notify import DeliveryError
+
+
+class FakeSender:
+    """Records every send, and fails the first `failures` of them with DeliveryError."""
+
+    def __init__(self, failures: int = 0) -> None:
+        self._failures_left = failures
+        self.calls: list[tuple[str, str]] = []
+
+    @classmethod
+    def broken(cls) -> "FakeSender":
+        """A sender whose every send fails."""
+        return cls(failures=sys.maxsize)
+
+    def send(self, address: str, message: str) -> None:
+        self.calls.append((address, message))
+        if self._failures_left > 0:
+            self._failures_left -= 1
+            raise DeliveryError("simulated outage")
+
+
+class CrashingSender:
+    """A sender with a bug: it raises an error that is not a DeliveryError."""
+
+    def __init__(self) -> None:
+        self.calls = 0
+
+    def send(self, address: str, message: str) -> None:
+        self.calls += 1
+        raise RuntimeError("sender bug")
diff -ruN before/tests/test_report.py after/tests/test_report.py
--- before/tests/test_report.py
+++ after/tests/test_report.py
@@ -0,0 +1,11 @@
+import pytest
+
+from notify import DeliveryReport
+
+
+@pytest.mark.parametrize(("delivered", "channel"), [(True, None), (False, "email")])
+def test_rejects_a_channel_that_contradicts_delivered(
+    delivered: bool, channel: str | None
+) -> None:
+    with pytest.raises(ValueError, match="channel"):
+        DeliveryReport(delivered=delivered, channel=channel, attempts=[])
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,209 @@
+from typing import Any
+
+import pytest
+from fakes import CrashingSender, FakeSender
+
+from notify import NotificationService, TemplateStore, User
+
+EMAIL = "alice@example.com"
+PHONE = "+390351234567"
+PUSH_TOKEN = "token-1"
+
+
+@pytest.fixture
+def templates() -> TemplateStore:
+    store = TemplateStore()
+    store.add("welcome", "Hi {name}!")
+    return store
+
+
+def reachable_user(*preferred_channels: str) -> User:
+    """A user with an address on every channel."""
+    return User(
+        "u1",
+        email=EMAIL,
+        phone=PHONE,
+        push_token=PUSH_TOKEN,
+        preferred_channels=list(preferred_channels),
+    )
+
+
+def test_rejects_negative_max_retries(templates: TemplateStore) -> None:
+    with pytest.raises(ValueError, match="max_retries"):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_delivers_on_the_first_preferred_channel(templates: TemplateStore) -> None:
+    service = NotificationService(
+        {"email": FakeSender(), "sms": FakeSender()}, templates
+    )
+
+    report = service.notify(reachable_user("sms", "email"), "welcome", name="Alice")
+
+    assert report.delivered is True
+    assert report.channel == "sms"
+    assert report.attempts == [("sms", True)]
+
+
+def test_sends_the_rendered_message_to_the_channel_address(
+    templates: TemplateStore,
+) -> None:
+    sms = FakeSender()
+    service = NotificationService({"sms": sms}, templates)
+
+    service.notify(reachable_user("sms"), "welcome", name="Alice")
+
+    assert sms.calls == [(PHONE, "Hi Alice!")]
+
+
+def test_accepts_placeholders_named_like_its_own_parameters() -> None:
+    store = TemplateStore()
+    store.add("greeting", "{user} sent you {template_name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, store)
+
+    service.notify(
+        reachable_user("email"), "greeting", user="Bob", template_name="a card"
+    )
+
+    assert email.calls == [(EMAIL, "Bob sent you a card")]
+
+
+def test_retries_a_failing_channel_until_it_succeeds(templates: TemplateStore) -> None:
+    service = NotificationService(
+        {"email": FakeSender(failures=2)}, templates, max_retries=2
+    )
+
+    report = service.notify(reachable_user("email"), "welcome", name="Alice")
+
+    assert report.delivered is True
+    assert report.attempts == [("email", False), ("email", False), ("email", True)]
+
+
+def test_falls_back_to_the_next_channel_once_retries_run_out(
+    templates: TemplateStore,
+) -> None:
+    senders = {"email": FakeSender.broken(), "push": FakeSender()}
+    service = NotificationService(senders, templates, max_retries=1)
+
+    report = service.notify(reachable_user("email", "push"), "welcome", name="Alice")
+
+    assert report.channel == "push"
+    assert report.attempts == [("email", False), ("email", False), ("push", True)]
+
+
+def test_allows_two_retries_by_default(templates: TemplateStore) -> None:
+    service = NotificationService({"email": FakeSender.broken()}, templates)
+
+    report = service.notify(reachable_user("email"), "welcome", name="Alice")
+
+    assert report.attempts == [("email", False)] * 3
+
+
+def test_zero_retries_tries_each_channel_once(templates: TemplateStore) -> None:
+    senders = {"email": FakeSender.broken(), "sms": FakeSender.broken()}
+    service = NotificationService(senders, templates, max_retries=0)
+
+    report = service.notify(reachable_user("email", "sms"), "welcome", name="Alice")
+
+    assert report.attempts == [("email", False), ("sms", False)]
+
+
+def test_stops_at_the_first_successful_send(templates: TemplateStore) -> None:
+    sms = FakeSender()
+    service = NotificationService(
+        {"email": FakeSender(failures=1), "sms": sms}, templates
+    )
+
+    service.notify(reachable_user("email", "sms"), "welcome", name="Alice")
+
+    assert sms.calls == []
+
+
+def test_reports_failure_when_every_channel_fails(templates: TemplateStore) -> None:
+    senders = {"email": FakeSender.broken(), "sms": FakeSender.broken()}
+    service = NotificationService(senders, templates, max_retries=0)
+
+    report = service.notify(reachable_user("email", "sms"), "welcome", name="Alice")
+
+    assert report.delivered is False
+    assert report.channel is None
+
+
+def test_skips_a_channel_without_a_sender(templates: TemplateStore) -> None:
+    service = NotificationService({"email": FakeSender()}, templates)
+
+    report = service.notify(reachable_user("sms", "email"), "welcome", name="Alice")
+
+    assert report.attempts == [("email", True)]
+
+
+def test_skips_a_channel_the_user_has_no_address_for(templates: TemplateStore) -> None:
+    sms = FakeSender()
+    service = NotificationService({"sms": sms, "email": FakeSender()}, templates)
+    user = User("u1", email=EMAIL, preferred_channels=["sms", "email"])
+
+    report = service.notify(user, "welcome", name="Alice")
+
+    assert report.attempts == [("email", True)]
+    assert sms.calls == []
+
+
+def test_skips_a_channel_with_an_unknown_name(templates: TemplateStore) -> None:
+    fax = FakeSender()
+    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)
+
+    report = service.notify(reachable_user("fax", "email"), "welcome", name="Alice")
+
+    assert report.attempts == [("email", True)]
+    assert fax.calls == []
+
+
+def test_reports_no_attempts_when_no_channel_is_usable(
+    templates: TemplateStore,
+) -> None:
+    service = NotificationService({"email": FakeSender()}, templates)
+
+    report = service.notify(User("u1"), "welcome", name="Alice")
+
+    assert report.delivered is False
+    assert report.attempts == []
+
+
+@pytest.mark.parametrize(
+    ("template_name", "params", "expected_error"),
+    [("unknown", {"name": "Alice"}, KeyError), ("welcome", {}, ValueError)],
+)
+def test_raises_template_errors_before_sending(
+    templates: TemplateStore,
+    template_name: str,
+    params: dict[str, Any],
+    expected_error: type[Exception],
+) -> None:
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(expected_error):
+        service.notify(reachable_user("email"), template_name, **params)
+    assert email.calls == []
+
+
+def test_propagates_sender_errors_other_than_delivery_error(
+    templates: TemplateStore,
+) -> None:
+    crashing = CrashingSender()
+    service = NotificationService({"email": crashing, "sms": FakeSender()}, templates)
+
+    with pytest.raises(RuntimeError, match="sender bug"):
+        service.notify(reachable_user("email", "sms"), "welcome", name="Alice")
+    assert crashing.calls == 1
+
+
+def test_logs_why_a_delivery_attempt_failed(
+    templates: TemplateStore, caplog: pytest.LogCaptureFixture
+) -> None:
+    service = NotificationService({"email": FakeSender(failures=1)}, templates)
+
+    service.notify(reachable_user("email"), "welcome", name="Alice")
+
+    assert "Delivery via email failed: simulated outage" in caplog.messages
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,44 @@
+import pytest
+
+from notify import TemplateStore
+
+
+def test_render_fills_placeholders() -> None:
+    store = TemplateStore()
+    store.add("welcome", "Hi {name}, your code is {code}.")
+
+    assert (
+        store.render("welcome", name="Alice", code=42) == "Hi Alice, your code is 42."
+    )
+
+
+def test_add_replaces_a_template_with_the_same_name() -> None:
+    store = TemplateStore()
+    store.add("welcome", "Hi {name}!")
+
+    store.add("welcome", "Welcome, {name}.")
+
+    assert store.render("welcome", name="Alice") == "Welcome, Alice."
+
+
+def test_render_rejects_an_unknown_template() -> None:
+    store = TemplateStore()
+
+    with pytest.raises(KeyError, match="welcome"):
+        store.render("welcome")
+
+
+def test_render_rejects_a_missing_parameter() -> None:
+    store = TemplateStore()
+    store.add("welcome", "Hi {name}!")
+
+    with pytest.raises(ValueError, match="name"):
+        store.render("welcome", nickname="Ali")
+
+
+def test_render_treats_a_positional_placeholder_as_a_missing_parameter() -> None:
+    store = TemplateStore()
+    store.add("welcome", "Hi {0}!")
+
+    with pytest.raises(ValueError, match="parameter is missing"):
+        store.render("welcome", name="Alice")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,53 @@
+from typing import Any
+
+import pytest
+
+from notify import User
+
+
+@pytest.mark.parametrize("channels_kwarg", [{}, {"preferred_channels": None}])
+def test_preferred_channels_default_to_email(channels_kwarg: dict[str, Any]) -> None:
+    user = User("u1", **channels_kwarg)
+
+    assert user.preferred_channels == ["email"]
+
+
+def test_empty_preferred_channels_stay_empty() -> None:
+    user = User("u1", preferred_channels=[])
+
+    assert user.preferred_channels == []
+
+
+def test_preferred_channels_are_not_shared_with_the_caller() -> None:
+    channels = ["sms"]
+    user = User("u1", preferred_channels=channels)
+
+    channels.append("push")
+
+    assert user.preferred_channels == ["sms"]
+
+
+@pytest.mark.parametrize(
+    ("channel", "expected_address"),
+    [("email", "alice@example.com"), ("sms", "+390351234567"), ("push", "token-1")],
+)
+def test_address_for_returns_the_address_of_each_channel(
+    channel: str, expected_address: str
+) -> None:
+    user = User(
+        "u1", email="alice@example.com", phone="+390351234567", push_token="token-1"
+    )
+
+    assert user.address_for(channel) == expected_address
+
+
+def test_address_for_returns_none_when_the_user_has_no_address_there() -> None:
+    user = User("u1", email="alice@example.com")
+
+    assert user.address_for("sms") is None
+
+
+def test_address_for_returns_none_for_an_unknown_channel() -> None:
+    user = User("u1", email="alice@example.com")
+
+    assert user.address_for("fax") is None
```

### Implementation 2

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,19 @@
+"""Send templated messages to users over their preferred channels.
+
+Senders for each channel are injected; a sender raises ``DeliveryError`` when
+delivery fails, which triggers retries and then fallback to the next channel.
+"""
+
+from notify.errors import DeliveryError
+from notify.service import DeliveryReport, NotificationService, Sender
+from notify.templates import TemplateStore
+from notify.user import User
+
+__all__ = [
+    "DeliveryError",
+    "DeliveryReport",
+    "NotificationService",
+    "Sender",
+    "TemplateStore",
+    "User",
+]
diff -ruN before/notify/errors.py after/notify/errors.py
--- before/notify/errors.py
+++ after/notify/errors.py
@@ -0,0 +1,10 @@
+"""Exceptions raised by the notify package and by its senders."""
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when a message could not be delivered.
+
+    The notification service treats this error as retryable: it retries the
+    same channel and then falls back to the next one. Any other exception
+    raised by a sender is treated as a bug and propagates to the caller.
+    """
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,108 @@
+"""Delivering a rendered message over a user's preferred channels."""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Any, Mapping, Optional, Protocol
+
+from notify.errors import DeliveryError
+from notify.templates import TemplateStore
+from notify.user import User
+
+
+class Sender(Protocol):
+    """Delivers a message to an address on one channel.
+
+    Implementations raise ``DeliveryError`` when delivery fails.
+    """
+
+    def send(self, address: str, message: str) -> None: ...
+
+
+@dataclass
+class DeliveryReport:
+    """The outcome of one ``NotificationService.notify`` call.
+
+    ``attempts`` lists every send attempt as ``(channel, succeeded)``, in the
+    order the attempts happened.
+    """
+
+    delivered: bool
+    channel: Optional[str] = None
+    attempts: list[tuple[str, bool]] = field(default_factory=list)
+
+
+class NotificationService:
+    """Sends templated messages to users, with retries and channel fallback."""
+
+    def __init__(
+        self,
+        senders: Mapping[str, Sender],
+        templates: TemplateStore,
+        max_retries: int = 2,
+    ) -> None:
+        """
+        Args:
+            senders: channel name -> sender for that channel.
+            templates: where messages are rendered from.
+            max_retries: extra attempts on a channel after its first failure.
+
+        Raises:
+            ValueError: ``max_retries`` is negative.
+        """
+        if max_retries < 0:
+            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._max_retries = max_retries
+
+    def notify(
+        self, user: User, template_name: str, /, **params: Any
+    ) -> DeliveryReport:
+        """Render ``template_name`` and deliver it to ``user``.
+
+        ``user`` and ``template_name`` are positional-only so that templates
+        can use placeholders with those names.
+
+        Channels are tried in the user's order of preference. A channel is
+        skipped, with no attempt recorded, when it has no sender, the user has
+        no address for it, or its name is unknown. A channel that keeps
+        raising ``DeliveryError`` is tried ``1 + max_retries`` times before
+        falling back to the next one. Delivery stops at the first success.
+
+        Raises:
+            KeyError, ValueError: the template is unknown or a parameter is
+                missing; raised before anything is sent.
+            Exception: anything other than ``DeliveryError`` raised by a sender.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is None or address is None:
+                continue
+            outcomes = self._send_with_retries(sender, address, message)
+            attempts.extend((channel, succeeded) for succeeded in outcomes)
+            if outcomes[-1]:
+                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _send_with_retries(
+        self, sender: Sender, address: str, message: str
+    ) -> list[bool]:
+        """Send until it succeeds or the retries run out.
+
+        Returns the outcome of each attempt, in order. The list is never
+        empty, and only its last entry can be ``True``.
+        """
+        outcomes: list[bool] = []
+        for _ in range(1 + self._max_retries):
+            try:
+                sender.send(address, message)
+            except DeliveryError:
+                outcomes.append(False)
+            else:
+                outcomes.append(True)
+                break
+        return outcomes
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,38 @@
+"""Named message templates using ``str.format`` placeholders."""
+
+from __future__ import annotations
+
+from typing import Any
+
+
+class TemplateStore:
+    """Stores message templates by name and renders them with parameters."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store ``text`` under ``name``, replacing any existing template."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: Any) -> str:
+        """Fill the template ``name`` with ``params``.
+
+        ``name`` is positional-only so that templates can use a ``{name}``
+        placeholder.
+
+        Raises:
+            KeyError: no template is stored under ``name``.
+            ValueError: the template needs a parameter that was not given.
+        """
+        if name not in self._templates:
+            raise KeyError(f"Unknown template: {name!r}")
+        text = self._templates[name]
+        try:
+            return text.format(**params)
+        except (KeyError, IndexError) as missing:
+            # str.format raises KeyError for a missing {name} and IndexError
+            # for a positional {0}, which can never be filled by keywords.
+            raise ValueError(
+                f"Template {name!r} is missing a parameter: {missing}"
+            ) from missing
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,53 @@
+"""The recipient of a notification and the addresses it can be reached at."""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any, Optional
+
+DEFAULT_CHANNELS = ("email",)
+
+# Channel name -> name of the User attribute holding the address for it.
+_ADDRESS_FIELD_BY_CHANNEL = {
+    "email": "email",
+    "sms": "phone",
+    "push": "push_token",
+}
+
+
+@dataclass
+class User:
+    """A user who can be notified on one or more channels.
+
+    ``preferred_channels`` is the ordered list of channels to try. It defaults
+    to ``["email"]`` and is copied, so later changes to the list passed in do
+    not affect the user.
+    """
+
+    id: Any
+    email: Optional[str] = None
+    phone: Optional[str] = None
+    push_token: Optional[str] = None
+    preferred_channels: Optional[list[str]] = None
+
+    def __post_init__(self) -> None:
+        if self.preferred_channels is None:
+            self.preferred_channels = list(DEFAULT_CHANNELS)
+        elif isinstance(self.preferred_channels, str):
+            raise TypeError(
+                "preferred_channels must be a list of channel names, "
+                f"not the string {self.preferred_channels!r}"
+            )
+        else:
+            self.preferred_channels = list(self.preferred_channels)
+
+    def address_for(self, channel: str) -> Optional[str]:
+        """Return the user's address for ``channel``.
+
+        Returns ``None`` when the channel name is unknown or when the user has
+        no (or an empty) address for it.
+        """
+        field_name = _ADDRESS_FIELD_BY_CHANNEL.get(channel)
+        if field_name is None:
+            return None
+        return getattr(self, field_name) or None
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,261 @@
+import pytest
+
+from notify import (
+    DeliveryError,
+    DeliveryReport,
+    NotificationService,
+    TemplateStore,
+    User,
+)
+
+
+class FakeSender:
+    """Records calls; fails the first ``failures`` sends with DeliveryError."""
+
+    def __init__(self, failures=0):
+        self.failures = failures
+        self.calls = []
+
+    def send(self, address, message):
+        self.calls.append((address, message))
+        if len(self.calls) <= self.failures:
+            raise DeliveryError(f"send #{len(self.calls)} failed")
+
+
+class AlwaysFails(FakeSender):
+    def __init__(self):
+        super().__init__(failures=float("inf"))
+
+
+class Explodes:
+    def send(self, address, message):
+        raise RuntimeError("bug in sender")
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("hi", "Hi {name}")
+    return store
+
+
+def full_user(channels):
+    return User(
+        id=7,
+        email="u@example.com",
+        phone="+39000",
+        push_token="tok",
+        preferred_channels=channels,
+    )
+
+
+def test_max_retries_must_not_be_negative(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_zero_retries_is_allowed(templates):
+    NotificationService({}, templates, max_retries=0)
+
+
+def test_delivers_on_first_channel(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(User(id=1, email="u@example.com"), "hi", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=True, channel="email", attempts=[("email", True)]
+    )
+    assert email.calls == [("u@example.com", "Hi Ada")]
+
+
+def test_sends_to_the_address_of_each_channel(templates):
+    sms, push = AlwaysFails(), FakeSender()
+    service = NotificationService({"sms": sms, "push": push}, templates, max_retries=0)
+
+    service.notify(full_user(["sms", "push"]), "hi", name="Ada")
+
+    assert sms.calls == [("+39000", "Hi Ada")]
+    assert push.calls == [("tok", "Hi Ada")]
+
+
+def test_retries_same_channel_until_success(templates):
+    email = FakeSender(failures=2)
+    service = NotificationService({"email": email}, templates, max_retries=2)
+
+    report = service.notify(full_user(["email", "sms"]), "hi", name="Ada")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", False), ("email", False), ("email", True)]
+
+
+def test_falls_back_after_retries_are_exhausted(templates):
+    email, sms = AlwaysFails(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)
+
+    report = service.notify(full_user(["email", "sms"]), "hi", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=True,
+        channel="sms",
+        attempts=[("email", False), ("email", False), ("sms", True)],
+    )
+    assert len(email.calls) == 2
+
+
+def test_default_max_retries_is_two(templates):
+    email = AlwaysFails()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(full_user(["email"]), "hi", name="Ada")
+
+    assert len(email.calls) == 3
+    assert report.attempts == [("email", False)] * 3
+
+
+def test_reports_failure_when_every_channel_fails(templates):
+    service = NotificationService(
+        {"email": AlwaysFails(), "push": AlwaysFails()}, templates, max_retries=0
+    )
+
+    report = service.notify(full_user(["email", "push"]), "hi", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=False,
+        channel=None,
+        attempts=[("email", False), ("push", False)],
+    )
+
+
+def test_stops_at_first_success(templates):
+    email, sms = FakeSender(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    service.notify(full_user(["email", "sms"]), "hi", name="Ada")
+
+    assert sms.calls == []
+
+
+def test_follows_preferred_channel_order(templates):
+    email, push = FakeSender(), FakeSender()
+    service = NotificationService({"email": email, "push": push}, templates)
+
+    report = service.notify(full_user(["push", "email"]), "hi", name="Ada")
+
+    assert report.channel == "push"
+    assert email.calls == []
+
+
+def test_skips_channel_without_sender(templates):
+    service = NotificationService({"email": FakeSender()}, templates)
+
+    report = service.notify(full_user(["sms", "email"]), "hi", name="Ada")
+
+    assert report.attempts == [("email", True)]
+
+
+def test_skips_channel_without_address(templates):
+    sms = FakeSender()
+    service = NotificationService({"sms": sms, "email": FakeSender()}, templates)
+    user = User(id=1, email="u@example.com", preferred_channels=["sms", "email"])
+
+    report = service.notify(user, "hi", name="Ada")
+
+    assert report.attempts == [("email", True)]
+    assert sms.calls == []
+
+
+def test_skips_unknown_channel_even_with_a_sender(templates):
+    fax = FakeSender()
+    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)
+
+    report = service.notify(full_user(["fax", "email"]), "hi", name="Ada")
+
+    assert report.attempts == [("email", True)]
+    assert fax.calls == []
+
+
+def test_no_usable_channel_gives_empty_failed_report(templates):
+    service = NotificationService({}, templates)
+
+    report = service.notify(full_user(["email", "sms"]), "hi", name="Ada")
+
+    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
+
+
+def test_unknown_template_propagates_before_sending(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(KeyError):
+        service.notify(full_user(["email"]), "nope")
+    assert email.calls == []
+
+
+def test_missing_parameter_propagates_before_sending(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(ValueError):
+        service.notify(full_user(["email"]), "hi")
+    assert email.calls == []
+
+
+def test_template_errors_raise_even_with_no_usable_channel(templates):
+    service = NotificationService({}, templates)
+
+    with pytest.raises(ValueError):
+        service.notify(User(id=1), "hi")
+
+
+def test_other_sender_exceptions_propagate_without_retry(templates):
+    sms = FakeSender()
+    service = NotificationService({"email": Explodes(), "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError):
+        service.notify(full_user(["email", "sms"]), "hi", name="Ada")
+    assert sms.calls == []
+
+
+def test_delivery_error_subclasses_are_retried(templates):
+    class Timeout(DeliveryError):
+        pass
+
+    class FlakySender:
+        def __init__(self):
+            self.calls = 0
+
+        def send(self, address, message):
+            self.calls += 1
+            if self.calls == 1:
+                raise Timeout()
+
+    service = NotificationService({"email": FlakySender()}, templates)
+
+    report = service.notify(full_user(["email"]), "hi", name="Ada")
+
+    assert report.attempts == [("email", False), ("email", True)]
+
+
+def test_templates_may_use_user_and_template_name_placeholders(templates):
+    templates.add("meta", "{user} got {template_name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(full_user(["email"]), "meta", user="Ada", template_name="meta")
+
+    assert email.calls == [("u@example.com", "Ada got meta")]
+
+
+def test_each_notify_call_gets_its_own_report(templates):
+    service = NotificationService({"email": FakeSender()}, templates)
+    user = full_user(["email"])
+
+    first = service.notify(user, "hi", name="Ada")
+    second = service.notify(user, "hi", name="Bob")
+
+    assert first.attempts == [("email", True)]
+    assert second.attempts == [("email", True)]
+    assert first.attempts is not second.attempts
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,56 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def store():
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}, welcome to {place}!")
+    return store
+
+
+def test_render_fills_placeholders(store):
+    assert store.render("welcome", name="Ada", place="Bergamo") == (
+        "Hello Ada, welcome to Bergamo!"
+    )
+
+
+def test_name_placeholder_does_not_clash_with_template_name():
+    store = TemplateStore()
+    store.add("greet", "Hi {name}")
+    assert store.render("greet", name="Ada") == "Hi Ada"
+
+
+def test_extra_parameters_are_ignored(store):
+    assert store.render("welcome", name="Ada", place="Rome", unused=1) == (
+        "Hello Ada, welcome to Rome!"
+    )
+
+
+def test_adding_a_template_again_replaces_it(store):
+    store.add("welcome", "Hi {name}")
+    assert store.render("welcome", name="Ada") == "Hi Ada"
+
+
+def test_unknown_template_raises_key_error(store):
+    with pytest.raises(KeyError):
+        store.render("missing")
+
+
+def test_missing_parameter_raises_value_error(store):
+    with pytest.raises(ValueError, match="name"):
+        store.render("welcome", place="Rome")
+
+
+def test_missing_parameter_is_not_a_key_error(store):
+    with pytest.raises(ValueError) as excinfo:
+        store.render("welcome", place="Rome")
+    assert not isinstance(excinfo.value, KeyError)
+
+
+def test_positional_placeholder_raises_value_error():
+    store = TemplateStore()
+    store.add("positional", "Code {0}")
+    with pytest.raises(ValueError):
+        store.render("positional", code=1)
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,43 @@
+import pytest
+
+from notify import User
+
+
+def test_preferred_channels_default_to_email():
+    assert User(id=1).preferred_channels == ["email"]
+
+
+def test_default_channels_are_not_shared_between_users():
+    first, second = User(id=1), User(id=2)
+    first.preferred_channels.append("sms")
+    assert second.preferred_channels == ["email"]
+
+
+def test_preferred_channels_are_copied():
+    channels = ["sms", "email"]
+    user = User(id=1, preferred_channels=channels)
+    channels.append("push")
+    assert user.preferred_channels == ["sms", "email"]
+
+
+def test_a_bare_string_is_rejected_as_preferred_channels():
+    with pytest.raises(TypeError):
+        User(id=1, preferred_channels="email")
+
+
+@pytest.mark.parametrize(
+    ("channel", "expected"),
+    [("email", "a@b.c"), ("sms", "+39123"), ("push", "tok-1")],
+)
+def test_address_for_known_channels(channel, expected):
+    user = User(id=1, email="a@b.c", phone="+39123", push_token="tok-1")
+    assert user.address_for(channel) == expected
+
+
+@pytest.mark.parametrize("channel", ["email", "sms", "push", "fax"])
+def test_address_for_returns_none_when_missing_or_unknown(channel):
+    assert User(id=1).address_for(channel) is None
+
+
+def test_empty_address_counts_as_missing():
+    assert User(id=1, email="").address_for("email") is None
```

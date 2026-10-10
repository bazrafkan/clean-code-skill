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
@@ -0,0 +1,5 @@
+"""Exceptions raised by the notify package."""
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it could not deliver a message."""
diff -ruN before/notify/report.py after/notify/report.py
--- before/notify/report.py
+++ after/notify/report.py
@@ -0,0 +1,12 @@
+"""The outcome of a single notify() call."""
+
+from dataclasses import dataclass, field
+
+
+@dataclass
+class DeliveryReport:
+    delivered: bool
+    # The channel that delivered the message, or None if none did.
+    channel: str | None
+    # One (channel, succeeded) entry per send attempt, in the order made.
+    attempts: list[tuple[str, bool]] = field(default_factory=list)
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,80 @@
+"""Delivers a rendered template to a user, with retries and channel fallback."""
+
+from collections.abc import Mapping
+from typing import Protocol
+
+from .errors import DeliveryError
+from .report import DeliveryReport
+from .templates import TemplateStore
+from .user import User
+
+
+class Sender(Protocol):
+    def send(self, address: str, message: str) -> None:
+        """Deliver `message` to `address`, raising DeliveryError on failure."""
+
+
+class NotificationService:
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
+    def notify(
+        self, user: User, template_name: str, /, **params: object
+    ) -> DeliveryReport:
+        """Send the rendered template on the user's first channel that works.
+
+        `user` and `template_name` are positional-only so templates may use
+        placeholders with those names. Template errors are raised before
+        anything is sent. A channel is
+        skipped, with no attempt recorded, when it has no sender, the user
+        has no address for it, or its name is unknown. Each usable channel
+        gets one attempt plus up to `max_retries` retries on DeliveryError
+        before falling back to the next one. Any other exception from a
+        sender propagates.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
+        tried: set[str] = set()
+
+        for channel in user.preferred_channels:
+            # A repeated channel would exceed its retry budget, so try it once.
+            if channel in tried:
+                continue
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is None or address is None:
+                continue
+            tried.add(channel)
+
+            if self._send_with_retries(sender, channel, address, message, attempts):
+                return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _send_with_retries(
+        self,
+        sender: Sender,
+        channel: str,
+        address: str,
+        message: str,
+        attempts: list[tuple[str, bool]],
+    ) -> bool:
+        """Try one channel, recording each attempt. Return True on success."""
+        for _ in range(1 + self._max_retries):
+            try:
+                sender.send(address, message)
+            except DeliveryError:
+                attempts.append((channel, False))
+            else:
+                attempts.append((channel, True))
+                return True
+        return False
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,29 @@
+"""Named message templates with `{param}` placeholders."""
+
+
+class TemplateStore:
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store `text` under `name`, replacing any template already there."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill template `name` with `params`.
+
+        `name` is positional-only so a template can use a `{name}` placeholder.
+        Raises KeyError if no template is called `name`, and ValueError if
+        the template needs a parameter that was not given.
+        """
+        try:
+            template = self._templates[name]
+        except KeyError:
+            raise KeyError(f"unknown template: {name!r}") from None
+
+        try:
+            return template.format_map(params)
+        except KeyError as exc:
+            raise ValueError(
+                f"template {name!r} is missing parameter {exc.args[0]!r}"
+            ) from exc
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,36 @@
+"""The recipient of a notification and the channels they can be reached on."""
+
+from dataclasses import dataclass
+
+# Each known channel and the User attribute that holds its address.
+CHANNEL_ADDRESS_FIELDS = {
+    "email": "email",
+    "sms": "phone",
+    "push": "push_token",
+}
+
+DEFAULT_CHANNELS = ("email",)
+
+
+@dataclass
+class User:
+    id: str
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    # Ordered from most to least preferred. None means DEFAULT_CHANNELS.
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        if self.preferred_channels is None:
+            self.preferred_channels = list(DEFAULT_CHANNELS)
+        else:
+            # Copy so later changes to the caller's list do not leak in.
+            self.preferred_channels = list(self.preferred_channels)
+
+    def address_for(self, channel: str) -> str | None:
+        """Return the address for `channel`, or None if it is unknown or unset."""
+        field_name = CHANNEL_ADDRESS_FIELDS.get(channel)
+        if field_name is None:
+            return None
+        return getattr(self, field_name) or None
diff -ruN before/tests/test_notify.py after/tests/test_notify.py
--- before/tests/test_notify.py
+++ after/tests/test_notify.py
@@ -0,0 +1,288 @@
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+
+class FakeSender:
+    """Fails the first `failures` sends with DeliveryError, then succeeds."""
+
+    def __init__(self, failures=0, error=None):
+        self.failures = failures
+        self.error = error
+        self.sent = []
+
+    def send(self, address, message):
+        self.sent.append((address, message))
+        if self.error is not None:
+            raise self.error
+        if len(self.sent) <= self.failures:
+            raise DeliveryError("boom")
+
+
+ALWAYS_FAILS = 10**6
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("welcome", "Hi {name}!")
+    return store
+
+
+def full_user(channels):
+    return User(
+        id="u1",
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
+    assert User(id="u1").preferred_channels == ["email"]
+
+
+def test_user_copies_preferred_channels():
+    channels = ["sms"]
+    user = User(id="u1", preferred_channels=channels)
+    channels.append("push")
+    assert user.preferred_channels == ["sms"]
+
+
+def test_explicit_empty_channels_stay_empty():
+    assert User(id="u1", preferred_channels=[]).preferred_channels == []
+
+
+# --- TemplateStore ------------------------------------------------------------
+
+
+def test_render_fills_placeholders(templates):
+    assert templates.render("welcome", name="Ada") == "Hi Ada!"
+
+
+def test_render_unknown_template_raises_key_error(templates):
+    with pytest.raises(KeyError):
+        templates.render("nope")
+
+
+def test_render_missing_param_raises_value_error(templates):
+    with pytest.raises(ValueError, match="name"):
+        templates.render("welcome")
+
+
+def test_render_missing_param_is_not_a_key_error(templates):
+    with pytest.raises(ValueError) as info:
+        templates.render("welcome")
+    assert not isinstance(info.value, KeyError)
+
+
+def test_add_replaces_existing_template(templates):
+    templates.add("welcome", "Hello {name}")
+    assert templates.render("welcome", name="Ada") == "Hello Ada"
+
+
+# --- NotificationService construction -------------------------------------------
+
+
+def test_negative_max_retries_rejected(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_zero_max_retries_allowed(templates):
+    NotificationService({}, templates, max_retries=0)
+
+
+# --- notify -----------------------------------------------------------------------
+
+
+def test_delivers_on_first_channel(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(User(id="u1", email="a@example.com"), "welcome", name="Ada")
+
+    assert report == DeliveryReport(True, "email", [("email", True)])
+    assert email.sent == [("a@example.com", "Hi Ada!")]
+
+
+def test_retries_same_channel_then_succeeds(templates):
+    email = FakeSender(failures=2)
+    service = NotificationService({"email": email}, templates, max_retries=2)
+
+    report = service.notify(full_user(["email"]), "welcome", name="Ada")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", False), ("email", False), ("email", True)]
+
+
+def test_falls_back_after_retries_exhausted(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=1)
+
+    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert report.channel == "sms"
+    assert report.attempts == [("email", False), ("email", False), ("sms", True)]
+    assert sms.sent == [("+391234", "Hi Ada!")]
+
+
+def test_zero_retries_means_single_attempt_per_channel(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    push = FakeSender(failures=ALWAYS_FAILS)
+    service = NotificationService({"email": email, "push": push}, templates, max_retries=0)
+
+    report = service.notify(full_user(["email", "push"]), "welcome", name="Ada")
+
+    assert report == DeliveryReport(False, None, [("email", False), ("push", False)])
+
+
+def test_all_channels_fail(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(full_user(["email"]), "welcome", name="Ada")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == [("email", False)] * 3
+
+
+def test_stops_at_first_success(templates):
+    email = FakeSender()
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    service.notify(full_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert sms.sent == []
+
+
+def test_follows_preferred_order(templates):
+    email = FakeSender()
+    push = FakeSender()
+    service = NotificationService({"email": email, "push": push}, templates)
+
+    report = service.notify(full_user(["push", "email"]), "welcome", name="Ada")
+
+    assert report.channel == "push"
+    assert push.sent == [("tok", "Hi Ada!")]
+    assert email.sent == []
+
+
+@pytest.mark.parametrize(
+    "senders_keys, user_kwargs, channels",
+    [
+        # no sender configured for sms
+        (["email"], {"phone": "+391234"}, ["sms", "email"]),
+        # user has no phone number
+        (["sms", "email"], {}, ["sms", "email"]),
+        # unknown channel name, even with a sender registered under it
+        (["fax", "email"], {}, ["fax", "email"]),
+    ],
+)
+def test_unusable_channels_are_skipped_without_attempt(
+    templates, senders_keys, user_kwargs, channels
+):
+    senders = {name: FakeSender() for name in senders_keys}
+    user = User(id="u1", email="a@example.com", preferred_channels=channels, **user_kwargs)
+    service = NotificationService(senders, templates)
+
+    report = service.notify(user, "welcome", name="Ada")
+
+    assert report == DeliveryReport(True, "email", [("email", True)])
+    for name, sender in senders.items():
+        if name != "email":
+            assert sender.sent == []
+
+
+def test_empty_address_counts_as_missing(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(User(id="u1", email=""), "welcome", name="Ada")
+
+    assert report == DeliveryReport(False, None, [])
+    assert email.sent == []
+
+
+def test_no_usable_channel_gives_empty_report(templates):
+    service = NotificationService({}, templates)
+
+    report = service.notify(full_user(["email", "sms", "push"]), "welcome", name="Ada")
+
+    assert report == DeliveryReport(False, None, [])
+
+
+def test_repeated_channel_is_not_retried_again(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    service = NotificationService({"email": email}, templates, max_retries=1)
+
+    report = service.notify(full_user(["email", "email"]), "welcome", name="Ada")
+
+    assert report.attempts == [("email", False), ("email", False)]
+
+
+def test_template_errors_raised_before_sending(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+    user = full_user(["email"])
+
+    with pytest.raises(KeyError):
+        service.notify(user, "missing-template")
+    with pytest.raises(ValueError):
+        service.notify(user, "welcome")
+    assert email.sent == []
+
+
+def test_other_exceptions_propagate_without_retry(templates):
+    email = FakeSender(error=RuntimeError("bug"))
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError):
+        service.notify(full_user(["email", "sms"]), "welcome", name="Ada")
+    assert len(email.sent) == 1
+    assert sms.sent == []
+
+
+def test_delivery_error_subclass_is_retried(templates):
+    class Timeout(DeliveryError):
+        pass
+
+    email = FakeSender(error=Timeout("slow"))
+    service = NotificationService({"email": email}, templates, max_retries=1)
+
+    report = service.notify(full_user(["email"]), "welcome", name="Ada")
+
+    assert report.attempts == [("email", False), ("email", False)]
+
+
+def test_placeholders_may_share_names_with_method_parameters():
+    store = TemplateStore()
+    store.add("t", "{name}/{user}/{template_name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, store)
+
+    service.notify(full_user(["email"]), "t", name="n", user="u", template_name="tn")
+
+    assert email.sent == [("a@example.com", "n/u/tn")]
+
+
+def test_each_call_gets_a_fresh_report(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+    user = full_user(["email"])
+
+    first = service.notify(user, "welcome", name="Ada")
+    second = service.notify(user, "welcome", name="Bob")
+
+    assert first.attempts == [("email", True)]
+    assert second.attempts == [("email", True)]
+    assert first.attempts is not second.attempts
```

### Implementation 2

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,5 @@
+from .service import DeliveryError, DeliveryReport, NotificationService
+from .templates import TemplateStore
+from .user import User
+
+__all__ = ["DeliveryError", "DeliveryReport", "NotificationService", "TemplateStore", "User"]
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,59 @@
+from collections.abc import Iterator, Mapping
+from dataclasses import dataclass
+from typing import Protocol
+
+from .templates import TemplateStore
+from .user import User
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it fails to deliver a message."""
+
+
+class Sender(Protocol):
+    def send(self, address: str, message: str) -> None:
+        """Deliver `message` to `address`, raising DeliveryError on failure."""
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    delivered: bool
+    channel: str | None
+    attempts: list[tuple[str, bool]]
+
+
+class NotificationService:
+    """Sends a message through a user's preferred channels, retrying each one before falling back to the next."""
+
+    def __init__(self, senders: Mapping[str, Sender], templates: TemplateStore, max_retries: int = 2) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must not be negative, got {max_retries}")
+        self._senders = senders
+        self._templates = templates
+        self._attempts_per_channel = 1 + max_retries
+
+    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
+        for channel, sender, address in self._reachable_channels(user):
+            for _ in range(self._attempts_per_channel):
+                succeeded = _try_send(sender, address, message)
+                attempts.append((channel, succeeded))
+                if succeeded:
+                    return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _reachable_channels(self, user: User) -> Iterator[tuple[str, Sender, str]]:
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is not None and address is not None:
+                yield channel, sender, address
+
+
+def _try_send(sender: Sender, address: str, message: str) -> bool:
+    try:
+        sender.send(address, message)
+    except DeliveryError:
+        return False
+    return True
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,17 @@
+class TemplateStore:
+    """Named message templates with `str.format`-style `{param}` placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill template `name`. Raises KeyError if it is unknown, ValueError if a parameter is missing."""
+        template = self._templates[name]
+        try:
+            return template.format(**params)
+        except KeyError as error:
+            missing_param = error.args[0]
+            raise ValueError(f"template {name!r} needs parameter {missing_param!r}") from error
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,19 @@
+from dataclasses import dataclass
+
+
+@dataclass
+class User:
+    id: str
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        if self.preferred_channels is None:
+            self.preferred_channels = ["email"]
+
+    def address_for(self, channel: str) -> str | None:
+        """Return the user's address on `channel`, or None if they have none or the channel is unknown."""
+        addresses = {"email": self.email, "sms": self.phone, "push": self.push_token}
+        return addresses.get(channel)
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,205 @@
+import pytest
+
+from notify import DeliveryError, NotificationService, TemplateStore, User
+
+
+class FakeSender:
+    """Fails the first `failures` sends with DeliveryError, then succeeds."""
+
+    def __init__(self, failures: int = 0) -> None:
+        self.failures_left = failures
+        self.calls: list[tuple[str, str]] = []
+
+    def send(self, address: str, message: str) -> None:
+        self.calls.append((address, message))
+        if self.failures_left > 0:
+            self.failures_left -= 1
+            raise DeliveryError(f"could not reach {address}")
+
+
+class BrokenSender:
+    def __init__(self) -> None:
+        self.calls = 0
+
+    def send(self, address: str, message: str) -> None:
+        self.calls += 1
+        raise DeliveryError(f"could not reach {address}")
+
+
+@pytest.fixture
+def templates() -> TemplateStore:
+    templates = TemplateStore()
+    templates.add("greeting", "Hello {name}")
+    return templates
+
+
+def make_user(preferred_channels=None) -> User:
+    return User(
+        id="u1",
+        email="ada@example.com",
+        phone="+39 000",
+        push_token="tok",
+        preferred_channels=preferred_channels,
+    )
+
+
+def test_negative_max_retries_raises_value_error(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_delivers_rendered_message_to_first_preferred_channel(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(make_user(), "greeting", name="Ada")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", True)]
+    assert email.calls == [("ada@example.com", "Hello Ada")]
+
+
+def test_template_parameters_may_reuse_notify_argument_names(templates):
+    templates.add("handover", "{user} passes {template_name} on")
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(make_user(), "handover", user="Ada", template_name="the baton")
+
+    assert email.calls == [("ada@example.com", "Ada passes the baton on")]
+
+
+def test_user_without_preferences_is_notified_by_email(templates):
+    email, sms = FakeSender(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    report = service.notify(make_user(), "greeting", name="Ada")
+
+    assert report.channel == "email"
+    assert sms.calls == []
+
+
+def test_retries_same_channel_until_it_succeeds(templates):
+    sms = FakeSender(failures=2)
+    service = NotificationService({"sms": sms}, templates, max_retries=2)
+
+    report = service.notify(make_user(["sms"]), "greeting", name="Ada")
+
+    assert report.delivered is True
+    assert report.attempts == [("sms", False), ("sms", False), ("sms", True)]
+
+
+def test_falls_back_to_next_channel_after_retries_are_exhausted(templates):
+    service = NotificationService({"email": BrokenSender(), "sms": FakeSender()}, templates, max_retries=1)
+
+    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")
+
+    assert report.delivered is True
+    assert report.channel == "sms"
+    assert report.attempts == [("email", False), ("email", False), ("sms", True)]
+
+
+def test_default_max_retries_allows_two_retries(templates):
+    email = BrokenSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(make_user(), "greeting", name="Ada")
+
+    assert email.calls == 3
+
+
+def test_zero_max_retries_tries_each_channel_once(templates):
+    service = NotificationService({"email": BrokenSender(), "push": BrokenSender()}, templates, max_retries=0)
+
+    report = service.notify(make_user(["email", "push"]), "greeting", name="Ada")
+
+    assert report.attempts == [("email", False), ("push", False)]
+
+
+def test_stops_at_first_successful_send(templates):
+    push = FakeSender()
+    service = NotificationService({"sms": FakeSender(), "push": push}, templates)
+
+    service.notify(make_user(["sms", "push"]), "greeting", name="Ada")
+
+    assert push.calls == []
+
+
+def test_reports_failure_when_every_channel_fails(templates):
+    service = NotificationService({"email": BrokenSender(), "sms": BrokenSender()}, templates, max_retries=0)
+
+    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == [("email", False), ("sms", False)]
+
+
+def test_skips_channel_without_configured_sender(templates):
+    service = NotificationService({"sms": FakeSender()}, templates)
+
+    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")
+
+    assert report.attempts == [("sms", True)]
+
+
+def test_skips_channel_where_user_has_no_address(templates):
+    email = FakeSender()
+    service = NotificationService({"sms": FakeSender(), "email": email}, templates)
+    user = User(id="u1", email="ada@example.com", preferred_channels=["sms", "email"])
+
+    report = service.notify(user, "greeting", name="Ada")
+
+    assert report.attempts == [("email", True)]
+
+
+def test_skips_unknown_channel_even_with_a_sender(templates):
+    fax = FakeSender()
+    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)
+
+    report = service.notify(make_user(["fax", "email"]), "greeting", name="Ada")
+
+    assert report.attempts == [("email", True)]
+    assert fax.calls == []
+
+
+def test_no_reachable_channel_reports_failure_without_attempts(templates):
+    service = NotificationService({}, templates)
+
+    report = service.notify(make_user(["email", "sms"]), "greeting", name="Ada")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == []
+
+
+@pytest.mark.parametrize(
+    ("template_name", "params", "error"),
+    [
+        ("unknown", {"name": "Ada"}, KeyError),
+        ("greeting", {}, ValueError),
+    ],
+)
+def test_template_errors_propagate_before_sending(templates, template_name, params, error):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(error):
+        service.notify(make_user(), template_name, **params)
+
+    assert email.calls == []
+
+
+def test_errors_other_than_delivery_error_propagate(templates):
+    class CrashingSender:
+        def send(self, address: str, message: str) -> None:
+            raise RuntimeError("sender bug")
+
+    sms = FakeSender()
+    service = NotificationService({"email": CrashingSender(), "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError, match="sender bug"):
+        service.notify(make_user(["email", "sms"]), "greeting", name="Ada")
+
+    assert sms.calls == []
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,24 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def store() -> TemplateStore:
+    store = TemplateStore()
+    store.add("welcome", "Hi {name}, welcome to {place}!")
+    return store
+
+
+def test_render_fills_placeholders_including_one_called_name(store):
+    assert store.render("welcome", name="Ada", place="Bergamo") == "Hi Ada, welcome to Bergamo!"
+
+
+def test_render_unknown_template_raises_key_error(store):
+    with pytest.raises(KeyError):
+        store.render("goodbye", name="Ada")
+
+
+def test_render_missing_parameter_raises_value_error(store):
+    with pytest.raises(ValueError, match="place"):
+        store.render("welcome", name="Ada")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,17 @@
+from notify import User
+
+
+def test_preferred_channels_default_to_email():
+    assert User(id="u1").preferred_channels == ["email"]
+
+
+def test_address_for_maps_each_channel_to_its_address():
+    user = User(id="u1", email="ada@example.com", phone="+39 000", push_token="tok")
+
+    assert user.address_for("email") == "ada@example.com"
+    assert user.address_for("sms") == "+39 000"
+    assert user.address_for("push") == "tok"
+
+
+def test_address_for_unknown_channel_is_none():
+    assert User(id="u1", email="ada@example.com").address_for("fax") is None
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,7 @@
+"""Send a templated message to a user through their preferred channels, with retries and fallback."""
+
+from .service import DeliveryError, DeliveryReport, NotificationService
+from .templates import TemplateStore
+from .user import User
+
+__all__ = ["DeliveryError", "DeliveryReport", "NotificationService", "TemplateStore", "User"]
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,67 @@
+from collections.abc import Iterator, Mapping
+from dataclasses import dataclass
+from typing import Protocol
+
+from .templates import TemplateStore
+from .user import User
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it could not deliver a message."""
+
+
+class Sender(Protocol):
+    def send(self, address: str, message: str) -> None:
+        """Delivers `message` to `address`, raising DeliveryError on failure."""
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """Outcome of one notification.
+
+    `attempts` holds a `(channel, succeeded)` tuple for every send, in the order they happened.
+    """
+
+    delivered: bool
+    channel: str | None
+    attempts: list[tuple[str, bool]]
+
+
+class NotificationService:
+    """Sends a templated message through a user's preferred channels, retrying each before falling back to the next."""
+
+    def __init__(self, senders: Mapping[str, Sender], templates: TemplateStore, max_retries: int = 2) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must not be negative, got {max_retries}")
+        self._senders = senders
+        self._templates = templates
+        self._attempts_per_channel = 1 + max_retries
+
+    # `user` and `template_name` are positional-only so that templates can use placeholders with those names.
+    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
+        """Template errors are raised before anything is sent. Sender errors other than DeliveryError propagate."""
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
+        for channel, sender, address in self._usable_channels(user):
+            for _ in range(self._attempts_per_channel):
+                succeeded = _try_send(sender, address, message)
+                attempts.append((channel, succeeded))
+                if succeeded:
+                    return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _usable_channels(self, user: User) -> Iterator[tuple[str, Sender, str]]:
+        """Yields `(channel, sender, address)` for each preferred channel that has both a sender and an address."""
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is not None and address is not None:
+                yield channel, sender, address
+
+
+def _try_send(sender: Sender, address: str, message: str) -> bool:
+    try:
+        sender.send(address, message)
+    except DeliveryError:
+        return False
+    return True
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,18 @@
+class TemplateStore:
+    """Named message templates with `str.format`-style `{param}` placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        self._templates[name] = text
+
+    # `name` is positional-only so that templates can use a `{name}` placeholder.
+    def render(self, name: str, /, **params: object) -> str:
+        """Raises KeyError for an unknown template and ValueError for a missing parameter."""
+        template = self._templates[name]
+        try:
+            return template.format(**params)
+        except KeyError as error:
+            missing = error.args[0]
+            raise ValueError(f"template {name!r} needs parameter {missing!r}") from error
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,21 @@
+from dataclasses import dataclass
+
+
+@dataclass
+class User:
+    """A notification recipient: their addresses and the channels to try, in order of preference."""
+
+    id: str
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        if self.preferred_channels is None:
+            self.preferred_channels = ["email"]
+
+    def address_for(self, channel: str) -> str | None:
+        """Returns the user's address on `channel`, or None if they have none or the channel is unknown."""
+        addresses = {"email": self.email, "sms": self.phone, "push": self.push_token}
+        return addresses.get(channel)
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,191 @@
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+EMAIL = "ann@example.com"
+PHONE = "+390000000"
+PUSH_TOKEN = "device-1"
+
+
+class FakeSender:
+    """Records every send and raises DeliveryError on the first `failures` of them."""
+
+    def __init__(self, failures: int = 0) -> None:
+        self.sent: list[tuple[str, str]] = []
+        self._failures_left = failures
+
+    def send(self, address: str, message: str) -> None:
+        self.sent.append((address, message))
+        if self._failures_left > 0:
+            self._failures_left -= 1
+            raise DeliveryError(f"simulated failure sending to {address}")
+
+
+class FailingSender:
+    """Records every send and raises `error` on each of them."""
+
+    def __init__(self, error: Exception) -> None:
+        self.sent: list[tuple[str, str]] = []
+        self._error = error
+
+    def send(self, address: str, message: str) -> None:
+        self.sent.append((address, message))
+        raise self._error
+
+
+def make_templates() -> TemplateStore:
+    templates = TemplateStore()
+    templates.add("welcome", "Hello {name}")
+    return templates
+
+
+def reachable_user(*channels: str) -> User:
+    return User("u1", email=EMAIL, phone=PHONE, push_token=PUSH_TOKEN, preferred_channels=list(channels))
+
+
+def unavailable() -> FailingSender:
+    return FailingSender(DeliveryError("provider unavailable"))
+
+
+def test_rejects_negative_max_retries():
+    with pytest.raises(ValueError):
+        NotificationService({}, make_templates(), max_retries=-1)
+
+
+def test_sends_rendered_message_to_first_preferred_channel():
+    email = FakeSender()
+    service = NotificationService({"email": email}, make_templates())
+
+    report = service.notify(reachable_user("email"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
+    assert email.sent == [(EMAIL, "Hello Ann")]
+
+
+def test_retries_same_channel_after_delivery_error():
+    email = FakeSender(failures=2)
+    service = NotificationService({"email": email}, make_templates(), max_retries=2)
+
+    report = service.notify(reachable_user("email"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(
+        delivered=True,
+        channel="email",
+        attempts=[("email", False), ("email", False), ("email", True)],
+    )
+
+
+def test_falls_back_to_next_channel_after_two_retries_by_default():
+    email, sms = unavailable(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, make_templates())
+
+    report = service.notify(reachable_user("email", "sms"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(
+        delivered=True,
+        channel="sms",
+        attempts=[("email", False), ("email", False), ("email", False), ("sms", True)],
+    )
+    assert sms.sent == [(PHONE, "Hello Ann")]
+
+
+def test_zero_retries_tries_each_channel_once():
+    service = NotificationService({"email": unavailable(), "sms": FakeSender()}, make_templates(), max_retries=0)
+
+    report = service.notify(reachable_user("email", "sms"), "welcome", name="Ann")
+
+    assert report.attempts == [("email", False), ("sms", True)]
+
+
+def test_stops_at_first_successful_send():
+    email, push = FakeSender(), FakeSender()
+    service = NotificationService({"email": email, "push": push}, make_templates())
+
+    service.notify(reachable_user("email", "push"), "welcome", name="Ann")
+
+    assert push.sent == []
+
+
+def test_reports_failure_when_every_channel_fails():
+    service = NotificationService({"email": unavailable(), "push": unavailable()}, make_templates(), max_retries=1)
+
+    report = service.notify(reachable_user("email", "push"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(
+        delivered=False,
+        channel=None,
+        attempts=[("email", False), ("email", False), ("push", False), ("push", False)],
+    )
+
+
+def test_skips_channel_without_sender():
+    service = NotificationService({"push": FakeSender()}, make_templates())
+
+    report = service.notify(reachable_user("sms", "push"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=True, channel="push", attempts=[("push", True)])
+
+
+def test_skips_channel_the_user_has_no_address_for():
+    sms, push = FakeSender(), FakeSender()
+    service = NotificationService({"sms": sms, "push": push}, make_templates())
+    user = User("u1", push_token=PUSH_TOKEN, preferred_channels=["sms", "push"])
+
+    report = service.notify(user, "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=True, channel="push", attempts=[("push", True)])
+    assert sms.sent == []
+
+
+def test_skips_unknown_channel_even_when_it_has_a_sender():
+    fax = FakeSender()
+    service = NotificationService({"fax": fax, "email": FakeSender()}, make_templates())
+
+    report = service.notify(reachable_user("fax", "email"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
+    assert fax.sent == []
+
+
+def test_reports_no_attempts_when_no_channel_is_usable():
+    service = NotificationService({"email": FakeSender()}, make_templates())
+
+    report = service.notify(User("u1", phone=PHONE, preferred_channels=["email", "sms"]), "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
+
+
+@pytest.mark.parametrize(
+    "template_name, params, error",
+    [("missing", {"name": "Ann"}, KeyError), ("welcome", {}, ValueError)],
+)
+def test_template_errors_propagate_before_anything_is_sent(template_name, params, error):
+    email = FakeSender()
+    service = NotificationService({"email": email}, make_templates())
+
+    with pytest.raises(error):
+        service.notify(reachable_user("email"), template_name, **params)
+
+    assert email.sent == []
+
+
+def test_errors_other_than_delivery_error_propagate_without_retry_or_fallback():
+    email, sms = FailingSender(RuntimeError("sender bug")), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, make_templates())
+
+    with pytest.raises(RuntimeError, match="sender bug"):
+        service.notify(reachable_user("email", "sms"), "welcome", name="Ann")
+
+    assert len(email.sent) == 1
+    assert sms.sent == []
+
+
+def test_template_parameters_may_share_names_with_notify_arguments():
+    email = FakeSender()
+    templates = TemplateStore()
+    templates.add("digest", "{user} has {template_name}")
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(reachable_user("email"), "digest", user="Ann", template_name="news")
+
+    assert email.sent == [(EMAIL, "Ann has news")]
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,33 @@
+import pytest
+
+from notify import TemplateStore
+
+
+def store_with(name: str, text: str) -> TemplateStore:
+    templates = TemplateStore()
+    templates.add(name, text)
+    return templates
+
+
+def test_render_fills_placeholders():
+    templates = store_with("order", "Order {order_id} ships on {day}")
+
+    assert templates.render("order", order_id=42, day="Monday") == "Order 42 ships on Monday"
+
+
+def test_render_accepts_a_parameter_called_name():
+    templates = store_with("welcome", "Hello {name}")
+
+    assert templates.render("welcome", name="Ann") == "Hello Ann"
+
+
+def test_render_raises_key_error_for_unknown_template():
+    with pytest.raises(KeyError):
+        TemplateStore().render("missing")
+
+
+def test_render_raises_value_error_for_missing_parameter():
+    templates = store_with("welcome", "Hello {name}")
+
+    with pytest.raises(ValueError, match="name"):
+        templates.render("welcome")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,33 @@
+import pytest
+
+from notify import User
+
+
+def test_preferred_channels_default_to_email():
+    assert User("u1").preferred_channels == ["email"]
+
+
+def test_default_preferred_channels_are_not_shared_between_users():
+    first, second = User("u1"), User("u2")
+
+    first.preferred_channels.append("sms")
+
+    assert second.preferred_channels == ["email"]
+
+
+@pytest.mark.parametrize(
+    "channel, address",
+    [("email", "ann@example.com"), ("sms", "+390000000"), ("push", "device-1")],
+)
+def test_address_for_returns_the_channels_address(channel, address):
+    user = User("u1", email="ann@example.com", phone="+390000000", push_token="device-1")
+
+    assert user.address_for(channel) == address
+
+
+def test_address_for_is_none_when_user_has_no_address_for_channel():
+    assert User("u1", email="ann@example.com").address_for("sms") is None
+
+
+def test_address_for_is_none_for_unknown_channel():
+    assert User("u1", email="ann@example.com").address_for("fax") is None
```

### Implementation 2

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,19 @@
+"""Send a templated message to a user through their preferred channels.
+
+Senders are injected: any object with `send(address, message) -> None` that
+raises `DeliveryError` on failure.
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
+"""Exceptions raised by the notify package."""
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it cannot deliver a message.
+
+    The service treats it as an expected failure: it retries the channel and
+    then falls back to the next one. Any other exception from a sender is not
+    handled and propagates to the caller.
+    """
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,96 @@
+"""Delivery of templated messages over a user's preferred channels."""
+
+from collections.abc import Mapping
+from dataclasses import dataclass
+from typing import Protocol
+
+from notify.errors import DeliveryError
+from notify.templates import TemplateStore
+from notify.user import User
+
+
+class Sender(Protocol):
+    """Delivers a message to an address on one channel.
+
+    Raises DeliveryError when delivery fails.
+    """
+
+    def send(self, address: str, message: str) -> None: ...
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    """The outcome of one `NotificationService.notify` call."""
+
+    delivered: bool
+    channel: str | None
+    attempts: list[tuple[str, bool]]
+
+
+class NotificationService:
+    """Sends a rendered template through a user's channels, with retries and fallback."""
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
+            templates: where message templates are looked up.
+            max_retries: extra attempts on a channel after its first failure.
+        """
+        if max_retries < 0:
+            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
+        self._senders = dict(senders)
+        self._templates = templates
+        self._max_retries = max_retries
+
+    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
+        """Render `template_name` with `params` and deliver it to `user`.
+
+        Channels are tried in the user's order of preference. A channel with
+        no sender, no address for this user or an unknown name is skipped
+        without an attempt. Each channel gets up to `max_retries` extra
+        attempts after a DeliveryError before the next channel is tried.
+        Delivery stops at the first success.
+
+        `user` and `template_name` are positional-only so templates may use
+        `{user}` or `{template_name}` placeholders.
+
+        Raises:
+            KeyError, ValueError: the template is unknown or a parameter is
+                missing; nothing is sent.
+            Any exception other than DeliveryError raised by a sender.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
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
+        attempts: list[tuple[str, bool]],
+    ) -> bool:
+        """Try one channel up to 1 + max_retries times, recording each attempt."""
+        for _ in range(1 + self._max_retries):
+            try:
+                sender.send(address, message)
+            except DeliveryError:
+                attempts.append((channel, False))
+            else:
+                attempts.append((channel, True))
+                return True
+        return False
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,31 @@
+"""Named message templates."""
+
+
+class TemplateStore:
+    """Stores templates that use `str.format` style `{param}` placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        """Store `text` under `name`, replacing any template with that name."""
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Fill the template `name` with `params`.
+
+        `name` is positional-only so a template may itself use a `{name}`
+        placeholder.
+
+        Raises:
+            KeyError: no template is stored under `name`.
+            ValueError: a placeholder has no matching parameter.
+        """
+        try:
+            text = self._templates[name]
+        except KeyError:
+            raise KeyError(f"unknown template: {name!r}") from None
+        try:
+            return text.format(**params)
+        except (KeyError, IndexError) as exc:
+            raise ValueError(f"missing parameter for template {name!r}: {exc}") from exc
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,44 @@
+"""The recipient of a notification."""
+
+from dataclasses import dataclass
+from typing import Any
+
+# Each supported channel and the User attribute that holds its address.
+CHANNEL_ADDRESS_FIELDS = {
+    "email": "email",
+    "sms": "phone",
+    "push": "push_token",
+}
+
+DEFAULT_CHANNELS = ("email",)
+
+
+@dataclass
+class User:
+    """A user with optional addresses and an ordered list of preferred channels."""
+
+    id: Any
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        if self.preferred_channels is None:
+            self.preferred_channels = list(DEFAULT_CHANNELS)
+        elif isinstance(self.preferred_channels, str):
+            # A bare string would be iterated letter by letter and silently
+            # match no channel, so reject it outright.
+            raise TypeError("preferred_channels must be a list of channel names, not a string")
+        else:
+            self.preferred_channels = list(self.preferred_channels)
+
+    def address_for(self, channel: str) -> str | None:
+        """Return this user's address for `channel`, or None if there is none.
+
+        Unknown channel names and empty addresses both count as no address.
+        """
+        field_name = CHANNEL_ADDRESS_FIELDS.get(channel)
+        if field_name is None:
+            return None
+        return getattr(self, field_name) or None
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,166 @@
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+
+class FakeSender:
+    """Records calls; fails with DeliveryError for the first `failures` sends."""
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
+            raise DeliveryError("down")
+
+
+ALWAYS_FAILS = 10**6
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}")
+    return store
+
+
+def full_user(channels):
+    return User(
+        1,
+        email="a@example.com",
+        phone="+39123",
+        push_token="tok",
+        preferred_channels=channels,
+    )
+
+
+def test_negative_max_retries_is_rejected(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_delivers_on_first_preferred_channel(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(User(1, email="a@example.com"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
+    assert email.calls == [("a@example.com", "Hello Ann")]
+
+
+def test_retries_same_channel_until_success(templates):
+    email = FakeSender(failures=2)
+    service = NotificationService({"email": email}, templates, max_retries=2)
+
+    report = service.notify(User(1, email="a@example.com"), "welcome", name="Ann")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", False), ("email", False), ("email", True)]
+
+
+def test_falls_back_after_retries_are_exhausted(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=2)
+
+    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ann")
+
+    assert report.channel == "sms"
+    assert report.attempts == [("email", False)] * 3 + [("sms", True)]
+    assert sms.calls == [("+39123", "Hello Ann")]
+
+
+def test_zero_retries_means_one_attempt_per_channel(templates):
+    email = FakeSender(failures=ALWAYS_FAILS)
+    push = FakeSender()
+    service = NotificationService({"email": email, "push": push}, templates, max_retries=0)
+
+    report = service.notify(full_user(["email", "push"]), "welcome", name="Ann")
+
+    assert report.attempts == [("email", False), ("push", True)]
+    assert push.calls == [("tok", "Hello Ann")]
+
+
+def test_stops_at_first_success(templates):
+    email, sms = FakeSender(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    service.notify(full_user(["email", "sms"]), "welcome", name="Ann")
+
+    assert sms.calls == []
+
+
+def test_all_channels_failing_is_reported(templates):
+    senders = {"email": FakeSender(failures=ALWAYS_FAILS), "sms": FakeSender(failures=ALWAYS_FAILS)}
+    service = NotificationService(senders, templates, max_retries=1)
+
+    report = service.notify(full_user(["email", "sms"]), "welcome", name="Ann")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == [("email", False), ("email", False), ("sms", False), ("sms", False)]
+
+
+def test_skips_channels_without_sender_address_or_known_name(templates):
+    push = FakeSender()
+    fax = FakeSender()
+    service = NotificationService({"push": push, "fax": fax, "email": FakeSender()}, templates)
+    user = User(1, phone="+39123", push_token="tok", preferred_channels=["fax", "sms", "email", "push"])
+
+    report = service.notify(user, "welcome", name="Ann")
+
+    # fax: unknown name; sms: no sender; email: no address.
+    assert report.attempts == [("push", True)]
+    assert fax.calls == []
+
+
+def test_no_usable_channel_gives_empty_report(templates):
+    service = NotificationService({}, templates)
+
+    report = service.notify(User(1, email="a@example.com"), "welcome", name="Ann")
+
+    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
+
+
+@pytest.mark.parametrize(
+    "template_name, params, error",
+    [("missing", {"name": "Ann"}, KeyError), ("welcome", {}, ValueError)],
+)
+def test_template_errors_propagate_before_sending(templates, template_name, params, error):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(error):
+        service.notify(User(1, email="a@example.com"), template_name, **params)
+
+    assert email.calls == []
+
+
+def test_non_delivery_errors_propagate(templates):
+    email = FakeSender(error=RuntimeError("bug"))
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError):
+        service.notify(full_user(["email", "sms"]), "welcome", name="Ann")
+
+    assert len(email.calls) == 1
+    assert sms.calls == []
+
+
+def test_template_may_use_user_and_template_name_placeholders():
+    store = TemplateStore()
+    store.add("t", "{user} got {template_name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, store)
+
+    service.notify(User(1, email="a@example.com"), "t", user="Ann", template_name="news")
+
+    assert email.calls == [("a@example.com", "Ann got news")]
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,46 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def store():
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}, welcome to {site}!")
+    return store
+
+
+def test_render_fills_placeholders(store):
+    assert store.render("welcome", name="Ann", site="Acme") == "Hello Ann, welcome to Acme!"
+
+
+def test_render_ignores_extra_params(store):
+    assert store.render("welcome", name="Ann", site="Acme", unused=1) == "Hello Ann, welcome to Acme!"
+
+
+def test_render_without_placeholders():
+    store = TemplateStore()
+    store.add("ping", "ping")
+    assert store.render("ping") == "ping"
+
+
+def test_add_replaces_existing_template(store):
+    store.add("welcome", "Hi {name}")
+    assert store.render("welcome", name="Ann") == "Hi Ann"
+
+
+def test_unknown_template_raises_key_error(store):
+    with pytest.raises(KeyError):
+        store.render("nope")
+
+
+def test_missing_parameter_raises_value_error(store):
+    with pytest.raises(ValueError, match="site"):
+        store.render("welcome", name="Ann")
+
+
+def test_positional_placeholder_raises_value_error():
+    store = TemplateStore()
+    store.add("bad", "Hello {}")
+    with pytest.raises(ValueError):
+        store.render("bad")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,40 @@
+import pytest
+
+from notify import User
+
+
+def test_preferred_channels_default_to_email():
+    assert User(1).preferred_channels == ["email"]
+    assert User(1, preferred_channels=None).preferred_channels == ["email"]
+
+
+def test_default_channels_are_not_shared_between_users():
+    first, second = User(1), User(2)
+    first.preferred_channels.append("sms")
+    assert second.preferred_channels == ["email"]
+
+
+def test_preferred_channels_are_copied():
+    channels = ["sms", "email"]
+    user = User(1, preferred_channels=channels)
+    channels.append("push")
+    assert user.preferred_channels == ["sms", "email"]
+
+
+def test_preferred_channels_as_string_is_rejected():
+    with pytest.raises(TypeError):
+        User(1, preferred_channels="email")
+
+
+def test_address_for_maps_each_channel_to_its_field():
+    user = User(1, email="a@example.com", phone="+39123", push_token="tok")
+    assert user.address_for("email") == "a@example.com"
+    assert user.address_for("sms") == "+39123"
+    assert user.address_for("push") == "tok"
+
+
+def test_address_for_missing_empty_or_unknown_is_none():
+    user = User(1, email="", phone=None)
+    assert user.address_for("email") is None
+    assert user.address_for("sms") is None
+    assert user.address_for("fax") is None
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,7 @@
+"""Send a message to a user through their preferred channels, with retries and fallback."""
+
+from .service import DeliveryError, DeliveryReport, NotificationService
+from .templates import TemplateStore
+from .user import User
+
+__all__ = ["DeliveryError", "DeliveryReport", "NotificationService", "TemplateStore", "User"]
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,65 @@
+from collections.abc import Iterator, Mapping
+from dataclasses import dataclass
+from typing import Protocol
+
+from .templates import TemplateStore
+from .user import User
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it could not deliver a message."""
+
+
+class Sender(Protocol):
+    def send(self, address: str, message: str) -> None:
+        """Delivers the message to the address, or raises DeliveryError."""
+
+
+@dataclass(frozen=True)
+class DeliveryReport:
+    delivered: bool
+    channel: str | None
+    attempts: list[tuple[str, bool]]
+
+
+class NotificationService:
+    """Sends a templated message through a user's preferred channels.
+
+    Each channel is retried up to max_retries times before falling back to the next one.
+    """
+
+    def __init__(
+        self, senders: Mapping[str, Sender], templates: TemplateStore, max_retries: int = 2
+    ) -> None:
+        if max_retries < 0:
+            raise ValueError(f"max_retries must not be negative, got {max_retries}")
+        self._senders = senders
+        self._templates = templates
+        self._max_attempts_per_channel = max_retries + 1
+
+    def notify(self, user: User, template_name: str, /, **params: object) -> DeliveryReport:
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
+        for channel, sender, address in self._reachable_channels(user):
+            for _ in range(self._max_attempts_per_channel):
+                succeeded = _try_send(sender, address, message)
+                attempts.append((channel, succeeded))
+                if succeeded:
+                    return DeliveryReport(delivered=True, channel=channel, attempts=attempts)
+        return DeliveryReport(delivered=False, channel=None, attempts=attempts)
+
+    def _reachable_channels(self, user: User) -> Iterator[tuple[str, Sender, str]]:
+        """Yields, in preference order, the channels that have both a sender and an address."""
+        for channel in user.preferred_channels:
+            sender = self._senders.get(channel)
+            address = user.address_for(channel)
+            if sender is not None and address is not None:
+                yield channel, sender, address
+
+
+def _try_send(sender: Sender, address: str, message: str) -> bool:
+    try:
+        sender.send(address, message)
+    except DeliveryError:
+        return False
+    return True
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,18 @@
+class TemplateStore:
+    """Named message templates with str.format-style {param} placeholders."""
+
+    def __init__(self) -> None:
+        self._templates: dict[str, str] = {}
+
+    def add(self, name: str, text: str) -> None:
+        self._templates[name] = text
+
+    def render(self, name: str, /, **params: object) -> str:
+        """Raises KeyError for an unknown template and ValueError for a missing parameter."""
+        template = self._templates[name]
+        try:
+            return template.format(**params)
+        except KeyError as missing:
+            raise ValueError(
+                f"template {name!r} needs parameter {missing.args[0]!r}"
+            ) from missing
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,19 @@
+from dataclasses import dataclass
+
+
+@dataclass
+class User:
+    id: str
+    email: str | None = None
+    phone: str | None = None
+    push_token: str | None = None
+    preferred_channels: list[str] | None = None
+
+    def __post_init__(self) -> None:
+        if self.preferred_channels is None:
+            self.preferred_channels = ["email"]
+
+    def address_for(self, channel: str) -> str | None:
+        """Returns None when the channel is unknown or the user has no address for it."""
+        addresses = {"email": self.email, "sms": self.phone, "push": self.push_token}
+        return addresses.get(channel)
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,192 @@
+import math
+
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+
+class FakeSender:
+    """Raises DeliveryError for the first `failures` sends, then succeeds. Records every call."""
+
+    def __init__(self, failures=0):
+        self._failures_left = failures
+        self.calls = []
+
+    def send(self, address, message):
+        self.calls.append((address, message))
+        if self._failures_left > 0:
+            self._failures_left -= 1
+            raise DeliveryError(f"simulated failure sending to {address}")
+
+
+class CrashingSender:
+    def send(self, address, message):
+        raise RuntimeError("sender bug")
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}!")
+    return store
+
+
+def make_user(preferred_channels):
+    return User(
+        id="u1",
+        email="ada@example.com",
+        phone="+39021234567",
+        push_token="token-1",
+        preferred_channels=preferred_channels,
+    )
+
+
+def test_rejects_negative_max_retries(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_sends_the_rendered_message_to_the_address_of_the_first_preferred_channel(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(make_user(["email"]), "welcome", name="Ada")
+
+    assert email.calls == [("ada@example.com", "Hello Ada!")]
+    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
+
+
+def test_accepts_template_parameters_named_like_its_own_arguments(templates):
+    templates.add("mention", "{user} used {template_name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(make_user(["email"]), "mention", user="Ada", template_name="welcome")
+
+    assert email.calls == [("ada@example.com", "Ada used welcome")]
+
+
+def test_retries_the_same_channel_until_it_succeeds(templates):
+    service = NotificationService({"sms": FakeSender(failures=2)}, templates, max_retries=2)
+
+    report = service.notify(make_user(["sms"]), "welcome", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=True,
+        channel="sms",
+        attempts=[("sms", False), ("sms", False), ("sms", True)],
+    )
+
+
+def test_retries_twice_by_default(templates):
+    service = NotificationService({"email": FakeSender(failures=math.inf)}, templates)
+
+    report = service.notify(make_user(["email"]), "welcome", name="Ada")
+
+    assert report.attempts == [("email", False)] * 3
+
+
+def test_falls_back_to_the_next_channel_after_retries_are_exhausted(templates):
+    senders = {"email": FakeSender(failures=math.inf), "push": FakeSender()}
+    service = NotificationService(senders, templates, max_retries=1)
+
+    report = service.notify(make_user(["email", "push"]), "welcome", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=True,
+        channel="push",
+        attempts=[("email", False), ("email", False), ("push", True)],
+    )
+
+
+def test_makes_a_single_attempt_per_channel_when_max_retries_is_zero(templates):
+    senders = {"email": FakeSender(failures=math.inf), "sms": FakeSender()}
+    service = NotificationService(senders, templates, max_retries=0)
+
+    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert report.attempts == [("email", False), ("sms", True)]
+
+
+def test_reports_failure_when_every_channel_fails(templates):
+    senders = {"email": FakeSender(failures=math.inf), "sms": FakeSender(failures=math.inf)}
+    service = NotificationService(senders, templates, max_retries=0)
+
+    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert report == DeliveryReport(
+        delivered=False, channel=None, attempts=[("email", False), ("sms", False)]
+    )
+
+
+def test_stops_at_the_first_successful_send(templates):
+    sms = FakeSender()
+    service = NotificationService({"email": FakeSender(), "sms": sms}, templates)
+
+    service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert sms.calls == []
+
+
+def test_skips_a_channel_without_a_sender_and_records_no_attempt(templates):
+    service = NotificationService({"sms": FakeSender()}, templates)
+
+    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert report.attempts == [("sms", True)]
+
+
+def test_skips_a_channel_the_user_has_no_address_for(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email, "sms": FakeSender()}, templates)
+    user = User(id="u1", phone="+39021234567", preferred_channels=["email", "sms"])
+
+    report = service.notify(user, "welcome", name="Ada")
+
+    assert email.calls == []
+    assert report.attempts == [("sms", True)]
+
+
+def test_skips_an_unknown_channel(templates):
+    fax = FakeSender()
+    service = NotificationService({"fax": fax, "email": FakeSender()}, templates)
+
+    report = service.notify(make_user(["fax", "email"]), "welcome", name="Ada")
+
+    assert fax.calls == []
+    assert report.attempts == [("email", True)]
+
+
+def test_reports_no_attempts_when_no_channel_is_reachable(templates):
+    service = NotificationService({}, templates)
+
+    report = service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
+
+    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
+
+
+def test_unknown_template_propagates_before_anything_is_sent(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(KeyError):
+        service.notify(make_user(["email"]), "goodbye", name="Ada")
+    assert email.calls == []
+
+
+def test_missing_template_parameter_propagates_before_anything_is_sent(templates):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(ValueError):
+        service.notify(make_user(["email"]), "welcome")
+    assert email.calls == []
+
+
+def test_errors_other_than_delivery_error_propagate_without_fallback(templates):
+    sms = FakeSender()
+    service = NotificationService({"email": CrashingSender(), "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError):
+        service.notify(make_user(["email", "sms"]), "welcome", name="Ada")
+    assert sms.calls == []
diff -ruN before/tests/test_templates.py after/tests/test_templates.py
--- before/tests/test_templates.py
+++ after/tests/test_templates.py
@@ -0,0 +1,24 @@
+import pytest
+
+from notify import TemplateStore
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("welcome", "Hello {name}, welcome to {product}!")
+    return store
+
+
+def test_render_fills_the_placeholders(templates):
+    assert templates.render("welcome", name="Ada", product="Notify") == "Hello Ada, welcome to Notify!"
+
+
+def test_render_raises_key_error_for_an_unknown_template(templates):
+    with pytest.raises(KeyError):
+        templates.render("goodbye", name="Ada")
+
+
+def test_render_raises_value_error_naming_the_missing_parameter(templates):
+    with pytest.raises(ValueError, match="product"):
+        templates.render("welcome", name="Ada")
diff -ruN before/tests/test_user.py after/tests/test_user.py
--- before/tests/test_user.py
+++ after/tests/test_user.py
@@ -0,0 +1,25 @@
+import pytest
+
+from notify import User
+
+
+def test_preferred_channels_default_to_email():
+    assert User(id="u1").preferred_channels == ["email"]
+
+
+@pytest.mark.parametrize(
+    ("channel", "expected_address"),
+    [("email", "ada@example.com"), ("sms", "+39021234567"), ("push", "token-1")],
+)
+def test_address_for_returns_the_address_matching_the_channel(channel, expected_address):
+    user = User(id="u1", email="ada@example.com", phone="+39021234567", push_token="token-1")
+
+    assert user.address_for(channel) == expected_address
+
+
+def test_address_for_returns_none_when_the_user_has_no_address_for_the_channel():
+    assert User(id="u1", email="ada@example.com").address_for("sms") is None
+
+
+def test_address_for_returns_none_for_an_unknown_channel():
+    assert User(id="u1", email="ada@example.com").address_for("fax") is None
```

### Implementation 2

```diff
diff -ruN before/notify/__init__.py after/notify/__init__.py
--- before/notify/__init__.py
+++ after/notify/__init__.py
@@ -0,0 +1,15 @@
+"""Send templated notifications to users over their preferred channels."""
+
+from notify.delivery import DeliveryError, DeliveryReport, Sender
+from notify.service import NotificationService
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
diff -ruN before/notify/delivery.py after/notify/delivery.py
--- before/notify/delivery.py
+++ after/notify/delivery.py
@@ -0,0 +1,28 @@
+"""Types shared between the service and the senders it drives."""
+
+from dataclasses import dataclass, field
+from typing import Protocol
+
+
+class DeliveryError(Exception):
+    """Raised by a sender when it could not deliver a message."""
+
+
+class Sender(Protocol):
+    """Anything that can deliver a message to an address on one channel."""
+
+    def send(self, address: str, message: str) -> None:
+        """Deliver ``message`` to ``address``; raise DeliveryError on failure."""
+
+
+@dataclass
+class DeliveryReport:
+    """Outcome of one ``NotificationService.notify`` call.
+
+    ``attempts`` lists every send attempt as ``(channel, succeeded)``,
+    in the order the attempts happened.
+    """
+
+    delivered: bool
+    channel: str | None = None
+    attempts: list[tuple[str, bool]] = field(default_factory=list)
diff -ruN before/notify/service.py after/notify/service.py
--- before/notify/service.py
+++ after/notify/service.py
@@ -0,0 +1,71 @@
+"""Delivery of templated messages over a user's preferred channels."""
+
+from collections.abc import Mapping
+
+from notify.delivery import DeliveryError, DeliveryReport, Sender
+from notify.templates import TemplateStore
+from notify.user import User
+
+
+class NotificationService:
+    """Sends a rendered template to a user, retrying each channel and falling back.
+
+    ``senders`` maps channel name to sender. Each usable channel gets one attempt
+    plus up to ``max_retries`` retries before the next channel is tried.
+    """
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
+        """Render ``template_name`` and send it to ``user``; stop at the first success.
+
+        ``user`` and ``template_name`` are positional-only, so templates may use
+        placeholders with those names.
+
+        A channel is skipped, with no attempt recorded, when it has no configured
+        sender or the user has no address for it (this includes unknown names).
+        Template errors propagate before anything is sent, and exceptions other
+        than DeliveryError propagate from the sender.
+        """
+        message = self._templates.render(template_name, **params)
+        attempts: list[tuple[str, bool]] = []
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
+        attempts: list[tuple[str, bool]],
+    ) -> bool:
+        """Try one channel up to ``1 + max_retries`` times, appending each attempt.
+
+        Returns True as soon as a send succeeds, False once every attempt failed.
+        """
+        for _ in range(1 + self._max_retries):
+            try:
+                sender.send(address, message)
+            except DeliveryError:
+                attempts.append((channel, False))
+            else:
+                attempts.append((channel, True))
+                return True
+        return False
diff -ruN before/notify/templates.py after/notify/templates.py
--- before/notify/templates.py
+++ after/notify/templates.py
@@ -0,0 +1,31 @@
+"""Named message templates using ``str.format`` placeholders."""
+
+
+class TemplateStore:
+    """Holds templates by name and renders them with keyword parameters."""
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
+        ``name`` is positional-only, so a template may use a ``{name}`` placeholder.
+
+        Raises:
+            KeyError: no template is stored under ``name``.
+            ValueError: a placeholder has no matching parameter.
+        """
+        text = self._templates[name]
+        try:
+            return text.format(**params)
+        except (KeyError, IndexError) as exc:
+            # IndexError comes from positional placeholders such as "{}" or "{0}",
+            # which keyword parameters can never fill.
+            raise ValueError(
+                f"missing parameter for template {name!r}: {exc}"
+            ) from exc
diff -ruN before/notify/user.py after/notify/user.py
--- before/notify/user.py
+++ after/notify/user.py
@@ -0,0 +1,43 @@
+"""Notification recipients and their per-channel addresses."""
+
+from dataclasses import dataclass
+
+# Each supported channel and the User attribute that holds its address.
+CHANNEL_ADDRESS_ATTRIBUTES = {
+    "email": "email",
+    "sms": "phone",
+    "push": "push_token",
+}
+
+DEFAULT_CHANNELS = ("email",)
+
+
+@dataclass
+class User:
+    """A recipient with an address per channel and an ordered channel preference.
+
+    ``preferred_channels`` defaults to ``["email"]``. The list given is copied,
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
+        if self.preferred_channels is None:
+            self.preferred_channels = list(DEFAULT_CHANNELS)
+        else:
+            self.preferred_channels = list(self.preferred_channels)
+
+    def address_for(self, channel: str) -> str | None:
+        """Return this user's address on ``channel``.
+
+        Returns None when the channel is unknown or the address is unset or empty.
+        """
+        attribute = CHANNEL_ADDRESS_ATTRIBUTES.get(channel)
+        if attribute is None:
+            return None
+        return getattr(self, attribute) or None
diff -ruN before/tests/test_service.py after/tests/test_service.py
--- before/tests/test_service.py
+++ after/tests/test_service.py
@@ -0,0 +1,180 @@
+import math
+
+import pytest
+
+from notify import DeliveryError, DeliveryReport, NotificationService, TemplateStore, User
+
+
+class FakeSender:
+    """Records every call; raises ``error`` on the first ``failures`` calls."""
+
+    def __init__(self, failures=0, error=DeliveryError):
+        self.calls = []
+        self._failures = failures
+        self._error = error
+
+    def send(self, address, message):
+        self.calls.append((address, message))
+        if len(self.calls) <= self._failures:
+            raise self._error("send failed")
+
+
+def always_failing():
+    return FakeSender(failures=math.inf)
+
+
+@pytest.fixture
+def templates():
+    store = TemplateStore()
+    store.add("greet", "Hi {name}")
+    return store
+
+
+@pytest.fixture
+def user():
+    return User(
+        id=7,
+        email="ada@example.com",
+        phone="+39123",
+        push_token="tok-1",
+        preferred_channels=["email", "sms", "push"],
+    )
+
+
+def test_negative_max_retries_is_rejected(templates):
+    with pytest.raises(ValueError):
+        NotificationService({}, templates, max_retries=-1)
+
+
+def test_first_channel_success_sends_rendered_message_to_its_address(templates, user):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report == DeliveryReport(delivered=True, channel="email", attempts=[("email", True)])
+    assert email.calls == [("ada@example.com", "Hi Ada")]
+
+
+def test_retries_same_channel_until_it_succeeds(templates, user):
+    email = FakeSender(failures=1)
+    service = NotificationService({"email": email}, templates, max_retries=2)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report.delivered is True
+    assert report.channel == "email"
+    assert report.attempts == [("email", False), ("email", True)]
+
+
+def test_falls_back_after_exhausting_retries(templates, user):
+    email, sms = always_failing(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=2)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report.channel == "sms"
+    assert report.attempts == [("email", False)] * 3 + [("sms", True)]
+    assert sms.calls == [("+39123", "Hi Ada")]
+
+
+def test_zero_retries_means_one_attempt_per_channel(templates, user):
+    email, sms = always_failing(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates, max_retries=0)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report.attempts == [("email", False), ("sms", True)]
+
+
+def test_stops_at_first_success(templates, user):
+    email, sms = FakeSender(), FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    service.notify(user, "greet", name="Ada")
+
+    assert sms.calls == []
+
+
+def test_all_channels_failing_reports_not_delivered(templates, user):
+    senders = {"email": always_failing(), "sms": always_failing(), "push": always_failing()}
+    service = NotificationService(senders, templates, max_retries=1)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report.delivered is False
+    assert report.channel is None
+    assert report.attempts == [
+        ("email", False), ("email", False),
+        ("sms", False), ("sms", False),
+        ("push", False), ("push", False),
+    ]
+
+
+def test_skips_channels_without_sender_address_or_known_name(templates):
+    push = FakeSender()
+    user = User(id=1, email="a@example.com", push_token="tok",
+                preferred_channels=["fax", "email", "sms", "push"])
+    # "fax" is unknown, "email" has no sender, "sms" has no address.
+    service = NotificationService({"fax": FakeSender(), "sms": FakeSender(), "push": push},
+                                  templates)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report == DeliveryReport(delivered=True, channel="push", attempts=[("push", True)])
+
+
+def test_no_usable_channel_reports_not_delivered_without_attempts(templates):
+    user = User(id=1)  # prefers email but has no email address
+    service = NotificationService({"email": FakeSender()}, templates)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report == DeliveryReport(delivered=False, channel=None, attempts=[])
+
+
+@pytest.mark.parametrize(
+    ("template_name", "params", "error"),
+    [("unknown", {"name": "Ada"}, KeyError), ("greet", {}, ValueError)],
+)
+def test_template_errors_propagate_before_sending(templates, user, template_name, params, error):
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    with pytest.raises(error):
+        service.notify(user, template_name, **params)
+
+    assert email.calls == []
+
+
+def test_other_exceptions_propagate_without_retry(templates, user):
+    email = FakeSender(failures=1, error=RuntimeError)
+    sms = FakeSender()
+    service = NotificationService({"email": email, "sms": sms}, templates)
+
+    with pytest.raises(RuntimeError):
+        service.notify(user, "greet", name="Ada")
+
+    assert len(email.calls) == 1
+    assert sms.calls == []
+
+
+def test_delivery_error_subclasses_are_retried(templates, user):
+    class Timeout(DeliveryError):
+        pass
+
+    service = NotificationService({"email": FakeSender(failures=1, error=Timeout)}, templates)
+
+    report = service.notify(user, "greet", name="Ada")
+
+    assert report.attempts == [("email", False), ("email", True)]
+
+
+def test_templates_may_use_user_and_template_name_placeholders(templates, user):
+    templates.add("meta", "{user} got {template_name}")
+    email = FakeSender()
+    service = NotificationService({"email": email}, templates)
+
+    service.notify(user, "meta", user="Ada", template_name="news")
+
+    assert email.calls == [("ada@example.com", "Ada got news")]
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
+def store():
+    templates = TemplateStore()
+    templates.add("welcome", "Hello {name}, welcome to {site}!")
+    return templates
+
+
+def test_render_fills_placeholders(store):
+    assert store.render("welcome", name="Ada", site="Notify") == "Hello Ada, welcome to Notify!"
+
+
+def test_render_ignores_extra_parameters(store):
+    assert store.render("welcome", name="Ada", site="X", unused=1) == "Hello Ada, welcome to X!"
+
+
+def test_unknown_template_raises_key_error(store):
+    with pytest.raises(KeyError):
+        store.render("missing", name="Ada")
+
+
+def test_missing_parameter_raises_value_error(store):
+    with pytest.raises(ValueError, match="site"):
+        store.render("welcome", name="Ada")
+
+
+def test_positional_placeholder_raises_value_error(store):
+    store.add("positional", "Hi {}")
+
+    with pytest.raises(ValueError):
+        store.render("positional")
+
+
+def test_add_replaces_existing_template(store):
+    store.add("welcome", "Hi {name}")
+
+    assert store.render("welcome", name="Ada") == "Hi Ada"
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
+def test_default_channel_list_is_not_shared_between_users():
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
+def test_address_for_maps_each_channel_to_its_field():
+    user = User(id=1, email="a@example.com", phone="+391234", push_token="tok")
+
+    assert user.address_for("email") == "a@example.com"
+    assert user.address_for("sms") == "+391234"
+    assert user.address_for("push") == "tok"
+
+
+def test_address_for_is_none_for_unknown_channel_or_missing_address():
+    user = User(id=1, email="", phone=None)
+
+    assert user.address_for("fax") is None
+    assert user.address_for("email") is None
+    assert user.address_for("sms") is None
```

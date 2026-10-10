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

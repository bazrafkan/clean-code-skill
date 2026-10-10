# Summary

I built the `notify` package. All five names import from the package root: `User`, `TemplateStore`, `NotificationService`, `DeliveryReport` and `DeliveryError`. The 25 tests in `tests/` pass (`python3 -m pytest`).

## Layout

- `notify/delivery.py`: `DeliveryError`, `DeliveryReport` (a dataclass with `delivered`, `channel` and `attempts`), and a `Sender` protocol describing `send(address, message)`.
- `notify/user.py`: `User`, plus the table that maps each channel to its address field (`email` uses `email`, `sms` uses `phone`, `push` uses `push_token`).
- `notify/templates.py`: `TemplateStore`.
- `notify/service.py`: `NotificationService`.
- `tests/`: tests for the user, the template store and the service. The service tests cover retries, fallback, skipped channels, template errors raised before any send, other exceptions passing through, and `max_retries=0`.

## Choices the spec didn't settle

- **Parameter names can be placeholders.** In `render(name, /, **params)` and `notify(user, template_name, /, **params)`, the leading arguments are positional-only. That means a template can use `{name}` or `{user}`. Otherwise `render("welcome", name="Ada")` would fail with a `TypeError`. The trade-off is that `notify(user=..., template_name=...)` can't be called with keywords.
- **Empty addresses count as missing.** An empty string is treated like `None`, so that channel is skipped.
- **Positional placeholders raise `ValueError`.** Templates with `{}` or `{0}` raise `ValueError`, the same as a missing parameter, because keyword arguments can never fill them.
- **`preferred_channels` is copied.** The `User` takes a copy, so later changes to the caller's list don't affect it. Each user also gets its own default `["email"]` list.
- **Subclasses of `DeliveryError` are retried.** Any other exception stops `notify` straight away, with no retry.
- **Duplicate channels are not removed.** If the preference list names a channel twice, it gets a second round of attempts. The spec says to go through the list in order, so I followed it literally.
- **No validation or delays beyond the spec.** There is no wait between retries and no check that `senders` keys are known channels. The only constructor check is `max_retries < 0`.
- **Partial attempts are lost on other errors.** When an exception other than `DeliveryError` stops `notify`, no report is returned, so the attempts made up to that point aren't reported.

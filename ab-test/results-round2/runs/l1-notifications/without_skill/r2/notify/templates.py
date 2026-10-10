"""Named message templates."""


class TemplateStore:
    """Stores templates that use `str.format` style `{param}` placeholders."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store `text` under `name`, replacing any template with that name."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill the template `name` with `params`.

        `name` is positional-only so a template may itself use a `{name}`
        placeholder.

        Raises:
            KeyError: no template is stored under `name`.
            ValueError: a placeholder has no matching parameter.
        """
        try:
            text = self._templates[name]
        except KeyError:
            raise KeyError(f"unknown template: {name!r}") from None
        try:
            return text.format(**params)
        except (KeyError, IndexError) as exc:
            raise ValueError(f"missing parameter for template {name!r}: {exc}") from exc

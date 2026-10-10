"""Named message templates using ``str.format`` placeholders."""


class TemplateStore:
    """Holds templates by name and renders them with keyword parameters."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store ``text`` under ``name``, replacing any existing template."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill the template ``name`` with ``params``.

        ``name`` is positional-only, so a template may use a ``{name}`` placeholder.

        Raises:
            KeyError: no template is stored under ``name``.
            ValueError: a placeholder has no matching parameter.
        """
        text = self._templates[name]
        try:
            return text.format(**params)
        except (KeyError, IndexError) as exc:
            # IndexError comes from positional placeholders such as "{}" or "{0}",
            # which keyword parameters can never fill.
            raise ValueError(
                f"missing parameter for template {name!r}: {exc}"
            ) from exc

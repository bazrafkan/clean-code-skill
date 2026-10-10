"""Named message templates using ``str.format`` placeholders."""


class TemplateStore:
    """Stores templates by name and renders them with keyword parameters."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store ``text`` under ``name``, replacing any existing template."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill the template ``name`` with ``params``.

        ``name`` is positional-only so that a template may itself use a
        ``{name}`` placeholder.

        Raises:
            KeyError: no template is stored under ``name``.
            ValueError: the template needs a parameter that was not given.
        """
        text = self._templates[name]
        try:
            return text.format(**params)
        except (KeyError, IndexError) as missing:
            raise ValueError(
                f"Template {name!r} is missing parameter {missing}"
            ) from missing

"""Named message templates."""


class TemplateStore:
    """Stores templates that use ``str.format``-style ``{param}`` placeholders."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store ``text`` under ``name``, replacing any template with that name."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill the template ``name`` with ``params``.

        ``name`` is positional-only so that templates may use ``{name}``.
        Raises KeyError if no template has that name, and ValueError if a
        placeholder has no matching parameter.
        """
        try:
            text = self._templates[name]
        except KeyError:
            raise KeyError(f"unknown template: {name!r}") from None
        try:
            return text.format(**params)
        except (KeyError, IndexError) as error:
            # IndexError comes from positional placeholders ("{}", "{0}"),
            # which can never be filled because only keyword params are accepted.
            raise ValueError(f"template {name!r} is missing a parameter: {error}") from error

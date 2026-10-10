"""Named message templates with ``str.format``-style ``{param}`` placeholders."""


class TemplateStore:
    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store ``text`` under ``name``, replacing any template of that name."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill template ``name`` with ``params``.

        Raises KeyError for an unknown template, ValueError for a missing parameter.
        """
        # name is positional-only so templates may use a {name} placeholder.
        template = self._template(name)
        try:
            return template.format(**params)
        except KeyError as error:
            raise ValueError(
                f"template {name!r} is missing parameter {error}"
            ) from error

    def _template(self, name: str) -> str:
        if name not in self._templates:
            raise KeyError(f"unknown template {name!r}")
        return self._templates[name]

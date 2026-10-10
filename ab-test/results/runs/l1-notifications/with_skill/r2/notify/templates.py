class TemplateStore:
    """Named message templates with `str.format`-style `{param}` placeholders."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store `text` as template `name`, replacing any template of that name."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill template `name` with `params`.

        Raises KeyError for an unknown template and ValueError for a placeholder
        without a matching parameter.
        """
        if name not in self._templates:
            raise KeyError(f"Unknown template {name!r}")
        try:
            return self._templates[name].format(**params)
        except KeyError as error:
            missing_param = error.args[0]
            raise ValueError(
                f"Template {name!r} needs parameter {missing_param!r}"
            ) from error

class TemplateStore:
    """Named message templates with str.format-style {param} placeholders."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Raises KeyError for an unknown template and ValueError for a missing parameter."""
        template = self._templates[name]
        try:
            return template.format(**params)
        except KeyError as missing:
            raise ValueError(
                f"template {name!r} needs parameter {missing.args[0]!r}"
            ) from missing

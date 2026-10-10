class TemplateStore:
    """Named message templates with `str.format`-style `{param}` placeholders."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill template `name`. Raises KeyError if it is unknown, ValueError if a parameter is missing."""
        template = self._templates[name]
        try:
            return template.format(**params)
        except KeyError as error:
            missing_param = error.args[0]
            raise ValueError(f"template {name!r} needs parameter {missing_param!r}") from error

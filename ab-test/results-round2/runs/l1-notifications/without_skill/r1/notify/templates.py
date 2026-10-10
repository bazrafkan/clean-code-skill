"""Named message templates with `{param}` placeholders."""


class TemplateStore:
    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store `text` under `name`, replacing any template already there."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill template `name` with `params`.

        `name` is positional-only so a template can use a `{name}` placeholder.
        Raises KeyError if no template is called `name`, and ValueError if
        the template needs a parameter that was not given.
        """
        try:
            template = self._templates[name]
        except KeyError:
            raise KeyError(f"unknown template: {name!r}") from None

        try:
            return template.format_map(params)
        except KeyError as exc:
            raise ValueError(
                f"template {name!r} is missing parameter {exc.args[0]!r}"
            ) from exc

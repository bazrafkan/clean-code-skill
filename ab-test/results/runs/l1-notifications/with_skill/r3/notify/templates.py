class TemplateStore:
    """Named message templates with `str.format`-style `{param}` placeholders."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store `text` under `name`, replacing any template already stored there."""
        self._templates[name] = text

    def render(self, name: str, /, **params: object) -> str:
        """Fill the template called `name` with `params`.

        `name` is positional-only, so a template may have a `{name}` placeholder.
        Raises KeyError if no template has that name, and ValueError if the
        template needs a parameter that was not given.
        """
        template = self._templates.get(name)
        if template is None:
            raise KeyError(f"unknown template {name!r}")
        try:
            return template.format(**params)
        # A positional placeholder such as `{0}` raises IndexError: render() takes
        # keyword parameters only, so that parameter can never be given.
        except (KeyError, IndexError) as missing:
            raise ValueError(
                f"cannot render template {name!r}, a parameter is missing: {missing}"
            ) from missing

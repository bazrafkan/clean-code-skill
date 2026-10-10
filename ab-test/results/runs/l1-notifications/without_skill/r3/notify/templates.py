"""Named message templates using ``str.format`` placeholders."""

from __future__ import annotations

from typing import Any


class TemplateStore:
    """Stores message templates by name and renders them with parameters."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}

    def add(self, name: str, text: str) -> None:
        """Store ``text`` under ``name``, replacing any existing template."""
        self._templates[name] = text

    def render(self, name: str, /, **params: Any) -> str:
        """Fill the template ``name`` with ``params``.

        ``name`` is positional-only so that templates can use a ``{name}``
        placeholder.

        Raises:
            KeyError: no template is stored under ``name``.
            ValueError: the template needs a parameter that was not given.
        """
        if name not in self._templates:
            raise KeyError(f"Unknown template: {name!r}")
        text = self._templates[name]
        try:
            return text.format(**params)
        except (KeyError, IndexError) as missing:
            # str.format raises KeyError for a missing {name} and IndexError
            # for a positional {0}, which can never be filled by keywords.
            raise ValueError(
                f"Template {name!r} is missing a parameter: {missing}"
            ) from missing

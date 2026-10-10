import pytest

from notify import TemplateStore


@pytest.fixture
def templates() -> TemplateStore:
    store = TemplateStore()
    store.add("welcome", "Hello {name}, welcome to {place}!")
    return store


def test_render_fills_the_placeholders(templates: TemplateStore) -> None:
    message = templates.render("welcome", name="Alice", place="Bergamo")

    assert message == "Hello Alice, welcome to Bergamo!"


def test_render_ignores_extra_parameters(templates: TemplateStore) -> None:
    message = templates.render("welcome", name="Alice", place="Bergamo", unused=1)

    assert message == "Hello Alice, welcome to Bergamo!"


def test_add_replaces_a_template_with_the_same_name(templates: TemplateStore) -> None:
    templates.add("welcome", "Hi {name}")

    assert templates.render("welcome", name="Alice") == "Hi Alice"


def test_render_unknown_template_raises_key_error(templates: TemplateStore) -> None:
    with pytest.raises(KeyError, match="goodbye"):
        templates.render("goodbye", name="Alice")


def test_render_missing_parameter_raises_value_error_naming_it(
    templates: TemplateStore,
) -> None:
    with pytest.raises(ValueError, match="place"):
        templates.render("welcome", name="Alice")

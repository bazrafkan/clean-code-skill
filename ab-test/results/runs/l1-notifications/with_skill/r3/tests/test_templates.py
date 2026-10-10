import pytest

from notify import TemplateStore


def test_render_fills_placeholders() -> None:
    store = TemplateStore()
    store.add("welcome", "Hi {name}, your code is {code}.")

    assert (
        store.render("welcome", name="Alice", code=42) == "Hi Alice, your code is 42."
    )


def test_add_replaces_a_template_with_the_same_name() -> None:
    store = TemplateStore()
    store.add("welcome", "Hi {name}!")

    store.add("welcome", "Welcome, {name}.")

    assert store.render("welcome", name="Alice") == "Welcome, Alice."


def test_render_rejects_an_unknown_template() -> None:
    store = TemplateStore()

    with pytest.raises(KeyError, match="welcome"):
        store.render("welcome")


def test_render_rejects_a_missing_parameter() -> None:
    store = TemplateStore()
    store.add("welcome", "Hi {name}!")

    with pytest.raises(ValueError, match="name"):
        store.render("welcome", nickname="Ali")


def test_render_treats_a_positional_placeholder_as_a_missing_parameter() -> None:
    store = TemplateStore()
    store.add("welcome", "Hi {0}!")

    with pytest.raises(ValueError, match="parameter is missing"):
        store.render("welcome", name="Alice")

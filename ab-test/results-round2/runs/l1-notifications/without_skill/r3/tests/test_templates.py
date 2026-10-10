import pytest

from notify import TemplateStore


@pytest.fixture
def store():
    templates = TemplateStore()
    templates.add("welcome", "Hello {name}, welcome to {site}!")
    return templates


def test_render_fills_placeholders(store):
    assert store.render("welcome", name="Ada", site="Notify") == "Hello Ada, welcome to Notify!"


def test_render_ignores_extra_parameters(store):
    assert store.render("welcome", name="Ada", site="X", unused=1) == "Hello Ada, welcome to X!"


def test_unknown_template_raises_key_error(store):
    with pytest.raises(KeyError):
        store.render("missing", name="Ada")


def test_missing_parameter_raises_value_error(store):
    with pytest.raises(ValueError, match="site"):
        store.render("welcome", name="Ada")


def test_positional_placeholder_raises_value_error(store):
    store.add("positional", "Hi {}")

    with pytest.raises(ValueError):
        store.render("positional")


def test_add_replaces_existing_template(store):
    store.add("welcome", "Hi {name}")

    assert store.render("welcome", name="Ada") == "Hi Ada"

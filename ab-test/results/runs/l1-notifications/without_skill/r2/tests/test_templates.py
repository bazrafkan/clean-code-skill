import pytest

from notify import TemplateStore


@pytest.fixture
def store():
    templates = TemplateStore()
    templates.add("welcome", "Hi {name}, welcome to {product}!")
    return templates


def test_render_fills_placeholders(store):
    assert store.render("welcome", name="Ada", product="Notify") == "Hi Ada, welcome to Notify!"


def test_add_replaces_existing_template(store):
    store.add("welcome", "Hello {name}")

    assert store.render("welcome", name="Ada") == "Hello Ada"


def test_unknown_template_raises_key_error(store):
    with pytest.raises(KeyError):
        store.render("missing")


def test_missing_parameter_raises_value_error(store):
    with pytest.raises(ValueError, match="name"):
        store.render("welcome", product="Notify")


def test_positional_placeholder_raises_value_error():
    store = TemplateStore()
    store.add("positional", "Code: {}")

    with pytest.raises(ValueError):
        store.render("positional")

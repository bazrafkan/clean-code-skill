import pytest

from notify import TemplateStore


@pytest.fixture
def store():
    store = TemplateStore()
    store.add("welcome", "Hello {name}, welcome to {site}!")
    return store


def test_render_fills_placeholders(store):
    assert store.render("welcome", name="Ann", site="Acme") == "Hello Ann, welcome to Acme!"


def test_render_ignores_extra_params(store):
    assert store.render("welcome", name="Ann", site="Acme", unused=1) == "Hello Ann, welcome to Acme!"


def test_render_without_placeholders():
    store = TemplateStore()
    store.add("ping", "ping")
    assert store.render("ping") == "ping"


def test_add_replaces_existing_template(store):
    store.add("welcome", "Hi {name}")
    assert store.render("welcome", name="Ann") == "Hi Ann"


def test_unknown_template_raises_key_error(store):
    with pytest.raises(KeyError):
        store.render("nope")


def test_missing_parameter_raises_value_error(store):
    with pytest.raises(ValueError, match="site"):
        store.render("welcome", name="Ann")


def test_positional_placeholder_raises_value_error():
    store = TemplateStore()
    store.add("bad", "Hello {}")
    with pytest.raises(ValueError):
        store.render("bad")

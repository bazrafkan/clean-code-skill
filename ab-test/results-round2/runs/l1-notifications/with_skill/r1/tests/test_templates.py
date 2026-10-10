import pytest

from notify import TemplateStore


@pytest.fixture
def store() -> TemplateStore:
    store = TemplateStore()
    store.add("welcome", "Hi {name}, welcome to {place}!")
    return store


def test_render_fills_placeholders_including_one_called_name(store):
    assert store.render("welcome", name="Ada", place="Bergamo") == "Hi Ada, welcome to Bergamo!"


def test_render_unknown_template_raises_key_error(store):
    with pytest.raises(KeyError):
        store.render("goodbye", name="Ada")


def test_render_missing_parameter_raises_value_error(store):
    with pytest.raises(ValueError, match="place"):
        store.render("welcome", name="Ada")

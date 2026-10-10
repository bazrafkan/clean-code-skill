import pytest

from notify import TemplateStore


@pytest.fixture
def templates():
    store = TemplateStore()
    store.add("welcome", "Hello {name}, welcome to {product}!")
    return store


def test_render_fills_the_placeholders(templates):
    assert templates.render("welcome", name="Ada", product="Notify") == "Hello Ada, welcome to Notify!"


def test_render_raises_key_error_for_an_unknown_template(templates):
    with pytest.raises(KeyError):
        templates.render("goodbye", name="Ada")


def test_render_raises_value_error_naming_the_missing_parameter(templates):
    with pytest.raises(ValueError, match="product"):
        templates.render("welcome", name="Ada")

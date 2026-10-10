import pytest

from notify import TemplateStore


@pytest.fixture
def store() -> TemplateStore:
    store = TemplateStore()
    store.add("welcome", "Hi {first_name}, welcome to {product}!")
    return store


def test_render_fills_every_placeholder(store: TemplateStore) -> None:
    rendered = store.render("welcome", first_name="Ada", product="Notify")

    assert rendered == "Hi Ada, welcome to Notify!"


def test_render_accepts_a_parameter_called_name() -> None:
    store = TemplateStore()
    store.add("greeting", "Hello {name}")

    assert store.render("greeting", name="Ada") == "Hello Ada"


def test_add_replaces_a_template_with_the_same_name(store: TemplateStore) -> None:
    store.add("welcome", "Welcome back, {first_name}")

    assert store.render("welcome", first_name="Ada") == "Welcome back, Ada"


def test_render_of_unknown_template_raises_key_error(store: TemplateStore) -> None:
    with pytest.raises(KeyError, match="goodbye"):
        store.render("goodbye")


def test_render_with_missing_parameter_raises_value_error(
    store: TemplateStore,
) -> None:
    with pytest.raises(ValueError, match="product"):
        store.render("welcome", first_name="Ada")

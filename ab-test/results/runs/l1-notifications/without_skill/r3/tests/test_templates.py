import pytest

from notify import TemplateStore


@pytest.fixture
def store():
    store = TemplateStore()
    store.add("welcome", "Hello {name}, welcome to {place}!")
    return store


def test_render_fills_placeholders(store):
    assert store.render("welcome", name="Ada", place="Bergamo") == (
        "Hello Ada, welcome to Bergamo!"
    )


def test_name_placeholder_does_not_clash_with_template_name():
    store = TemplateStore()
    store.add("greet", "Hi {name}")
    assert store.render("greet", name="Ada") == "Hi Ada"


def test_extra_parameters_are_ignored(store):
    assert store.render("welcome", name="Ada", place="Rome", unused=1) == (
        "Hello Ada, welcome to Rome!"
    )


def test_adding_a_template_again_replaces_it(store):
    store.add("welcome", "Hi {name}")
    assert store.render("welcome", name="Ada") == "Hi Ada"


def test_unknown_template_raises_key_error(store):
    with pytest.raises(KeyError):
        store.render("missing")


def test_missing_parameter_raises_value_error(store):
    with pytest.raises(ValueError, match="name"):
        store.render("welcome", place="Rome")


def test_missing_parameter_is_not_a_key_error(store):
    with pytest.raises(ValueError) as excinfo:
        store.render("welcome", place="Rome")
    assert not isinstance(excinfo.value, KeyError)


def test_positional_placeholder_raises_value_error():
    store = TemplateStore()
    store.add("positional", "Code {0}")
    with pytest.raises(ValueError):
        store.render("positional", code=1)

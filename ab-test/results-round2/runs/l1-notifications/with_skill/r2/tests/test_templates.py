import pytest

from notify import TemplateStore


def store_with(name: str, text: str) -> TemplateStore:
    templates = TemplateStore()
    templates.add(name, text)
    return templates


def test_render_fills_placeholders():
    templates = store_with("order", "Order {order_id} ships on {day}")

    assert templates.render("order", order_id=42, day="Monday") == "Order 42 ships on Monday"


def test_render_accepts_a_parameter_called_name():
    templates = store_with("welcome", "Hello {name}")

    assert templates.render("welcome", name="Ann") == "Hello Ann"


def test_render_raises_key_error_for_unknown_template():
    with pytest.raises(KeyError):
        TemplateStore().render("missing")


def test_render_raises_value_error_for_missing_parameter():
    templates = store_with("welcome", "Hello {name}")

    with pytest.raises(ValueError, match="name"):
        templates.render("welcome")

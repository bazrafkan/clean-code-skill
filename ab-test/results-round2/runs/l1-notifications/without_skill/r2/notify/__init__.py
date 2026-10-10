"""Send a templated message to a user through their preferred channels.

Senders are injected: any object with `send(address, message) -> None` that
raises `DeliveryError` on failure.
"""

from notify.errors import DeliveryError
from notify.service import DeliveryReport, NotificationService, Sender
from notify.templates import TemplateStore
from notify.user import User

__all__ = [
    "DeliveryError",
    "DeliveryReport",
    "NotificationService",
    "Sender",
    "TemplateStore",
    "User",
]

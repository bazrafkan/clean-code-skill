"""Send a message to a user on their preferred channels, with retries and fallback."""

from notify.report import DeliveryReport
from notify.sender import DeliveryError
from notify.service import NotificationService
from notify.templates import TemplateStore
from notify.user import User

__all__ = [
    "DeliveryError",
    "DeliveryReport",
    "NotificationService",
    "TemplateStore",
    "User",
]

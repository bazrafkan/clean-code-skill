"""Send a templated message to a user over their preferred channels, with retries and fallback."""

from notify.report import Attempt, DeliveryReport
from notify.senders import DeliveryError, Sender
from notify.service import NotificationService
from notify.templates import TemplateStore
from notify.user import User

__all__ = [
    "Attempt",
    "DeliveryError",
    "DeliveryReport",
    "NotificationService",
    "Sender",
    "TemplateStore",
    "User",
]

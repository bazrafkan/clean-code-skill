"""Send a message to a user over their preferred channels, with retries and fallback."""

from .report import DeliveryReport
from .sender import DeliveryError
from .service import NotificationService
from .templates import TemplateStore
from .user import User

__all__ = [
    "DeliveryError",
    "DeliveryReport",
    "NotificationService",
    "TemplateStore",
    "User",
]

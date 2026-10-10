"""Send templated messages to users over their preferred channels.

Senders for each channel are injected; a sender raises ``DeliveryError`` when
delivery fails, which triggers retries and then fallback to the next channel.
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

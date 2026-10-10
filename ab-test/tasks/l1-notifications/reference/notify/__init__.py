from dataclasses import dataclass, field
from string import Formatter


class DeliveryError(Exception):
    pass


_ADDRESS_FIELD = {"email": "email", "sms": "phone", "push": "push_token"}


@dataclass
class User:
    id: str
    email: str = None
    phone: str = None
    push_token: str = None
    preferred_channels: list = None

    def __post_init__(self):
        if self.preferred_channels is None:
            self.preferred_channels = ["email"]

    def address_for(self, channel):
        field_name = _ADDRESS_FIELD.get(channel)
        return getattr(self, field_name) if field_name else None


class TemplateStore:
    def __init__(self):
        self._templates = {}

    def add(self, name, text):
        self._templates[name] = text

    def render(self, name, **params):
        text = self._templates[name]
        try:
            return text.format(**params)
        except KeyError as missing:
            raise ValueError(f"missing parameter {missing}") from None


@dataclass
class DeliveryReport:
    delivered: bool
    channel: str = None
    attempts: list = field(default_factory=list)


class NotificationService:
    def __init__(self, senders, templates, max_retries=2):
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._senders = senders
        self._templates = templates
        self._max_retries = max_retries

    def notify(self, user, template_name, **params):
        message = self._templates.render(template_name, **params)
        attempts = []
        for channel in user.preferred_channels:
            sender = self._senders.get(channel)
            address = user.address_for(channel)
            if sender is None or not address:
                continue
            for _ in range(1 + self._max_retries):
                try:
                    sender.send(address, message)
                except DeliveryError:
                    attempts.append((channel, False))
                    continue
                attempts.append((channel, True))
                return DeliveryReport(True, channel, attempts)
        return DeliveryReport(False, None, attempts)

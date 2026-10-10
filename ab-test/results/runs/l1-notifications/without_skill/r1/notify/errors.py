"""Exceptions raised by the notify package and by the senders it drives."""


class DeliveryError(Exception):
    """Raised by a sender when a message could not be delivered.

    The service treats this as a recoverable failure: it retries the same
    channel and then falls back to the next one. Any other exception raised
    by a sender is considered a bug and propagates to the caller.
    """

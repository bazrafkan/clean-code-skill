"""Exceptions raised by the notify package and by its senders."""


class DeliveryError(Exception):
    """Raised by a sender when a message could not be delivered.

    The notification service treats this error as retryable: it retries the
    same channel and then falls back to the next one. Any other exception
    raised by a sender is treated as a bug and propagates to the caller.
    """

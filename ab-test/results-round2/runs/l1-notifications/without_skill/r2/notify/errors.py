"""Exceptions raised by the notify package."""


class DeliveryError(Exception):
    """Raised by a sender when it cannot deliver a message.

    The service treats it as an expected failure: it retries the channel and
    then falls back to the next one. Any other exception from a sender is not
    handled and propagates to the caller.
    """

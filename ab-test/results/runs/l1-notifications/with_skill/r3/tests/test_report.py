import pytest

from notify import DeliveryReport


@pytest.mark.parametrize(("delivered", "channel"), [(True, None), (False, "email")])
def test_rejects_a_channel_that_contradicts_delivered(
    delivered: bool, channel: str | None
) -> None:
    with pytest.raises(ValueError, match="channel"):
        DeliveryReport(delivered=delivered, channel=channel, attempts=[])

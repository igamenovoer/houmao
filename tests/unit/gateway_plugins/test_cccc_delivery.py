"""Deterministic tests for delivery boundaries and stream backpressure."""

from __future__ import annotations

import pytest

from houmao_cccc.delivery import ChatOffer, DeliveryBuffer, DeliverySettings


def _offer(seq: int, size: int = 100) -> ChatOffer:
    """Build one provider-ordered offer with a fixed original timestamp."""

    return ChatOffer(
        str(seq), str(seq), seq, "peer", "2026-11-25T10:30:02Z", "send", "Hi", 60.0, size
    )


def test_push_deadlines_and_duplicates_preserve_exact_boundaries() -> None:
    """A duplicate cannot move the quiet deadline, and equality closes the batch."""

    settings = DeliverySettings(transport="push", push_policy="batch", quiet_interval=2, max_wait=5)
    buffer = DeliveryBuffer.from_settings(settings, max_count=8, max_bytes=1000)
    buffer.stage([_offer(1)], 0.0)
    buffer.stage([_offer(2)], 1.0)
    buffer.stage([_offer(2)], 2.99)
    assert buffer.deadline == 3.0
    buffer.stage([_offer(3)], 3.0)
    first = buffer.head
    assert first == (_offer(1), _offer(2))
    assert buffer.deadline == 5.0
    buffer.stage([_offer(4)], 4.5)
    buffer.stage([_offer(5)], 6.0)
    buffer.stage([_offer(6)], 7.5)
    assert buffer.deadline == 8.0
    buffer.close_due(8.0)
    assert first is not None
    buffer.finish(first)
    assert buffer.head == tuple(map(_offer, (3, 4, 5, 6)))


def test_pull_snapshots_and_capacity_account_for_queued_wait() -> None:
    """Independent pulls seal independently and only settlement returns credit."""

    buffer = DeliveryBuffer.from_settings(DeliverySettings(), max_count=3, max_bytes=300)
    buffer.stage([_offer(1), _offer(2)], 0)
    buffer.stage([_offer(3)], 0)
    assert buffer.credit == (0, 0)
    with pytest.raises(ValueError, match="exceed staging credit"):
        buffer.stage([_offer(4)], 1)
    assert buffer.highest_sequence == 3
    first = buffer.head
    assert first == (_offer(1), _offer(2))
    assert first is not None
    buffer.finish(first)
    assert buffer.head == (_offer(3),)
    assert buffer.credit == (2, 200)


def test_policy_edit_seals_the_open_batch() -> None:
    """A current run's old policy still governs the batch already open."""

    settings = DeliverySettings(transport="push", push_policy="batch", quiet_interval=2, max_wait=5)
    buffer = DeliveryBuffer.from_settings(settings, max_count=8, max_bytes=1000)
    buffer.stage([_offer(1)], 0)
    buffer.configure(DeliverySettings(transport="push", push_policy="asap"))
    buffer.stage([_offer(2), _offer(3)], 0.1)
    for expected in (_offer(1), _offer(2), _offer(3)):
        actual = buffer.head
        assert actual == (expected,)
        assert actual is not None
        buffer.finish(actual)

"""Tests for the mailbox demo fixture."""

from mailbox_demo import compose_status_note


def test_compose_status_note_is_deterministic() -> None:
    """The helper should return the tracked fixture wording."""

    assert (
        compose_status_note("reply review")
        == "Status: reply review is ready for the next mailbox turn."
    )

"""Tests for the gateway notifier notify-block slot renderer."""

from __future__ import annotations

from collections.abc import Sequence

from houmao.agents.realm_controller.gateway_service import (
    _RenderedNotifyBlockEntry,
    _UnreadMailboxMessage,
    _render_notify_block_slots,
)
from houmao.agents.realm_controller.gateway_storage import GatewayMailNotifierRecord
from houmao.mailbox.protocol import MailboxNotifyAuth, MailboxNotifyBlock


def _record(
    *,
    notify_block_render: str = "enabled",
    notify_block_auth_mode: str = "permissive-log",
    notify_block_auth_verifier: str = "none",
    notify_block_shared_tokens: tuple[str, ...] = (),
    notify_block_per_message_chars: int = 512,
    notify_block_total_chars: int = 2048,
) -> GatewayMailNotifierRecord:
    return GatewayMailNotifierRecord(
        enabled=True,
        interval_seconds=5,
        mode="any_inbox",
        appendix_text="",
        context_error_policy="continue_current",
        pre_notification_context_action="none",
        last_poll_at_utc=None,
        last_notification_at_utc=None,
        last_notified_digest=None,
        compacted_eligible_message_refs=(),
        last_error=None,
        notify_block_render=notify_block_render,  # type: ignore[arg-type]
        notify_block_auth_mode=notify_block_auth_mode,  # type: ignore[arg-type]
        notify_block_auth_verifier=notify_block_auth_verifier,  # type: ignore[arg-type]
        notify_block_shared_tokens=notify_block_shared_tokens,
        notify_block_per_message_chars=notify_block_per_message_chars,
        notify_block_total_chars=notify_block_total_chars,
    )


def _msg(
    *,
    message_ref: str,
    created_at_utc: str = "2026-04-27T12:00:00Z",
    sender_address: str = "alice@houmao.localhost",
    subject: str = "hello",
    notify_block: MailboxNotifyBlock | None = None,
    notify_auth: MailboxNotifyAuth | None = None,
) -> _UnreadMailboxMessage:
    return _UnreadMailboxMessage(
        message_ref=message_ref,
        thread_ref=None,
        created_at_utc=created_at_utc,
        sender_address=sender_address,
        sender_display_name=None,
        subject=subject,
        notify_block=notify_block,
        notify_auth=notify_auth,
    )


def _entry_for(
    entries: Sequence[_RenderedNotifyBlockEntry], message_ref: str
) -> _RenderedNotifyBlockEntry:
    return next(e for e in entries if e.message_ref == message_ref)


def test_render_returns_empty_slots_when_no_messages_have_notify_block() -> None:
    record = _record()
    messages = [_msg(message_ref="filesystem:msg-a")]

    prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert prepend == ""
    assert append == ""
    assert entries == []


def test_render_single_append_block_renders_after_inbox_opener_slot() -> None:
    record = _record()
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            sender_address="HOUMAO-operator@houmao.localhost",
            notify_block=MailboxNotifyBlock(text="continue current task", placement="append"),
        )
    ]

    prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert prepend == ""
    assert "continue current task" in append
    assert "Sender notice — from HOUMAO-operator@houmao.localhost" in append
    assert append.startswith("\n\n")  # appended after the opener block
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is True
    assert rendered.auth_scheme == "none"
    assert rendered.auth_outcome == "skipped"
    assert rendered.block_chars == len("continue current task")
    assert rendered.block_truncated is False


def test_render_single_prepend_block_renders_before_inbox_opener_slot() -> None:
    record = _record()
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            sender_address="HOUMAO-operator@houmao.localhost",
            notify_block=MailboxNotifyBlock(text="OPERATOR DIRECTIVE", placement="prepend"),
        )
    ]

    prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert append == ""
    assert "OPERATOR DIRECTIVE" in prepend
    assert prepend.endswith("\n\n")  # prepended before the opener block
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is True


def test_render_multiple_blocks_cluster_by_placement_oldest_first() -> None:
    record = _record()
    older_prepend = _msg(
        message_ref="filesystem:msg-older-prepend",
        created_at_utc="2026-04-27T12:00:00Z",
        sender_address="agent-a@houmao.localhost",
        notify_block=MailboxNotifyBlock(text="A-prepend", placement="prepend"),
    )
    newer_prepend = _msg(
        message_ref="filesystem:msg-newer-prepend",
        created_at_utc="2026-04-27T12:05:00Z",
        sender_address="agent-b@houmao.localhost",
        notify_block=MailboxNotifyBlock(text="B-prepend", placement="prepend"),
    )
    older_append = _msg(
        message_ref="filesystem:msg-older-append",
        created_at_utc="2026-04-27T12:01:00Z",
        sender_address="agent-c@houmao.localhost",
        notify_block=MailboxNotifyBlock(text="C-append", placement="append"),
    )
    newer_append = _msg(
        message_ref="filesystem:msg-newer-append",
        created_at_utc="2026-04-27T12:06:00Z",
        sender_address="agent-d@houmao.localhost",
        notify_block=MailboxNotifyBlock(text="D-append", placement="append"),
    )

    prepend, append, entries = _render_notify_block_slots(
        # Caller-side order is mixed; renderer is responsible for ordering by
        # the timestamps inside each placement cluster.
        unread_messages=[older_prepend, older_append, newer_prepend, newer_append],
        record=record,
    )

    # Prepend cluster: oldest first.
    assert prepend.find("A-prepend") < prepend.find("B-prepend")
    # Append cluster: oldest first.
    assert append.find("C-append") < append.find("D-append")
    # All four messages produced rendered audit entries.
    assert sum(1 for e in entries if e.rendered) == 4


def test_render_aggregate_cap_summarizes_overflow_with_plus_n_more_line() -> None:
    record = _record(notify_block_total_chars=180)
    # Each "Sender notice — from <address>:\n> <text>" entry runs ~70+ chars.
    # Three entries will exceed an aggregate cap of 180.
    messages = [
        _msg(
            message_ref=f"filesystem:msg-{i}",
            created_at_utc=f"2026-04-27T12:0{i}:00Z",
            sender_address=f"sender-{i}@houmao.localhost",
            notify_block=MailboxNotifyBlock(
                text=f"directive {i}",
                placement="append",
            ),
        )
        for i in range(5)
    ]

    _prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert "+ " in append and "more sender notice(s)" in append
    suppressed = [e for e in entries if not e.rendered]
    rendered = [e for e in entries if e.rendered]
    assert len(suppressed) >= 1
    assert len(rendered) >= 1
    for e in suppressed:
        assert e.auth_detail == "aggregate cap reached"


def test_render_per_message_cap_truncates_oversize_block_visibly() -> None:
    record = _record(notify_block_per_message_chars=20)
    long_text = "x" * 80
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            notify_block=MailboxNotifyBlock(text=long_text, placement="append"),
        )
    ]

    _prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert "…" in append
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is True
    assert rendered.block_truncated is True
    assert rendered.block_chars == 20


def test_render_disabled_short_circuits_with_skipped_audit_entries() -> None:
    record = _record(notify_block_render="disabled")
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            notify_block=MailboxNotifyBlock(text="anything", placement="append"),
        ),
        _msg(message_ref="filesystem:msg-b"),  # no notify_block
    ]

    prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert prepend == ""
    assert append == ""
    assert len(entries) == 1  # only the message with notify_block
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is False
    assert rendered.auth_outcome == "skipped"
    assert rendered.auth_detail == "render disabled"


def test_render_permissive_log_renders_despite_verifier_failure() -> None:
    record = _record(
        notify_block_auth_mode="permissive-log",
        notify_block_auth_verifier="shared-token",
        notify_block_shared_tokens=("only-this-token",),
    )
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            notify_block=MailboxNotifyBlock(text="renders anyway", placement="append"),
            notify_auth=MailboxNotifyAuth(scheme="none", token="not-the-allowlisted-token"),
        )
    ]

    _prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert "renders anyway" in append
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is True
    assert rendered.auth_outcome == "failed"
    assert rendered.auth_scheme == "shared-token"


def test_render_required_mode_suppresses_block_on_verifier_failure() -> None:
    record = _record(
        notify_block_auth_mode="required",
        notify_block_auth_verifier="shared-token",
        notify_block_shared_tokens=("only-this-token",),
    )
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            notify_block=MailboxNotifyBlock(text="should be suppressed", placement="append"),
            notify_auth=MailboxNotifyAuth(scheme="none", token="not-the-allowlisted-token"),
        )
    ]

    prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert prepend == ""
    assert append == ""
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is False
    assert rendered.auth_outcome == "failed"
    assert rendered.auth_scheme == "shared-token"


def test_render_required_mode_renders_when_verifier_passes() -> None:
    record = _record(
        notify_block_auth_mode="required",
        notify_block_auth_verifier="shared-token",
        notify_block_shared_tokens=("good-bearer",),
    )
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            notify_block=MailboxNotifyBlock(text="authorized note", placement="append"),
            notify_auth=MailboxNotifyAuth(scheme="none", token="good-bearer"),
        )
    ]

    _prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert "authorized note" in append
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is True
    assert rendered.auth_outcome == "passed"
    assert rendered.auth_scheme == "shared-token"


def test_render_permissive_log_with_no_notify_auth_records_skipped_outcome() -> None:
    record = _record(
        notify_block_auth_mode="permissive-log",
        notify_block_auth_verifier="none",
    )
    messages = [
        _msg(
            message_ref="filesystem:msg-a",
            notify_block=MailboxNotifyBlock(text="hello", placement="append"),
            notify_auth=None,
        )
    ]

    _prepend, append, entries = _render_notify_block_slots(unread_messages=messages, record=record)

    assert "hello" in append
    rendered = _entry_for(entries, "filesystem:msg-a")
    assert rendered.rendered is True
    assert rendered.auth_outcome == "skipped"
    assert rendered.auth_scheme == "none"

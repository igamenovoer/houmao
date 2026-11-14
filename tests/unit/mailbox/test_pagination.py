"""Bounded metadata pages, cursor isolation, and honest content limits."""

from pathlib import Path

from pydantic import ValidationError
import pytest

from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox
from houmao.mailbox.models import GatewayMailListRequestV1
from houmao.mailbox.pagination import MailboxCursorError, build_mail_page_response
from houmao.mailbox.scope import MailboxScopeError
from tests.unit.mailbox.test_scope import _adapter


def test_list_defaults_are_finite_and_removed_body_input_is_explicit() -> None:
    """Omitted limits get a finite default; unbounded/body-list inputs fail."""

    assert GatewayMailListRequestV1(expected_binding_id="selected").limit == 50
    for fields in ({"limit": None}, {"limit": 0}, {"limit": 201}, {"include_body": False}):
        with pytest.raises(ValidationError):
            GatewayMailListRequestV1.model_validate({"expected_binding_id": "selected", **fields})


def test_local_metadata_pages_have_scoped_continuation_and_page_counts(tmp_path: Path) -> None:
    """Bodies are bounded separately and stable pages visit every matching item."""

    bootstrap_filesystem_mailbox(tmp_path)
    sender = _adapter(tmp_path, "owner-a", "a@example.test")
    reader = _adapter(tmp_path, "owner-b", "b@example.test")
    for index in range(5):
        sender.send(
            to_addresses=["b@example.test"],
            cc_addresses=[],
            subject=f"Item {index}",
            body_content="large body " * 10000,
            attachments=[],
        )
    query = dict(box="inbox", read_state="any", answered_state="any", archived=False, limit=2)
    page = reader.list_page(**query)
    first_refs = {message.message_ref for message in page.messages}
    assert len(first_refs) == 2
    assert page.has_more and not page.complete
    assert all(
        message.body_text is None and len(message.body_preview or "") <= 512
        for message in page.messages
    )
    response = build_mail_page_response(identity=reader.status(), box="inbox", page=page)
    assert response.counts_scope == "page" and response.message_count == 2
    assert response.total_count is None
    second = reader.list_page(**query, cursor=page.next_cursor)
    last = reader.list_page(**query, cursor=second.next_cursor)
    assert last.complete and not last.has_more and last.next_cursor is None
    assert len(first_refs | {m.message_ref for m in second.messages + last.messages}) == 5
    content = reader.peek(message_ref=last.messages[0].message_ref, box=None)
    assert content.content_complete is False
    assert content.content_limit_bytes == 65536 and content.content_limit_reason
    assert len((content.body_text or "").encode()) <= 65536


def test_cursor_filter_owner_and_mutation_are_refused(tmp_path: Path) -> None:
    """A continuation cannot drift query policy, owner, or local metadata state."""

    bootstrap_filesystem_mailbox(tmp_path)
    reader = _adapter(tmp_path, "owner-a", "a@example.test")
    other = _adapter(tmp_path, "owner-b", "b@example.test")
    for index in range(3):
        reader.send(
            to_addresses=["a@example.test"],
            cc_addresses=[],
            subject=str(index),
            body_content="body",
            attachments=[],
        )
    query = dict(box="inbox", read_state="any", answered_state="any", archived=False, limit=1)
    first = reader.list_page(**query)
    with pytest.raises(MailboxCursorError, match="another query|Invalid continuation"):
        reader.list_page(**{**query, "read_state": "unread"}, cursor=first.next_cursor)
    with pytest.raises(MailboxScopeError):
        other.list_page(**query, cursor=first.next_cursor)
    reader.mark(
        message_refs=[first.messages[0].message_ref], read=True, answered=None, archived=None
    )
    with pytest.raises(MailboxCursorError) as raised:
        reader.list_page(**query, cursor=first.next_cursor)
    assert raised.value.error_code == "stale_mail_cursor"


@pytest.mark.parametrize("since", ["2026-11-14T00:00:00", "bad-timestamp"])
def test_offline_since_requires_explicit_timezone(tmp_path: Path, since: str) -> None:
    """Both channels reject ambiguous timestamp boundaries before metadata paging."""

    from houmao.mailbox.services import GatewayMailboxUnsupportedError

    bootstrap_filesystem_mailbox(tmp_path)
    reader = _adapter(tmp_path, "owner", "a@example.test")
    with pytest.raises(GatewayMailboxUnsupportedError, match="since"):
        reader.list_page(
            box="inbox", read_state="any", answered_state="any", archived=False, since=since
        )

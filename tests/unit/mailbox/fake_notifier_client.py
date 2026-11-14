"""Hermetic metadata-only provider for gateway notifier scheduling regressions."""

from __future__ import annotations

from dataclasses import asdict
from collections.abc import Iterator
from contextlib import contextmanager
import json
from typing import Any

from houmao.mailbox.stalwart_models import (
    JmapEmailChanges,
    JmapMetadataBatch,
    JmapMetadataPage,
    JmapMetadataQuery,
    JmapOperationMeter,
    ValidatedJmapBinding,
)


class FakeNotifierJmapClient:
    """Keep a constant provider view while exercising real durable sync and fences."""

    def __init__(self, **kwargs: Any) -> None:
        self.m_sender: str = kwargs.get("sender_address") or "HOUMAO-gpu@agents.localhost"
        self.method_call_count: int = 0
        self.max_objects_in_get: int = 200

    @contextmanager
    def operation_meter(
        self, *, max_method_calls: int | None = None, timeout_seconds: float | None = None
    ) -> Iterator[JmapOperationMeter]:
        """Count this deterministic fake operation, including explicit failures."""
        before = self.method_call_count
        meter = JmapOperationMeter(deadline=float("inf"), remaining_methods=max_method_calls)
        try:
            yield meter
        finally:
            meter.attempted_methods = self.method_call_count - before

    def validate_binding(self, *, sender_address: str | None = None) -> ValidatedJmapBinding:
        """Authorize the deliberately fake sender without network or secret discovery."""
        return ValidatedJmapBinding(
            "acc-1",
            "identity-1",
            sender_address or self.m_sender,
            "http://127.0.0.1/.well-known/jmap",
            "http://127.0.0.1/jmap/",
            {},
            {"inbox": "inbox", "sent": "sent", "archive": "archive", "drafts": "drafts"},
            200,
            16,
        )

    def status(self) -> dict[str, str]:
        """Return only the fake selected account."""
        return {"account_id": "acc-1"}

    def primary_account_id(self) -> str:
        """Return the exact fixture account."""
        return "acc-1"

    def query_fingerprint(self, query: JmapMetadataQuery) -> str:
        """Match the exact fixture query policy, including notifier mode."""
        return json.dumps(asdict(query), sort_keys=True)

    def _message(self) -> dict[str, Any]:
        """Expose bounded metadata, never provider message content."""
        return {
            "id": "mail-1",
            "threadId": "thread-1",
            "receivedAt": "2026-03-19T08:00:00Z",
            "subject": "Stalwart unread notifier",
            "preview": "preview",
            "from": [{"email": "sender@agents.localhost"}],
            "to": [{"email": self.m_sender}],
            "cc": [],
            "replyTo": [],
            "unread": True,
            "read": False,
            "answered": False,
            "archived": False,
            "box": "inbox",
            "mailboxIds": {"inbox": True},
            "keywords": {},
        }

    def email_state(self, **kwargs: Any) -> str:
        """Count a finite state capture."""
        self.method_call_count += 1
        return "state-1"

    def query_metadata_page(self, *, query: JmapMetadataQuery, **kwargs: Any) -> JmapMetadataPage:
        """Return one eligible item and an authoritative complete query."""
        self.method_call_count += 2
        return JmapMetadataPage([self._message()], "query-1", 0, False, True, None, method_calls=2)

    def get_metadata(self, *, email_ids: Any, **kwargs: Any) -> JmapMetadataBatch:
        """Return authoritative missing IDs for any remembered absent items."""
        self.method_call_count += 1
        return JmapMetadataBatch(
            [self._message()] if "mail-1" in email_ids else [],
            [item for item in email_ids if item != "mail-1"],
            "state-1",
        )

    def changes(self, *, since_state: str, **kwargs: Any) -> JmapEmailChanges:
        """Observe unchanged mail without suppressing future due reminder cycles."""
        self.method_call_count += 1
        return JmapEmailChanges(since_state, "state-1", False, [], [], [])

    def metadata_matches_query(self, message: dict[str, Any], query: JmapMetadataQuery) -> bool:
        """Evaluate this fixture's single unchanged inbox item."""
        return message.get("id") == "mail-1"


def install_notifier_client(
    monkeypatch: Any, client_type: type[FakeNotifierJmapClient] = FakeNotifierJmapClient
) -> None:
    """Install the same explicit fixture at validation, authority, and raw boundaries."""
    for module in ("online_binding", "online_authority", "services"):
        monkeypatch.setattr(f"houmao.mailbox.{module}.StalwartJmapClient", client_type)

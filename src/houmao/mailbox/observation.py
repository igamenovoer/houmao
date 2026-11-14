"""Compose bounded online observation and compaction-eligibility revalidation.

The caller captures no terminal lock while this module contacts the provider. A
final immutable binding fence protects both cache publication and later admission.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
import json
import sqlite3
import time
from typing import Any, Literal

from houmao.mailbox.models import GatewayMailboxMessageV1
from houmao.mailbox.online_authority import OnlineConnectionAuthority
from houmao.mailbox.online_models import OnlineAuthorityContext, OnlineFence
from houmao.mailbox.scope import MailboxScopeError, MailScope
from houmao.mailbox.services import stalwart_message_to_model
from houmao.mailbox.stalwart import StalwartError
from houmao.mailbox.stalwart_models import JmapMetadataQuery
from houmao.mailbox.sync import SyncBudget, SyncObserver, SyncScope, SyncView


@dataclass(frozen=True)
class OnlineObservation:
    """Scoped notifier inputs with the fence required for atomic later admission."""

    messages: list[GatewayMailboxMessageV1]
    complete: bool
    confirmed_ineligible: tuple[str, ...]
    fence: OnlineFence
    authority: OnlineConnectionAuthority
    sync_view: SyncView


def observe_online(
    *,
    context: OnlineAuthorityContext,
    sqlite_path: Path,
    binding_id: str,
    mode: Literal["any_inbox", "unread_only"],
    compacted: Sequence[str] = (),
    budget: SyncBudget | None = None,
) -> OnlineObservation:
    """Observe metadata and revalidate remembered eligibility within one budget.

    Parameters
    ----------
    context : OnlineAuthorityContext
        Explicit runtime/owner authority, captured outside the terminal lock.
    sqlite_path : Path
        Gateway-owned database used for derived sync and round-robin progress.
    binding_id : str
        Expected online binding, never inferred from canonical mail identity.
    mode : str
        Exact notification mode, which forms part of the durable view scope.
    compacted : sequence of str
        Stable-order remembered scoped references. Eviction is never an eligibility
        loss. A bounded rotating subset is checked when method/time budget remains.
    budget : SyncBudget or None
        Shared observation/revalidation limits. Epoch initialization is separately
        finite and cached by the connection authority before this work begins.
    """
    if mode not in {"any_inbox", "unread_only"}:
        raise ValueError("online observation requires a supported notifier mode")
    limits = budget or SyncBudget()
    authority = OnlineConnectionAuthority.from_context(context)
    connection = authority.capture_connection(
        expected_binding_id=binding_id, timeout_seconds=limits.max_seconds
    )
    client = connection.client
    fence = connection.fence
    query = JmapMetadataQuery(
        box="inbox",
        read_state="unread" if mode == "unread_only" else "any",
        answered_state="any",
        archived=False,
    )
    scope = SyncScope.for_query(
        agent_id=context.agent_id,
        binding_id=binding_id,
        account_id=fence.account_id,
        query=query,
        client=client,
    )
    mail_scope = MailScope(context.agent_id, "online", binding_id)
    observer = SyncObserver.from_config(
        sqlite_path=sqlite_path,
        client=client,
        scope=scope,
        commit_guard=lambda callback: authority.commit_observation(fence, callback),
    )
    deadline = time.monotonic() + limits.max_seconds
    view = observer.observe(query, limits)
    lost = {mail_scope.encode("stalwart:" + email_id) for email_id in view.confirmed_ineligible}
    calls = view.method_calls
    old_position = _read_revalidation_position(sqlite_path, scope.key)
    position = old_position
    if view.phase not in {"degraded", "rebasing"} and not view.superseded and compacted:
        present = {str(message["id"]) for message in view.messages}
        remaining = max(0, limits.max_method_calls - calls)
        cap = min(max(1, client.max_objects_in_get), 200)
        # No full remembered-set scan: even very large eligibility sets yield work.
        scan_limit = min(len(compacted), cap * remaining + limits.max_cached_messages)
        scanned = 0
        while remaining > 0 and scanned < scan_limit and time.monotonic() < deadline:
            selected: dict[str, str] = {}
            while len(selected) < cap and scanned < scan_limit:
                reference = compacted[position % len(compacted)]
                position = (position + 1) % len(compacted)
                scanned += 1
                try:
                    raw = mail_scope.decode(reference)
                except MailboxScopeError:
                    continue
                if not raw.startswith("stalwart:"):
                    continue
                email_id = raw.removeprefix("stalwart:")
                if email_id and email_id not in present:
                    selected[email_id] = reference
            if not selected:
                continue
            try:
                result = client.get_metadata(
                    email_ids=tuple(selected),
                    timeout_seconds=max(0.001, deadline - time.monotonic()),
                )
                for email_id in result.not_found:
                    if email_id in selected:
                        lost.add(selected[email_id])
                for metadata in result.messages:
                    email_id = str(metadata["id"])
                    if email_id in selected and not client.metadata_matches_query(metadata, query):
                        lost.add(selected[email_id])
            except (StalwartError, OSError, ValueError):
                # Unknown eligibility retains compaction memory and is retried later.
                pass
            calls += 1
            remaining = max(0, limits.max_method_calls - calls)

    policy_current = True

    def publish_cursor() -> None:
        """Persist only derived scan progress inside the final short fence guard."""
        nonlocal policy_current
        try:
            policy_current = client.query_fingerprint(query) == scope.query_fingerprint
        except (StalwartError, ValueError):
            policy_current = False
        if not policy_current:
            return
        if position != old_position:
            _write_revalidation_position(sqlite_path, scope.key, position)

    if (
        view.superseded
        or not authority.commit_observation(fence, publish_cursor)
        or not policy_current
    ):
        return OnlineObservation(
            [],
            False,
            (),
            fence,
            authority,
            replace(
                view,
                messages=(),
                superseded=True,
                phase="degraded",
                error_code=(
                    "query_policy_changed"
                    if not policy_current
                    else view.error_code
                    if view.superseded
                    else "binding_superseded"
                ),
                method_calls=calls,
            ),
        )
    messages: list[GatewayMailboxMessageV1] = []
    if view.phase not in {"degraded", "rebasing"}:
        for metadata in view.messages:
            message = stalwart_message_to_model(metadata, include_body=False)
            messages.append(
                message.model_copy(
                    update={
                        "message_ref": mail_scope.encode(message.message_ref),
                        "thread_ref": mail_scope.encode(message.thread_ref, kind="thread")
                        if message.thread_ref is not None
                        else None,
                    }
                )
            )
    return OnlineObservation(
        messages,
        view.complete,
        tuple(sorted(lost)),
        fence,
        authority,
        replace(view, method_calls=calls),
    )


def read_online_sync_status(
    sqlite_path: Path,
    *,
    agent_id: str,
    binding_id: str,
    account_id: str,
    mode: Literal["any_inbox", "unread_only"],
) -> dict[str, Any]:
    """Read safe observation status after restart without provider access.

    Compatible exact-role views are returned newest-success first. A status read
    cannot select another binding/account and never returns cached message content.
    """
    if mode not in {"any_inbox", "unread_only"}:
        raise ValueError("online observation requires a supported notifier mode")
    if not sqlite_path.exists():
        return {"phase": "rebasing", "available": False, "views": []}
    try:
        with sqlite3.connect(sqlite_path, timeout=2.0) as connection:
            rows = connection.execute(
                "SELECT query_fingerprint,query_policy_json,snapshot_json FROM mail_sync_observations WHERE agent_id=? AND binding_id=? AND account_id=? ORDER BY json_extract(snapshot_json,'$.view.last_success_utc') DESC LIMIT 16",
                (agent_id, binding_id, account_id),
            ).fetchall()
    except sqlite3.Error:
        return {"phase": "rebasing", "available": False, "views": []}
    views = []
    for fingerprint, policy_json, snapshot_json in rows:
        try:
            policy = json.loads(policy_json)
            if (
                policy.get("box") != "inbox"
                or policy.get("read_state") != ("unread" if mode == "unread_only" else "any")
                or policy.get("answered_state") != "any"
                or policy.get("since") is not None
                or policy.get("archived") is not False
            ):
                continue
            view = json.loads(snapshot_json)["view"]
            safe = {
                key: view.get(key)
                for key in (
                    "phase",
                    "complete",
                    "has_more",
                    "incremental_supported",
                    "last_success_utc",
                    "error_code",
                    "retry_after_utc",
                )
            }
            safe.update(view_fingerprint=fingerprint, cached_count=len(view.get("messages", [])))
            views.append(safe)
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
    return {
        "phase": views[0]["phase"] if views else "rebasing",
        "available": bool(views),
        "views": views,
    }


def _read_revalidation_position(sqlite_path: Path, key: str) -> int:
    """Read a disposable per-view round-robin cursor without loading remembered IDs."""
    with sqlite3.connect(sqlite_path, timeout=2.0) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS mail_sync_revalidation (scope_key TEXT PRIMARY KEY, next_position INTEGER NOT NULL)"
        )
        row = connection.execute(
            "SELECT next_position FROM mail_sync_revalidation WHERE scope_key=?", (key,)
        ).fetchone()
    try:
        return max(0, int(row[0])) if row is not None else 0
    except (ValueError, TypeError):
        return 0


def _write_revalidation_position(sqlite_path: Path, key: str, position: int) -> None:
    """Advance only the already bounded, successfully fenced local scan cursor."""
    with sqlite3.connect(sqlite_path, timeout=2.0) as connection:
        connection.execute(
            "INSERT INTO mail_sync_revalidation VALUES(?,?) ON CONFLICT(scope_key) DO UPDATE SET next_position=excluded.next_position",
            (key, position),
        )

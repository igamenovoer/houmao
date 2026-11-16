"""Atomic periodic reminder admission and immutable queued origin fences.

These records describe core notifier wakeups. They contain no message bodies,
provider credentials, resend spool, or generic gateway plugin events.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Literal


@dataclass(frozen=True)
class ReminderOrigin:
    """The selected mailbox revision at admission, independent of body identity."""

    agent_id: str
    channel: str
    binding_id: str
    revision: str
    epoch_id: str | None = None
    account_id: str | None = None


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Add derived admission storage to the gateway-owned database."""

    connection.execute("""
        CREATE TABLE IF NOT EXISTS mail_reminder_admission (
            scope_key TEXT NOT NULL,
            cycle_key TEXT NOT NULL,
            request_id TEXT NOT NULL UNIQUE,
            agent_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            binding_id TEXT NOT NULL,
            revision TEXT NOT NULL,
            epoch_id TEXT,
            account_id TEXT,
            PRIMARY KEY(scope_key, cycle_key)
        )
    """)


def admit_mail_reminder(
    sqlite_path: Path,
    *,
    scope_key: str,
    cycle_key: str,
    origin: ReminderOrigin,
    request_id: str,
    payload_json: str,
    accepted_at_utc: str,
    managed_agent_instance_epoch: int,
    initial_state: Literal["accepted", "observing"] = "accepted",
) -> bool:
    """Commit a cycle admission and its pending prompt in the same transaction.

    A busy or previously admitted cycle creates neither row. Callers must hold
    the selected binding's short commit fence across this local transaction.
    """

    with sqlite3.connect(sqlite_path) as connection:
        _ensure_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        if (
            connection.execute(
                "SELECT 1 FROM mail_reminder_admission WHERE scope_key=? AND cycle_key=?",
                (scope_key, cycle_key),
            ).fetchone()
            is not None
        ):
            return False
        if (
            connection.execute(
                """
            SELECT 1 FROM mail_reminder_admission a JOIN gateway_requests r
            ON a.request_id=r.request_id
            WHERE a.scope_key=? AND r.state IN ('accepted','running','observing') LIMIT 1
        """,
                (scope_key,),
            ).fetchone()
            is not None
        ):
            return False
        connection.execute(
            """
            INSERT INTO gateway_requests (
                request_id,request_kind,payload_json,state,accepted_at_utc,
                managed_agent_instance_epoch
            ) VALUES (?,'mail_notifier_prompt',?,?,?,?)
        """,
            (
                request_id,
                payload_json,
                initial_state,
                accepted_at_utc,
                managed_agent_instance_epoch,
            ),
        )
        connection.execute(
            """
            INSERT INTO mail_reminder_admission VALUES (?,?,?,?,?,?,?,?,?)
        """,
            (
                scope_key,
                cycle_key,
                request_id,
                origin.agent_id,
                origin.channel,
                origin.binding_id,
                origin.revision,
                origin.epoch_id,
                origin.account_id,
            ),
        )
        connection.execute(
            """
            UPDATE gateway_mail_notifier SET last_poll_at_utc=?,last_notification_at_utc=?,
                last_notified_digest=NULL,last_error=NULL WHERE scope_key=?
        """,
            (accepted_at_utc, accepted_at_utc, scope_key),
        )
        connection.commit()
    return True


def reminder_origin(sqlite_path: Path, request_id: str) -> ReminderOrigin | None:
    """Read a queued reminder's immutable origin without interpreting credentials."""

    with sqlite3.connect(sqlite_path) as connection:
        if (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mail_reminder_admission'"
            ).fetchone()
            is None
        ):
            return None
        row = connection.execute(
            """
            SELECT agent_id,channel,binding_id,revision,epoch_id,account_id
            FROM mail_reminder_admission WHERE request_id=?
        """,
            (request_id,),
        ).fetchone()
    if row is None:
        return None
    return ReminderOrigin(
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]),
        str(row[4]) if row[4] is not None else None,
        str(row[5]) if row[5] is not None else None,
    )


def cancel_pending_mail_reminders(
    sqlite_path: Path,
    *,
    agent_id: str,
    channel: str,
    binding_id: str,
    revision: str | None = None,
) -> int:
    """Cancel unstarted old wakeups while preserving already dispatched outcomes."""

    if not sqlite_path.exists():
        return 0
    with sqlite3.connect(sqlite_path) as connection:
        _ensure_schema(connection)
        conditions = "a.agent_id=? AND a.channel=? AND a.binding_id=?"
        parameters = [agent_id, channel, binding_id]
        if revision is not None:
            conditions += " AND a.revision=?"
            parameters.append(revision)
        cursor = connection.execute(
            """
            UPDATE gateway_requests SET state='failed',
                error_detail='Origin mailbox revision retired before dispatch'
            WHERE state='accepted' AND request_id IN (
                SELECT a.request_id FROM mail_reminder_admission a WHERE
        """
            + conditions
            + ")",
            parameters,
        )
        connection.commit()
        return cursor.rowcount

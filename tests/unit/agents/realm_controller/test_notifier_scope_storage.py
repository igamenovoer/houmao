"""Concurrent notifier configuration is independent of status reads."""

from pathlib import Path
import sqlite3
import threading
from typing import Any

import pytest

from houmao.agents.realm_controller.gateway_storage import (
    read_gateway_mail_notifier_record,
    write_gateway_mail_notifier_record,
)


def test_empty_status_read_cannot_overwrite_concurrent_enable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "gateway.sqlite"
    scope = '["agent","online","binding"]'
    read_gateway_mail_notifier_record(path, scope_key="another-scope")
    read_selected = threading.Event()
    enable_completed = threading.Event()
    original_connect = sqlite3.connect
    errors: list[BaseException] = []

    class PausedCursor:
        """Pause a missing-row read after taking its snapshot."""

        def __init__(self, cursor: sqlite3.Cursor) -> None:
            self.m_cursor = cursor

        def fetchone(self) -> Any:
            row = self.m_cursor.fetchone()
            if row is None:
                read_selected.set()
                assert enable_completed.wait(5)
            return row

    class PausedConnection(sqlite3.Connection):
        """Intercept only the controlled status reader's selection."""

        def execute(self, sql: str, parameters: Any = ()) -> Any:
            cursor = super().execute(sql, parameters)
            if (
                threading.current_thread().name == "status-reader"
                and "FROM gateway_mail_notifier" in sql
            ):
                return PausedCursor(cursor)
            return cursor

    def connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        """Use real SQLite transactions with a deterministic reader pause."""

        return original_connect(*args, factory=PausedConnection, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect)

    def read() -> None:
        """Capture thread errors for an actionable assertion."""

        try:
            read_gateway_mail_notifier_record(path, scope_key=scope)
        except BaseException as exc:
            errors.append(exc)

    reader = threading.Thread(target=read, name="status-reader")
    reader.start()
    try:
        assert read_selected.wait(5)
        write_gateway_mail_notifier_record(path, scope_key=scope, enabled=True, interval_seconds=60)
    finally:
        enable_completed.set()
        reader.join(5)
    assert not reader.is_alive()
    assert errors == []
    assert read_gateway_mail_notifier_record(path, scope_key=scope).enabled is True

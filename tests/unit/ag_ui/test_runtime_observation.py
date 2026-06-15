from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime


def _runtime_stub(**attrs: object) -> GatewayServiceRuntime:
    """Build a GatewayServiceRuntime instance with only tested attributes."""

    runtime = object.__new__(GatewayServiceRuntime)
    for name, value in attrs.items():
        setattr(runtime, name, value)
    return cast(GatewayServiceRuntime, runtime)


def _create_queue(path: Path) -> None:
    """Create the minimal gateway request table used by observation helpers."""

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE gateway_requests (
                request_id TEXT PRIMARY KEY,
                request_kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                state TEXT NOT NULL,
                accepted_at_utc TEXT NOT NULL,
                started_at_utc TEXT,
                finished_at_utc TEXT,
                managed_agent_instance_epoch INTEGER NOT NULL,
                error_detail TEXT,
                result_json TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO gateway_requests (
                request_id,
                request_kind,
                payload_json,
                state,
                accepted_at_utc,
                started_at_utc,
                finished_at_utc,
                managed_agent_instance_epoch,
                error_detail,
                result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "request-1",
                "submit_prompt",
                "{}",
                "completed",
                "2026-06-08T01:00:00Z",
                "2026-06-08T01:00:01Z",
                "2026-06-08T01:00:02Z",
                1,
                None,
                '{"ok": true}',
            ),
        )
        connection.commit()


def test_gateway_runtime_observes_admitted_request_state(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.sqlite"
    _create_queue(queue_path)
    runtime = _runtime_stub(m_paths=SimpleNamespace(queue_path=queue_path))

    observed = runtime.ag_ui_request_state("request-1")

    assert observed is not None
    assert observed.request_id == "request-1"
    assert observed.request_kind == "submit_prompt"
    assert observed.state == "completed"
    assert observed.terminal is True
    assert observed.failed is False
    assert observed.result == {"ok": True}
    assert runtime.ag_ui_request_state("missing") is None


def test_gateway_runtime_resolves_headless_artifact_from_ag_ui_run_id(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    runtime = _runtime_stub(
        m_lock=threading.Lock(),
        m_attach_contract=SimpleNamespace(
            backend="codex_headless",
            manifest_path=str(manifest_path),
            attach_identity="agent-1",
        ),
    )

    missing = runtime.ag_ui_headless_artifact("run-alpha")

    assert missing is not None
    assert missing.provider == "codex"
    assert missing.artifact_available is False
    assert missing.turn_dir == tmp_path / "manifest.turn-artifacts" / "run-alpha"
    assert missing.canonical_events_path == missing.turn_dir / "canonical-events.jsonl"

    missing.canonical_events_path.parent.mkdir(parents=True)
    missing.canonical_events_path.write_text("", encoding="utf-8")
    available = runtime.ag_ui_headless_artifact("run-alpha")

    assert available is not None
    assert available.artifact_available is True


def test_gateway_runtime_reports_unavailable_artifact_and_tui_cases(tmp_path: Path) -> None:
    runtime = _runtime_stub(
        m_lock=threading.Lock(),
        m_tui_tracking=None,
        m_attach_contract=SimpleNamespace(
            backend="local_interactive",
            manifest_path=str(tmp_path / "manifest.json"),
            attach_identity="agent-1",
        ),
    )

    assert runtime.ag_ui_headless_artifact("run-alpha") is None

    tui_observation = runtime.ag_ui_tui_observation()
    assert tui_observation.available is False
    assert tui_observation.final_text is None
    assert tui_observation.status["backend"] == "local_interactive"
    assert tui_observation.status["targetTransportFamily"] == "tui"

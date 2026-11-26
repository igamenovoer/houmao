"""Check the finite Hermes client artifact and settlement boundaries."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import stat
import sys

import pytest

from houmao.agents.realm_controller import owner_admission
from houmao.agents.realm_controller.backends.headless_bridge import main
from houmao.agents.realm_controller.backends.headless_output import (
    load_preferred_canonical_headless_events,
)
from houmao.agents.realm_controller.backends.hermes_headless_protocol import (
    HERMES_HEADLESS_INPUT,
    HERMES_HEADLESS_REQUEST,
    inspect_hermes_headless_result,
    reconcile_hermes_headless_turn,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    load_session_manifest,
    parse_session_manifest_payload,
    write_session_manifest,
)
from tests.unit.agents.realm_controller.test_schema_and_manifest import (
    _identity_fields,
    _sample_plan,
)


def _run_worker(
    tmp_path: Path, *, session_id: str, exit_code: int, turn_name: str = "turn-a"
) -> Path:
    """Run a real finite child through the bridge with literal private stdin."""

    turn_dir = tmp_path / turn_name
    turn_dir.mkdir(mode=0o700)
    (turn_dir / HERMES_HEADLESS_INPUT).write_text("line one\nline two\n", encoding="utf-8")
    (turn_dir / HERMES_HEADLESS_REQUEST).write_text(
        json.dumps(
            {
                "session_id": "local-exact",
                "turn_id": turn_name,
                "turn_index": 1,
                "generation_id": "managed-generation",
            }
        ),
        encoding="utf-8",
    )
    env_path = tmp_path / f"{turn_name}.json"
    env_path.write_text("{}", encoding="utf-8")
    code = f"""
import json
import sys

assert sys.stdin.read() == 'line one\\nline two\\n'
print(json.dumps({{"type": "system", "subtype": "init", "session_id": ""}}))
print(json.dumps({{"type": "text", "text": "partial"}}))
print(json.dumps({{
    "type": "result", "exit_code": {exit_code}, "session_id": {session_id!r},
    "text": "full and complete", "replay_gap": True,
}}))
print("native stderr", file=sys.stderr)
raise SystemExit({exit_code})
"""
    assert (
        main(
            [
                "--provider",
                "hermes",
                "--output-format",
                "stream-json",
                "--turn-index",
                "1",
                "--turn-dir",
                str(turn_dir),
                "--cwd",
                str(tmp_path),
                "--launched-at-utc",
                "2026-01-01T00:00:00Z",
                "--env-file",
                str(env_path),
                "--replace-environment",
                "--",
                sys.executable,
                "-c",
                code,
            ]
        )
        == exit_code
    )
    return turn_dir


def test_headless_uses_literal_input_and_final_text_after_replay_gap(tmp_path: Path) -> None:
    """Preserve raw streams and publish only the exact session's complete native result."""

    first = _run_worker(tmp_path, session_id="local-exact", exit_code=0)
    second = _run_worker(tmp_path, session_id="local-exact", exit_code=0, turn_name="turn-b")
    for turn_dir in (first, second):
        outcome = reconcile_hermes_headless_turn(turn_dir, generation_id="managed-generation")
        assert (outcome.status, outcome.completion_source, outcome.session_id) == (
            "completed",
            "native_jsonl",
            "local-exact",
        )
        assert reconcile_hermes_headless_turn(turn_dir, generation_id="stale").status == "uncertain"
        assert not (turn_dir / HERMES_HEADLESS_INPUT).exists()
        assert stat.S_IMODE((turn_dir / "stdout.jsonl").stat().st_mode) == 0o600
        assert stat.S_IMODE((turn_dir / "stderr.log").stat().st_mode) == 0o600
        assert "native stderr" in (turn_dir / "stderr.log").read_text()
        assert "partial" in (turn_dir / "stdout.jsonl").read_text()
        events = load_preferred_canonical_headless_events(
            turn_dir=turn_dir, provider="hermes", output_format="stream-json", turn_index=1
        )
        assert [item.kind for item in events] == ["session", "assistant"]
        assert events[-1].data == {"text": "full and complete", "replay_gap": True}
    first_pid = json.loads((first / "process.json").read_text())["child_pid"]
    second_pid = json.loads((second / "process.json").read_text())["child_pid"]
    assert first_pid != second_pid


@pytest.mark.parametrize(
    ("session_id", "exit_code"), [("other-session", 0), ("local-exact", 130), ("local-exact", 1)]
)
def test_headless_client_exit_without_matching_settlement_stays_uncertain(
    tmp_path: Path, session_id: str, exit_code: int
) -> None:
    """Neither successful exit for another session nor Ctrl-C proves settlement."""

    turn_dir = _run_worker(tmp_path, session_id=session_id, exit_code=exit_code)
    assert reconcile_hermes_headless_turn(turn_dir).status == "uncertain"
    assert (turn_dir / "exitcode").read_text().strip() == str(exit_code)
    assert (turn_dir / "canonical-events.jsonl").read_text() == ""
    assert not (turn_dir / "usage-terminal.json").exists()


@pytest.mark.parametrize(
    "replacement",
    [
        "{ truncated frame",
        '{"type":"result","session_id":"local-exact","text":"unexpected","exit_code":1}',
        '{"type":"text","session_id":"earlier-turn","text":"foreign"}',
    ],
)
def test_hermes_malformed_or_cross_session_frames_leave_turn_unresolved(
    tmp_path: Path, replacement: str
) -> None:
    """Treat contradictory or incomplete protocol frames as insufficient evidence."""

    turn = tmp_path / "turn"
    turn.mkdir()
    (turn / HERMES_HEADLESS_REQUEST).write_text(
        json.dumps({"turn_id": turn.name, "turn_index": 1, "session_id": "local-exact"})
    )
    (turn / "stdout.jsonl").write_text(
        '{"type":"system","subtype":"init"}\n'
        + replacement
        + '\n{"type":"result","session_id":"local-exact","exit_code":0,"text":"native result"}\n'
    )

    result = inspect_hermes_headless_result(turn_dir=turn, returncode=0)

    assert result.status == "uncertain"
    assert result.events == []


def test_hermes_unattributed_counters_are_not_usage_evidence(tmp_path: Path) -> None:
    """Even nonzero JSONL counters can represent cumulative or unrelated activity."""

    turn = tmp_path / "turn"
    turn.mkdir()
    (turn / HERMES_HEADLESS_REQUEST).write_text(
        json.dumps({"turn_id": turn.name, "turn_index": 1, "session_id": "local-exact"})
    )
    (turn / "stdout.jsonl").write_text(
        '{"type":"system","subtype":"init"}\n'
        '{"type":"tool_use","name":"read_file","tool_call_id":"call-one"}\n'
        '{"type":"result","session_id":"local-exact","exit_code":0,"text":"done",'
        '"tokens":{"input":3500,"output":700,"total":4200}}\n'
    )

    result = inspect_hermes_headless_result(turn_dir=turn, returncode=0)

    assert result.status == "completed"
    assert [event.kind for event in result.events] == ["session", "tool_call", "assistant"]
    assert result.events[1].data == {"tool_name": "read_file", "tool_call_id": "call-one"}
    assert all("tokens" not in (event.data or {}) for event in result.events)


@pytest.mark.parametrize("matching_result", [True, False])
def test_hermes_worker_recovery_preserves_owner_and_native_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, matching_result: bool
) -> None:
    """Recover the exact saved continuation when the submitter died after client exit."""

    path = tmp_path / "manifest.json"
    generation = "managed-generation"
    plan = replace(
        _sample_plan(tmp_path), backend="hermes_headless", tool="hermes", executable="hermes"
    )
    stale = write_session_manifest(
        path,
        build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=plan,
                role_name="fixture-role",
                brain_manifest_path=tmp_path / "brain.yaml",
                registry_generation_id=generation,
                backend_state={},
                **_identity_fields("HOUMAO-hermes"),
            )
        ),
    ).payload
    assert stale["headless"]["session_id"] is None
    assert stale["headless"]["turn_index"] == 0
    gateway = tmp_path / "gateway"
    gateway.mkdir()
    database = gateway / "queue.sqlite"
    with sqlite3.connect(database):
        pass
    monkeypatch.setattr(
        owner_admission,
        "_owner_manifest",
        lambda path, _: parse_session_manifest_payload(
            load_session_manifest(path).payload, source="fixture"
        ),
    )
    claim = owner_admission.reserve_owner_prompt(path, generation, origin="gateway")
    claim.handoff()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE managed_prompt_attempts SET caller_birth_token='previous-process'"
        )
    claim.turn_dir.parent.mkdir()
    _run_worker(
        claim.turn_dir.parent,
        session_id="local-exact" if matching_result else "foreign",
        exit_code=0,
        turn_name=claim.request_id,
    )

    if not matching_result:
        with pytest.raises(owner_admission.OwnerAdmissionError) as refused:
            owner_admission.reserve_owner_prompt(path, generation, origin="runtime")
        assert refused.value.code == "uncertain"
        active = owner_admission.observe_owner_prompt(path, generation)
        assert active is not None and active.request_id == claim.request_id
        assert load_session_manifest(path).payload["headless"] == stale["headless"]
        return

    next_claim = owner_admission.reserve_owner_prompt(path, generation, origin="runtime")
    assert next_claim.request_id != claim.request_id
    saved = write_session_manifest(path, stale).payload
    assert saved["headless"]["session_id"] == saved["backend_state"]["session_id"] == "local-exact"
    assert saved["headless"]["turn_index"] == saved["backend_state"]["turn_index"] == 1

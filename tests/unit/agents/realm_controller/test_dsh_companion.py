"""Exercise the packaged JavaScript companion's lifecycle and privacy boundaries."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


def _run_companion(
    tmp_path: Path,
    *,
    pending: list[str],
    abandoned: list[str],
    role: str = "Literal {{example}} $HOME `code`\nsecond line",
) -> dict:
    """Invoke the real asset with a deterministic native-service boundary."""

    bun = shutil.which("bun")
    if bun is None:
        pytest.skip("Bun is required for packaged ECMAScript asset checks")
    asset = (
        Path(__file__).resolve().parents[4] / "src/houmao/agents/assets/dsh/managed-companion.mjs"
    )
    (tmp_path / "role.txt").write_text(role)
    evidence = tmp_path / "evidence.jsonl"
    control = {
        "version": 1,
        "attempt_id": "attempt-1",
        "runtime_session_id": "runtime-1",
        "generation": "generation-1",
        "expected_native_session_id": "native-1",
        "evidence_path": str(evidence),
        "abandoned_message_ids": abandoned,
    }
    (tmp_path / "control.json").write_text(json.dumps(control))
    script = tmp_path / "run.mjs"
    script.write_text(
        r"""
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
const [asset, directory, pendingJSON] = process.argv.slice(2);
const plugin = await import(pathToFileURL(asset).href);
const callbacks = new Map();
const sections = [];
const removed = [];
const ctx = {
  on(name, fn) { callbacks.set(name, fn); },
  systemPrompt: { section(section) { sections.push(section); } },
};
plugin.apply(ctx, {controlFile: `${directory}/control.json`, roleFile: `${directory}/role.txt`});
const pending = JSON.parse(pendingJSON).map(id => ({id}));
const session = {id: 'native-1', header: {}};
const agent = {session, inbox: {
  nextTurn: pending, nextStep: [],
  remove(id) { removed.push(id); return true; },
}};
let failure;
try {
  await callbacks.get('agent/created')({agent, source: 'resume'});
  callbacks.get('agent/inbox/inserted')({agent, message: {id: 'new-input', source: {kind: 'user'}}});
  callbacks.get('agent/inbox/claimed')({agent, message: {id: 'new-input'}, turn: 3});
  const child = {session: {id: 'child-1', header: {origin: 'subagent'}}};
  await callbacks.get('agent/created')({agent: child, source: 'startup'});
  callbacks.get('agent/inbox/inserted')({agent: child, message: {id: 'child-input'}});
} catch (error) { failure = error.message; }
callbacks.get('dispose')();
const rows = readFileSync(`${directory}/evidence.jsonl`, 'utf8').trim().split('\n').map(JSON.parse);
console.log(JSON.stringify({sections, removed, failure, rows}));
"""
    )
    result = subprocess.run(
        [bun, str(script), str(asset), str(tmp_path), json.dumps(pending)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_literal_role_and_bound_admission_evidence(tmp_path: Path) -> None:
    """Keep native guidance additive and exclude child input from root handoff."""

    result = _run_companion(tmp_path, pending=[], abandoned=[])
    section = result["sections"][0]
    assert section["text"] == "Literal {{example}} $HOME `code`\nsecond line"
    assert section["interpolate"] is False
    assert "complete" not in section
    events = [row["event"] for row in result["rows"]]
    assert events == ["loaded", "created", "admitted", "claimed"]
    assert result["rows"][-1]["turn"] == 3
    assert all(row["attempt_id"] == "attempt-1" for row in result["rows"])
    assert all("text" not in row and "content" not in row for row in result["rows"])
    assert "{{example}}" not in json.dumps(result["rows"])
    assert (tmp_path / "evidence.jsonl").stat().st_mode & 0o777 == 0o600


def test_abandoned_input_is_removed_before_activation(tmp_path: Path) -> None:
    """Use identified native inbox removal rather than rewriting persisted history."""

    result = _run_companion(tmp_path, pending=["abandoned-1"], abandoned=["abandoned-1"])
    assert result["removed"] == ["abandoned-1"]
    assert [row["event"] for row in result["rows"]][:3] == ["loaded", "reconciled", "created"]


def test_unknown_pending_input_refuses_activation(tmp_path: Path) -> None:
    """Preserve unidentified work and refuse a resume that might replay it."""

    result = _run_companion(tmp_path, pending=["unknown-1"], abandoned=[])
    assert "unidentified pending input" in result["failure"]
    assert result["removed"] == []
    assert [row["event"] for row in result["rows"]] == ["loaded", "unreconciled"]


def test_empty_role_registers_no_stale_section(tmp_path: Path) -> None:
    """Keep an empty managed role absent without replacing built-in instructions."""

    result = _run_companion(tmp_path, pending=[], abandoned=[], role="")
    assert result["sections"] == []
    assert result["rows"][0]["role_bytes"] == 0


def test_mixed_unknown_work_refuses_before_any_removal(tmp_path: Path) -> None:
    """Do not partially mutate the inbox when safe reconciliation is unproven."""

    result = _run_companion(
        tmp_path, pending=["abandoned-1", "unknown-2"], abandoned=["abandoned-1"]
    )
    assert "unidentified pending input" in result["failure"]
    assert result["removed"] == []

"""Verify the managed one-shot fence after native startup, before followup."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
from time import monotonic, sleep
from typing import Any

import pytest


@pytest.mark.parametrize("withdraw", ["revoked", "caller_exited"])
def test_native_headless_dispatch_cannot_outlive_the_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    isolated_tmux: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    withdraw: str,
) -> None:
    """Pause actual native initialization and withdraw permission before its first input."""

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config_tools = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    config = config_tools.resolve_config(
        case="self-hosted",
        client="dsh",
        mode="headless",
        surface="manager",
        process_env={
            "HOUMAO_TEST_SELF_HOSTED_MODEL": "controlled-fence",
            "HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL": endpoint,
            "HOUMAO_TEST_SELF_HOSTED_CONTEXT_WINDOW": "8192",
            "HOUMAO_TEST_SELF_HOSTED_MAX_OUTPUT_TOKENS": "256",
            "HOUMAO_TEST_SELF_HOSTED_DSH_REASONING": "false",
        },
    )
    prepared = prepare.prepare_run(
        config, run_root=tmp_path / "runs", executable=str(dsh_executable)
    )
    root = Path(prepared["run_dir"])
    marker = tmp_path / "native-started"
    release = tmp_path / "native-release"
    plugin = tmp_path / "native-test-gate.mjs"
    plugin.write_text(
        """import { existsSync, writeFileSync } from 'node:fs';
export const name = 'houmao-test-headless-gate';
export const inject = ['agents'];
export function apply(ctx, config) {
  ctx.on('agent/created', async () => {
    writeFileSync(config.marker, 'started', {mode: 0o600});
    for (let i = 0; i < 2000; i++) {
      if (existsSync(config.release)) return;
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    throw new Error('fixture did not release native startup');
  });
}
""",
        encoding="utf-8",
    )
    command = None
    try:
        launch.launch_run(root, timeout=50)
        run = prepare.load_run(root)
        assert run["tmux_socket_path"] != str(isolated_tmux)
        identity = run["identity"]
        manifest_path = Path(identity["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        patch = home / "houmao-profile.patch.json"
        original = patch.read_text(encoding="utf-8")
        rows = json.loads(original)
        rows.append(
            {
                "insert": [
                    {
                        "id": "houmao-test-headless-gate",
                        "name": str(plugin),
                        "config": {"marker": str(marker), "release": str(release)},
                    }
                ]
            }
        )
        patch.write_text(json.dumps(rows), encoding="utf-8")

        command = subprocess.Popen(
            [
                "houmao-mgr",
                "--print-json",
                "agents",
                "single",
                "--agent-id",
                identity["agent_id"],
                "prompt",
                "--prompt",
                "This fenced text must never reach the provider.",
            ],
            cwd=run["workdir"],
            env=launch.run_environment(run),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _wait_for_file(marker)
        turn_root = manifest_path.with_suffix(".turn-artifacts")
        (guard,) = turn_root.glob("*/.dispatch-permission.json")
        turn = guard.parent
        assert not (turn / "dsh-native-handoff.json").exists()
        assert requests == []
        if withdraw == "revoked":
            payload = json.loads(guard.read_text(encoding="utf-8"))
            payload["active"] = False
            replacement = guard.with_suffix(".revoked")
            replacement.write_text(json.dumps(payload), encoding="utf-8")
            replacement.chmod(0o600)
            replacement.replace(guard)
        else:
            command.terminate()
            command.communicate(timeout=10)
        release.touch()
        _wait_for_file(turn / "exitcode")
        assert (turn / "exitcode").read_text(encoding="utf-8").strip() != "0"
        assert not (turn / "dsh-native-handoff.json").exists()
        assert not (turn / "dsh-native-closure.json").exists()
        assert requests == []
        evidence = [
            json.loads(line)
            for line in (turn / "dsh-native-evidence.jsonl").read_text().splitlines()
        ]
        assert all(row["event"] not in {"admitted", "claimed"} for row in evidence)
        if withdraw == "revoked":
            _stdout, stderr = command.communicate(timeout=10)
            assert command.returncode != 0
            assert "native input permission is unavailable" in stderr

        patch.write_text(original, encoding="utf-8")
        literal = 'Reply only fencing-over.\nKeep literal $HOME; "quote" and `date`.'
        launch.prompt_run(root, prompt=literal, timeout=50)
        assert len(requests) == 1
        assert json.dumps(literal)[1:-1] in json.dumps(requests[0]["messages"])

        if withdraw == "revoked":
            native_binding = json.loads((home / "houmao-native-session.json").read_text())
            session_id = native_binding["native_session_id"]
            (journal,) = (home / "sessions").glob(f"*/{session_id}/session.v4.jsonl")
            native_sessions_before = sorted(path.name for path in journal.parents[1].iterdir())
            unavailable = journal.with_name("held-by-fixture.jsonl")
            journal.rename(unavailable)
            try:
                missing = subprocess.run(
                    [
                        "houmao-mgr",
                        "--print-json",
                        "agents",
                        "single",
                        "--agent-id",
                        identity["agent_id"],
                        "prompt",
                        "--prompt",
                        "This exact session is missing.",
                    ],
                    cwd=run["workdir"],
                    env=launch.run_environment(run),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                assert missing.returncode != 0
                assert "does not exist" in missing.stderr
                assert len(requests) == 1
                assert (
                    json.loads((home / "houmao-native-session.json").read_text()) == native_binding
                )
                assert (
                    sorted(path.name for path in journal.parents[1].iterdir())
                    == native_sessions_before
                )
            finally:
                unavailable.rename(journal)
    finally:
        release.touch()
        if command is not None and command.poll() is None:
            command.terminate()
            command.communicate(timeout=10)
        launch.stop_run(root)


def _wait_for_file(path: Path) -> None:
    """Wait for one private fixture marker with a bounded deadline."""

    deadline = monotonic() + 20
    while not path.is_file():
        if monotonic() >= deadline:
            raise AssertionError(f"Timed out waiting for fixture file {path.name}")
        sleep(0.02)

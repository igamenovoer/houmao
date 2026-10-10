#!/usr/bin/env python3
"""Run one iteration-1 session: prepare, launch, record, drive, freeze.

Usage:
    pixi run python scripts/explore/kimi-code-tui-parsing/run_session.py \
        --spec context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/iterations/2026-10-10-plan-1-state-matrix-capture/session-1-lifecycle.yaml \
        --run-root tmp/houmao-dev-tui-testing/2026-10-10-kimi-session1-lifecycle

The runner prepares a fresh Boltons copy, launches kimi per the
``houmao-dev-launch-agents`` contract, starts the 5 fps terminal recorder
before the first operation, drives the spec's tracker-blind operations, then
stops and freezes all evidence with SHA-256 digests.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from campaign_lib.drive import DriveError, TmuxDriver
from campaign_lib.fixture import prepare_boltons_copy
from campaign_lib.freeze import freeze_run
from campaign_lib.launch import DEFAULT_KIMI_HOME, kill_session, launch_kimi
from campaign_lib.runtime_observer import RuntimeObserver
from campaign_lib.spec import load_session_spec

REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    """Run one campaign session end to end."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="Session YAML (promptfoo format)")
    parser.add_argument("--run-root", type=Path, required=True, help="Fresh run root")
    parser.add_argument("--session-name", default=None, help="tmux session name (default derived)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Expand the spec and write definitions without launching or recording",
    )
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    if run_root.exists() and any(run_root.iterdir()):
        print(f"ERROR: run root not empty: {run_root}", file=sys.stderr)
        return 2
    run_root.mkdir(parents=True, exist_ok=True)

    spec = load_session_spec(args.spec)
    config = spec.provider_config
    session_name = args.session_name or (
        f"HMDEV-kimi-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}"
    )

    _write_definitions(run_root=run_root, spec=spec)
    if args.dry_run:
        print(json.dumps({"run_root": str(run_root), "cases": len(spec.cases), "dry_run": True}))
        return 0

    workdir_policy = str(config.get("workdir_policy") or "fresh-untrusted")
    profile = str(config.get("profile") or "kimi-tui-unattended")
    unattended = profile == "kimi-tui-unattended"
    interval = float(config.get("sample_interval_seconds") or 0.2)

    fixture_manifest = prepare_boltons_copy(workdir=run_root / "workdir" / "boltons")
    (run_root / "capture").mkdir(parents=True, exist_ok=True)
    (run_root / "capture" / "fixture_manifest.json").write_text(
        json.dumps(fixture_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    trust_projection = None
    if workdir_policy == "trusted":
        from houmao.agents.kimi_workspace_trust import ensure_kimi_workspace_trust

        trust_projection = ensure_kimi_workspace_trust(
            home_path=DEFAULT_KIMI_HOME,
            working_directory=run_root / "workdir" / "boltons",
        )

    launch_meta = launch_kimi(
        run_root=run_root,
        workdir=run_root / "workdir" / "boltons",
        session_name=session_name,
        unattended=unattended,
    )

    recording_root = run_root / "capture" / "recording"
    start = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.terminal_record",
            "start",
            "--mode",
            "active",
            "--target-session",
            session_name,
            "--target-pane",
            launch_meta["tmux_pane"],
            "--tool",
            "kimi",
            "--run-root",
            str(recording_root),
            "--sample-interval-seconds",
            str(interval),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if start.returncode != 0:
        print(f"ERROR: recorder start failed: {start.stderr[-800:]}", file=sys.stderr)
        kill_session(session_name=session_name)
        return 2

    manifest_path = recording_root / "manifest.json"
    record_started_at = json.loads(manifest_path.read_text(encoding="utf-8"))["started_at_utc"]

    observer = RuntimeObserver(
        session_name=session_name,
        pane_id=launch_meta["tmux_pane"],
        output_path=run_root / "capture" / "runtime_observations.ndjson",
        record_started_at_utc=record_started_at,
    )
    driver = TmuxDriver(
        session_name=session_name,
        pane_id=launch_meta["tmux_pane"],
        drive_log_path=run_root / "capture" / "drive_events.ndjson",
        record_started_at_utc=record_started_at,
    )

    failures: list[dict[str, str]] = []
    observer.start()
    try:
        for case in spec.cases:
            for op in case.ops:
                try:
                    driver.run_op(case_id=case.case_id, op=op)
                except DriveError as exc:
                    failures.append({"case_id": case.case_id, "error": str(exc)})
                    try:
                        driver.send_key("Escape")
                    except DriveError:
                        pass
    finally:
        observer.stop()
        stop = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.terminal_record",
                "stop",
                "--run-root",
                str(recording_root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if stop.returncode != 0:
            print(f"WARNING: recorder stop failed: {stop.stderr[-400:]}", file=sys.stderr)
        _teardown_recorder_session(recording_root, session_name=session_name)
        _wait_quiescence(recording_root)

    frozen = freeze_run(run_root=run_root)

    summary = {
        "run_root": str(run_root),
        "session_name": session_name,
        "spec": str(spec.path),
        "cases": len(spec.cases),
        "ops": sum(len(case.ops) for case in spec.cases),
        "failures": failures,
        "trust_preseed": None if trust_projection is None else trust_projection.to_payload(),
        "frozen_evidence": str(run_root / "capture" / "frozen-evidence.json"),
        "frozen_files": len(frozen["files"]),
        "note": "Live tmux session left running for inspection; kill with "
        f"`tmux kill-session -t {session_name}` after review.",
    }
    (run_root / "run-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if failures else 0


def _write_definitions(*, run_root: Path, spec) -> None:
    """Write definitions/task.md and definitions/scenario.json for the run."""

    definitions = run_root / "definitions"
    definitions.mkdir(parents=True, exist_ok=True)
    (definitions / "task.md").write_text(
        "\n".join(
            [
                f"# {spec.description}",
                "",
                f"Spec: `{spec.path}`",
                "",
                "Cases:",
                *[f"- `{case.case_id}`: {case.description}" for case in spec.cases],
                "",
            ]
        ),
        encoding="utf-8",
    )
    scenario = {
        "spec_path": str(spec.path),
        "provider_config": spec.provider_config,
        "cases": [
            {"case_id": case.case_id, "description": case.description, "ops": list(case.ops)}
            for case in spec.cases
        ],
    }
    (definitions / "scenario.json").write_text(
        json.dumps(scenario, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _teardown_recorder_session(recording_root: Path, *, session_name: str) -> None:
    """Ensure the recorder session and its asciinema attach are fully gone.

    The maintained controller can leave the asciinema attach client alive
    after ``stop`` finalizes, which keeps ``session.cast`` growing past the
    freeze. Poll for the recorder session, kill it if needed, then detach any
    remaining clients of the target session so the cast reaches finality
    before digests are taken.
    """

    from houmao.agents.realm_controller.backends.tmux_runtime import run_tmux

    try:
        manifest = json.loads((recording_root / "manifest.json").read_text(encoding="utf-8"))
        recorder_session = manifest.get("recorder_session_name")
    except (OSError, json.JSONDecodeError):
        recorder_session = None
    if recorder_session:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if run_tmux(["has-session", "-t", recorder_session]).returncode != 0:
                break
            time.sleep(0.3)
        if run_tmux(["has-session", "-t", recorder_session]).returncode == 0:
            run_tmux(["kill-session", "-t", recorder_session])
    run_tmux(["detach-client", "-s", session_name])


def _wait_quiescence(recording_root: Path, timeout_seconds: float = 30.0) -> None:
    """Wait until finalized recorder files stop changing."""

    names = ("manifest.json", "pane_snapshots.ndjson", "input_events.ndjson", "session.cast")
    deadline = time.monotonic() + timeout_seconds
    prior: tuple[tuple[int, int], ...] | None = None
    stable_polls = 0
    while time.monotonic() < deadline:
        current = tuple(
            (path.stat().st_size, path.stat().st_mtime_ns)
            for path in (recording_root / name for name in names)
            if path.is_file()
        )
        if current and current == prior:
            stable_polls += 1
            if stable_polls >= 5:
                return
        else:
            stable_polls = 0
        prior = current
        time.sleep(0.3)


if __name__ == "__main__":
    raise SystemExit(main())

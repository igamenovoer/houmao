#!/usr/bin/env python3
"""Run mailbox roundtrip demo automation scenarios from the pack directory.

This script drives the pack-owned `run_demo.sh` command surface through
named scenarios and writes machine-readable results under one caller-selected
automation root.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


ScenarioFunc = Callable[[Path, Path, Path, list[dict[str, Any]]], dict[str, Any]]


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _assert(condition: bool, message: str) -> None:
    """Raise one assertion error when the condition is false."""

    if not condition:
        raise AssertionError(message)


def _run_wrapper(
    *,
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
    command: str,
    demo_output_dir: Path,
    jobs_dir: Path | None = None,
    snapshot: bool = False,
    env_updates: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run one `run_demo.sh` command and persist stdout/stderr logs."""

    command_index = len(commands) + 1
    commands_dir = scenario_dir / "commands"
    stdout_path = commands_dir / f"{command_index:02d}-{command}.stdout.txt"
    stderr_path = commands_dir / f"{command_index:02d}-{command}.stderr.txt"

    argv = [str(pack_dir / "run_demo.sh"), command, "--demo-output-dir", str(demo_output_dir)]
    if jobs_dir is not None:
        argv.extend(["--jobs-dir", str(jobs_dir)])
    if snapshot:
        argv.append("--snapshot-report")

    env = dict(os.environ)
    if env_updates is not None:
        env.update(env_updates)

    result = subprocess.run(
        argv,
        cwd=str(repo_root.resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")

    payload = {
        "argv": argv,
        "exit_code": result.returncode,
        "stdout_path": str(stdout_path.resolve()),
        "stderr_path": str(stderr_path.resolve()),
    }
    commands.append(payload)
    return payload


def _load_stop_result(demo_dir: Path) -> dict[str, Any]:
    """Load the persisted stop-result payload for one demo root."""

    return _read_json(demo_dir / "stop_result.json")


def _scenario_auto_implicit_jobs_dir(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the default jobs-dir behavior for `auto`."""

    demo_dir = scenario_dir / "demo"
    command = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
    )
    _assert(command["exit_code"] == 0, "auto scenario should succeed")

    sender_start = _read_json(demo_dir / "sender_start.json")
    receiver_start = _read_json(demo_dir / "receiver_start.json")
    expected_sender_job = demo_dir / "project" / ".houmao" / "jobs" / "AGENTSYS-mailbox-sender"
    expected_receiver_job = demo_dir / "project" / ".houmao" / "jobs" / "AGENTSYS-mailbox-receiver"

    _assert(
        sender_start.get("job_dir") == str(expected_sender_job),
        "sender default job_dir should stay under the project worktree",
    )
    _assert(
        receiver_start.get("job_dir") == str(expected_receiver_job),
        "receiver default job_dir should stay under the project worktree",
    )
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "sender_job_dir": sender_start.get("job_dir"),
            "receiver_job_dir": receiver_start.get("job_dir"),
            "stop_result_path": str((demo_dir / "stop_result.json").resolve()),
        },
    }


def _scenario_auto_explicit_jobs_dir(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the explicit jobs-dir override for `auto`."""

    demo_dir = scenario_dir / "demo"
    jobs_dir = scenario_dir / "jobs-root"
    command = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
        jobs_dir=jobs_dir,
    )
    _assert(command["exit_code"] == 0, "auto scenario with explicit jobs dir should succeed")

    sender_start = _read_json(demo_dir / "sender_start.json")
    receiver_start = _read_json(demo_dir / "receiver_start.json")
    _assert(
        sender_start.get("job_dir") == str(jobs_dir / "AGENTSYS-mailbox-sender"),
        "sender explicit job_dir should use the selected jobs root",
    )
    _assert(
        receiver_start.get("job_dir") == str(jobs_dir / "AGENTSYS-mailbox-receiver"),
        "receiver explicit job_dir should use the selected jobs root",
    )
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "jobs_dir": str(jobs_dir.resolve()),
        "checks": {
            "sender_job_dir": sender_start.get("job_dir"),
            "receiver_job_dir": receiver_start.get("job_dir"),
        },
    }


def _scenario_stepwise_start_roundtrip_verify_stop(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the stepwise command surface."""

    demo_dir = scenario_dir / "demo"
    for command_name in ("start", "roundtrip", "verify", "stop"):
        command = _run_wrapper(
            repo_root=repo_root,
            pack_dir=pack_dir,
            scenario_dir=scenario_dir,
            commands=commands,
            command=command_name,
            demo_output_dir=demo_dir,
        )
        _assert(command["exit_code"] == 0, f"{command_name} should succeed")

    _assert((demo_dir / "verify_result.json").is_file(), "verify should emit verify_result.json")
    _assert((demo_dir / "sender_stop.json").is_file(), "stop should emit sender_stop.json")
    _assert((demo_dir / "receiver_stop.json").is_file(), "stop should emit receiver_stop.json")
    stop_result = _load_stop_result(demo_dir)
    _assert(bool(stop_result.get("stopped")), "stepwise stop should report success")
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "verify_result_path": str((demo_dir / "verify_result.json").resolve()),
            "stop_result_path": str((demo_dir / "stop_result.json").resolve()),
        },
    }


def _scenario_rerun_valid_project_reuse(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate rerun behavior against an existing compatible project worktree."""

    demo_dir = scenario_dir / "demo"
    first_run = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
    )
    _assert(first_run["exit_code"] == 0, "first auto rerun scenario should succeed")

    reuse_marker = demo_dir / "project" / "reuse-marker.txt"
    reuse_marker.write_text("keep me\n", encoding="utf-8")

    second_run = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
    )
    _assert(second_run["exit_code"] == 0, "second auto rerun scenario should succeed")
    _assert(reuse_marker.is_file(), "valid project worktree should be reused across reruns")
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "reuse_marker_path": str(reuse_marker.resolve()),
            "reuse_marker_preserved": True,
        },
    }


def _scenario_incompatible_project_dir(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate failure when `project/` already exists incompatibly."""

    demo_dir = scenario_dir / "demo"
    incompatible_project = demo_dir / "project"
    incompatible_project.mkdir(parents=True, exist_ok=True)
    (incompatible_project / "README.txt").write_text("not a worktree\n", encoding="utf-8")

    command = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
    )
    _assert(command["exit_code"] == 1, "incompatible project dir should fail clearly")
    stderr_text = Path(command["stderr_path"]).read_text(encoding="utf-8")
    _assert(
        "not a git worktree of the repository" in stderr_text,
        "failure should explain worktree mismatch",
    )
    _assert(
        not (demo_dir / "sender_start.json").exists(),
        "startup should stop before live session creation",
    )
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "error_contains_worktree_mismatch": True,
            "sender_start_created": False,
        },
    }


def _scenario_verify_snapshot_refresh(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate snapshot refresh through the pack-owned verify command."""

    demo_dir = scenario_dir / "demo"
    expected_report_path = pack_dir / "expected_report" / "report.json"
    original_expected = expected_report_path.read_text(encoding="utf-8")
    try:
        for command_name in ("start", "roundtrip"):
            command = _run_wrapper(
                repo_root=repo_root,
                pack_dir=pack_dir,
                scenario_dir=scenario_dir,
                commands=commands,
                command=command_name,
                demo_output_dir=demo_dir,
            )
            _assert(
                command["exit_code"] == 0,
                f"{command_name} should succeed before snapshot verification",
            )

        verify_command = _run_wrapper(
            repo_root=repo_root,
            pack_dir=pack_dir,
            scenario_dir=scenario_dir,
            commands=commands,
            command="verify",
            demo_output_dir=demo_dir,
            snapshot=True,
        )
        _assert(verify_command["exit_code"] == 0, "verify --snapshot-report should succeed")
        updated_expected = expected_report_path.read_text(encoding="utf-8")
        sanitized_report = (demo_dir / "report.sanitized.json").read_text(encoding="utf-8")
        _assert(
            updated_expected == sanitized_report,
            "snapshot refresh should write sanitized content only",
        )
    finally:
        expected_report_path.write_text(original_expected, encoding="utf-8")

    stop_command = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="stop",
        demo_output_dir=demo_dir,
    )
    _assert(stop_command["exit_code"] == 0, "stop should succeed after snapshot verification")
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "snapshot_refreshed": True,
            "verify_result_path": str((demo_dir / "verify_result.json").resolve()),
        },
    }


def _scenario_cleanup_ownership_reused_managed_cao(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate ownership-aware cleanup when CAO is reused."""

    demo_dir = scenario_dir / "demo"
    env_updates = {"FAKE_CAO_REUSE": "1"}
    for command_name in ("start", "roundtrip", "stop"):
        command = _run_wrapper(
            repo_root=repo_root,
            pack_dir=pack_dir,
            scenario_dir=scenario_dir,
            commands=commands,
            command=command_name,
            demo_output_dir=demo_dir,
            env_updates=env_updates,
        )
        _assert(command["exit_code"] == 0, f"{command_name} should succeed when reusing a managed CAO")
    stop_result = _load_stop_result(demo_dir)
    cao_stop = stop_result.get("cao_stop")
    _assert(isinstance(cao_stop, dict), "stop_result should record CAO ownership details")
    _assert(
        cao_stop.get("ownership") == "reused-existing-process",
        "stop should not stop a managed CAO that this run only reused",
    )
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "cao_ownership": cao_stop.get("ownership"),
            "cleanup_mode": bool(stop_result.get("cleanup")),
        },
    }


def _scenario_partial_failure_cleanup(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate cleanup artifacts for a synthetic partial failure."""

    demo_dir = scenario_dir / "demo"
    command = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
        env_updates={"MAILBOX_ROUNDTRIP_DEMO_FAULT": "fail-after-receiver-start"},
    )
    _assert(
        command["exit_code"] == 1, "partial failure scenario should exit with a command failure"
    )
    stop_result = _load_stop_result(demo_dir)
    _assert(bool(stop_result.get("cleanup")), "partial failure should record cleanup mode")
    for artifact_name in (
        "cleanup_sender_stop.json",
        "cleanup_receiver_stop.json",
        "cleanup_cao_stop.json",
    ):
        _assert((demo_dir / artifact_name).is_file(), f"missing cleanup artifact: {artifact_name}")
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "cleanup_mode": bool(stop_result.get("cleanup")),
            "cleanup_artifacts_present": True,
        },
    }


def _scenario_interrupted_run_cleanup(
    repo_root: Path,
    pack_dir: Path,
    scenario_dir: Path,
    commands: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate cleanup artifacts for a synthetic interruption."""

    demo_dir = scenario_dir / "demo"
    command = _run_wrapper(
        repo_root=repo_root,
        pack_dir=pack_dir,
        scenario_dir=scenario_dir,
        commands=commands,
        command="auto",
        demo_output_dir=demo_dir,
        env_updates={"MAILBOX_ROUNDTRIP_DEMO_FAULT": "interrupt-after-mail-send"},
    )
    _assert(command["exit_code"] == 130, "interrupted scenario should surface exit code 130")
    stop_result = _load_stop_result(demo_dir)
    _assert(bool(stop_result.get("cleanup")), "interrupt should record cleanup mode")
    _assert(
        (demo_dir / "mail_send.json").is_file(), "interrupt should leave diagnosable send artifacts"
    )
    _assert(
        not (demo_dir / "mail_reply.json").exists(), "interrupt should stop before reply completes"
    )
    for artifact_name in (
        "cleanup_sender_stop.json",
        "cleanup_receiver_stop.json",
        "cleanup_cao_stop.json",
    ):
        _assert((demo_dir / artifact_name).is_file(), f"missing cleanup artifact: {artifact_name}")
    return {
        "demo_output_dir": str(demo_dir.resolve()),
        "checks": {
            "cleanup_mode": bool(stop_result.get("cleanup")),
            "mail_send_preserved": True,
            "mail_reply_present": False,
        },
    }


SCENARIOS: dict[str, ScenarioFunc] = {
    "auto-implicit-jobs-dir": _scenario_auto_implicit_jobs_dir,
    "auto-explicit-jobs-dir": _scenario_auto_explicit_jobs_dir,
    "stepwise-start-roundtrip-verify-stop": _scenario_stepwise_start_roundtrip_verify_stop,
    "rerun-valid-project-reuse": _scenario_rerun_valid_project_reuse,
    "incompatible-project-dir": _scenario_incompatible_project_dir,
    "verify-snapshot-refresh": _scenario_verify_snapshot_refresh,
    "cleanup-ownership-reused-managed-cao": _scenario_cleanup_ownership_reused_managed_cao,
    "partial-failure-cleanup": _scenario_partial_failure_cleanup,
    "interrupted-run-cleanup": _scenario_interrupted_run_cleanup,
}


def _build_parser() -> argparse.ArgumentParser:
    """Build the scenario runner CLI parser."""

    parser = argparse.ArgumentParser(description="Run mailbox roundtrip demo automation scenarios")
    parser.add_argument("--automation-root", type=Path, required=True)
    parser.add_argument("--scenario", action="append", choices=sorted(SCENARIOS))
    parser.add_argument("--list-scenarios", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the selected automation scenarios."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.list_scenarios:
        for scenario_id in sorted(SCENARIOS):
            print(scenario_id)
        return 0

    script_dir = Path(__file__).resolve().parent
    pack_dir = script_dir.parent
    repo_root = pack_dir.parents[2]
    selected_scenarios = args.scenario if args.scenario is not None else list(SCENARIOS)

    automation_root = args.automation_root.resolve()
    automation_root.mkdir(parents=True, exist_ok=True)

    suite_results: list[dict[str, Any]] = []
    for scenario_id in selected_scenarios:
        scenario_dir = automation_root / scenario_id
        if scenario_dir.exists():
            shutil.rmtree(scenario_dir)
        scenario_dir.mkdir(parents=True, exist_ok=True)

        commands: list[dict[str, Any]] = []
        result_payload: dict[str, Any]
        try:
            result_payload = SCENARIOS[scenario_id](repo_root, pack_dir, scenario_dir, commands)
            scenario_result = {
                "scenario_id": scenario_id,
                "ok": True,
                "scenario_dir": str(scenario_dir.resolve()),
                "commands": commands,
                **result_payload,
            }
        except Exception as exc:
            scenario_result = {
                "scenario_id": scenario_id,
                "ok": False,
                "scenario_dir": str(scenario_dir.resolve()),
                "commands": commands,
                "error": str(exc),
            }

        _write_json(scenario_dir / "scenario-result.json", scenario_result)
        suite_results.append(
            {
                "scenario_id": scenario_id,
                "ok": scenario_result["ok"],
                "scenario_dir": scenario_result["scenario_dir"],
                "result_path": str((scenario_dir / "scenario-result.json").resolve()),
            }
        )

    suite_summary = {
        "automation_root": str(automation_root),
        "total": len(suite_results),
        "passed": sum(1 for item in suite_results if item["ok"]),
        "failed": sum(1 for item in suite_results if not item["ok"]),
        "scenarios": suite_results,
    }
    _write_json(automation_root / "suite-summary.json", suite_summary)
    print(json.dumps(suite_summary, indent=2, sort_keys=True))
    return 0 if suite_summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

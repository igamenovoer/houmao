#!/usr/bin/env python3
"""Sanitize and validate CAO launcher demo reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_FLOW_ORDER = [
    "status_before_start",
    "start",
    "status_after_start",
    "stop",
    "status_after_stop",
]


def _as_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _as_bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _as_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _as_str(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _read_step(
    flow: Mapping[str, Any],
    *,
    step_key: str,
    expected_operation: str,
) -> tuple[int, Mapping[str, Any]]:
    step = _as_mapping(flow.get(step_key), name=f"flow.{step_key}")
    payload = _as_mapping(step.get("payload"), name=f"flow.{step_key}.payload")
    exit_code = _as_int(step.get("exit_code"), name=f"flow.{step_key}.exit_code")
    operation = _as_str(
        payload.get("operation"), name=f"flow.{step_key}.payload.operation"
    )
    if operation != expected_operation:
        raise ValueError(
            f"flow.{step_key}.payload.operation must be {expected_operation!r}, got {operation!r}"
        )
    return exit_code, payload


def _assert_path_layout(
    *,
    expected_artifact_dir: Path,
    start_payload: Mapping[str, Any],
) -> None:
    artifact_dir = Path(
        _as_str(start_payload.get("artifact_dir"), name="start.payload.artifact_dir")
    )
    pid_file = Path(
        _as_str(start_payload.get("pid_file"), name="start.payload.pid_file")
    )
    log_file = Path(
        _as_str(start_payload.get("log_file"), name="start.payload.log_file")
    )
    launcher_result_file = Path(
        _as_str(
            start_payload.get("launcher_result_file"),
            name="start.payload.launcher_result_file",
        )
    )

    if artifact_dir != expected_artifact_dir:
        raise ValueError(
            "start.payload.artifact_dir does not match expected artifact directory"
        )
    if pid_file != expected_artifact_dir / "cao-server.pid":
        raise ValueError("start.payload.pid_file does not match expected pid file path")
    if log_file != expected_artifact_dir / "cao-server.log":
        raise ValueError("start.payload.log_file does not match expected log file path")
    if launcher_result_file != expected_artifact_dir / "launcher_result.json":
        raise ValueError(
            "start.payload.launcher_result_file does not match expected launcher result path"
        )


def sanitize_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a raw report and return deterministic sanitized output."""

    demo_name = _as_str(report.get("demo"), name="demo")
    if demo_name != "cao-server-launcher":
        raise ValueError("demo must be 'cao-server-launcher'")

    flow_order = report.get("flow_order")
    if flow_order != _FLOW_ORDER:
        raise ValueError(f"flow_order must equal {_FLOW_ORDER!r}")

    flow = _as_mapping(report.get("flow"), name="flow")
    status_before_exit, status_before_payload = _read_step(
        flow, step_key="status_before_start", expected_operation="status"
    )
    start_exit, start_payload = _read_step(
        flow, step_key="start", expected_operation="start"
    )
    status_after_start_exit, status_after_start_payload = _read_step(
        flow, step_key="status_after_start", expected_operation="status"
    )
    stop_exit, stop_payload = _read_step(
        flow, step_key="stop", expected_operation="stop"
    )
    status_after_stop_exit, status_after_stop_payload = _read_step(
        flow, step_key="status_after_stop", expected_operation="status"
    )

    if status_before_exit not in {0, 2}:
        raise ValueError("flow.status_before_start.exit_code must be 0 or 2")
    if status_after_stop_exit not in {0, 2}:
        raise ValueError("flow.status_after_stop.exit_code must be 0 or 2")
    if start_exit != 0:
        raise ValueError("flow.start.exit_code must be 0")
    if status_after_start_exit != 0:
        raise ValueError("flow.status_after_start.exit_code must be 0")
    if stop_exit != 0:
        raise ValueError("flow.stop.exit_code must be 0")

    start_healthy = _as_bool(start_payload.get("healthy"), name="start.payload.healthy")
    if not start_healthy:
        raise ValueError("flow.start.payload.healthy must be true")
    post_start_healthy = _as_bool(
        status_after_start_payload.get("healthy"),
        name="status_after_start.payload.healthy",
    )
    if not post_start_healthy:
        raise ValueError("flow.status_after_start.payload.healthy must be true")

    start_new = _as_bool(
        start_payload.get("started_new_process"),
        name="start.payload.started_new_process",
    )
    reused_existing = _as_bool(
        start_payload.get("reused_existing_process"),
        name="start.payload.reused_existing_process",
    )
    if start_new == reused_existing:
        raise ValueError("start mode must be exactly one of new/reused")

    stop_stopped = _as_bool(stop_payload.get("stopped"), name="stop.payload.stopped")
    stop_already = _as_bool(
        stop_payload.get("already_stopped"), name="stop.payload.already_stopped"
    )
    if stop_stopped == stop_already:
        raise ValueError("stop outcome must be exactly one of stopped/already_stopped")

    artifact_checks = _as_mapping(report.get("artifact_checks"), name="artifact_checks")
    expected_artifact_dir = Path(
        _as_str(
            artifact_checks.get("expected_artifact_dir"),
            name="artifact_checks.expected_artifact_dir",
        )
    )
    _assert_path_layout(
        expected_artifact_dir=expected_artifact_dir,
        start_payload=start_payload,
    )

    paths_match = _as_bool(
        artifact_checks.get("paths_match"),
        name="artifact_checks.paths_match",
    )
    if not paths_match:
        raise ValueError("artifact_checks.paths_match must be true")
    launcher_result_exists = _as_bool(
        artifact_checks.get("launcher_result_exists_after_start"),
        name="artifact_checks.launcher_result_exists_after_start",
    )
    if not launcher_result_exists:
        raise ValueError(
            "artifact_checks.launcher_result_exists_after_start must be true"
        )

    _as_bool(
        status_before_payload.get("healthy"),
        name="status_before_start.payload.healthy",
    )
    _as_bool(
        status_after_stop_payload.get("healthy"),
        name="status_after_stop.payload.healthy",
    )

    return {
        "artifact_layout": {
            "artifact_dir": "<WORKSPACE>/runtime/cao-server/<HOST>-<PORT>",
            "launcher_result_file": (
                "<WORKSPACE>/runtime/cao-server/<HOST>-<PORT>/launcher_result.json"
            ),
            "log_file": "<WORKSPACE>/runtime/cao-server/<HOST>-<PORT>/cao-server.log",
            "pid_file": "<WORKSPACE>/runtime/cao-server/<HOST>-<PORT>/cao-server.pid",
        },
        "base_url": "<BASE_URL>",
        "checks": {
            "artifact_layout_matches": True,
            "launcher_result_exists_after_start": True,
            "post_start_status_healthy": True,
            "start_exit_code_is_zero": True,
            "start_health_is_true": True,
            "start_mode_valid": True,
            "stop_exit_code_is_zero": True,
            "stop_outcome_valid": True,
        },
        "demo": "cao-server-launcher",
        "flow": ["status", "start", "status", "stop", "status"],
        "post_stop_status_healthy": "<BOOL>",
        "pre_start_status_healthy": "<BOOL>",
        "start_mode": "<STARTED_NEW_OR_REUSED_EXISTING>",
        "stop_outcome": "<STOPPED_OR_ALREADY_STOPPED>",
        "workspace": "<WORKSPACE>",
    }


def main() -> int:
    """CLI for report sanitization."""

    parser = argparse.ArgumentParser(description="Sanitize CAO launcher demo report")
    parser.add_argument("actual_report", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        report_payload = json.loads(args.actual_report.read_text(encoding="utf-8"))
        report = _as_mapping(report_payload, name="report")
        sanitized = sanitize_report(report)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"sanitize failed: {exc}", file=sys.stderr)
        return 1

    serialized = json.dumps(sanitized, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(serialized, end="")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(f"sanitized report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

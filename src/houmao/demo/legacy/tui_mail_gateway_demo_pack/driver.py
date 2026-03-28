"""CLI driver for the TUI mail gateway demo pack."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from . import runtime as runtime_helpers
from .mailbox import (
    DemoMailboxError,
    build_run_id,
    capture_turn_evidence,
    collect_gateway_status,
    collect_mailbox_snapshot,
    collect_notifier_status,
    deliver_turn_message,
    detect_processed_turns,
    gateway_can_accept_work,
    observe_unread_delivery,
)
from houmao.demo.legacy.launch_support import resolve_demo_preset_launch
from .models import (
    DEFAULT_EXPECTED_REPORT_RELATIVE,
    DEFAULT_PARAMETERS_RELATIVE,
    DemoPaths,
    DemoParameters,
    DemoState,
    SupportedTool,
    build_demo_layout,
    default_demo_output_dir,
    load_demo_parameters,
    load_demo_state,
    resolve_repo_relative_path,
    save_demo_state,
    utc_now_iso,
    write_json,
)
from .reporting import (
    build_inspect_snapshot,
    build_report_snapshot,
    sanitize_report,
    validate_report_contract,
    verify_sanitized_report,
)
from .runtime import (
    DemoRuntimeError,
    attach_gateway,
    build_brain,
    build_demo_environment,
    cao_profile_store,
    enable_notifier,
    load_session_details,
    prepare_output_root,
    provision_project_workdir,
    start_cao_service,
    start_mailbox_session,
    stop_cao_service,
    stop_session,
)


class DemoPackError(RuntimeError):
    """Raised when the pack cannot continue safely."""


def main(argv: list[str] | None = None) -> int:
    """Run the demo-pack CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return _command_start(args)
        if args.command == "drive":
            return _command_drive(args)
        if args.command == "inspect":
            return _command_inspect(args)
        if args.command == "verify":
            return _command_verify(args)
        if args.command == "stop":
            return _command_stop(args)
        if args.command == "auto":
            return _command_auto(args)
        raise DemoPackError(f"unsupported command: {args.command}")
    except (DemoPackError, DemoRuntimeError, DemoMailboxError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the demo-pack CLI parser."""

    parser = argparse.ArgumentParser(description="TUI mail gateway demo pack")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    _add_common_arguments(start_parser)
    start_parser.add_argument("--tool", choices=("claude", "codex"), required=True)

    drive_parser = subparsers.add_parser("drive")
    _add_common_arguments(drive_parser)
    drive_parser.add_argument("--timeout-seconds", type=float, default=None)

    inspect_parser = subparsers.add_parser("inspect")
    _add_common_arguments(inspect_parser)

    verify_parser = subparsers.add_parser("verify")
    _add_common_arguments(verify_parser)
    verify_parser.add_argument(
        "--expected-report",
        default=DEFAULT_EXPECTED_REPORT_RELATIVE,
        help="Repository-relative or absolute expected sanitized report path.",
    )
    verify_parser.add_argument("--snapshot", action="store_true")

    stop_parser = subparsers.add_parser("stop")
    _add_common_arguments(stop_parser)

    auto_parser = subparsers.add_parser("auto")
    _add_common_arguments(auto_parser)
    auto_parser.add_argument("--tool", choices=("claude", "codex"), required=True)
    auto_parser.add_argument("--timeout-seconds", type=float, default=None)
    auto_parser.add_argument(
        "--expected-report",
        default=DEFAULT_EXPECTED_REPORT_RELATIVE,
        help="Repository-relative or absolute expected sanitized report path.",
    )
    auto_parser.add_argument("--snapshot", action="store_true")

    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments shared across pack commands."""

    parser.add_argument(
        "--demo-output-dir",
        default=None,
        help="Repository-relative or absolute demo output root.",
    )
    parser.add_argument(
        "--parameters",
        default=DEFAULT_PARAMETERS_RELATIVE,
        help="Repository-relative or absolute tracked parameters file.",
    )


def _repo_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[4]


def _load_parameters(args: argparse.Namespace, *, repo_root: Path) -> DemoParameters:
    """Load tracked demo parameters for this invocation."""

    parameters_path = resolve_repo_relative_path(args.parameters, repo_root=repo_root)
    return load_demo_parameters(parameters_path)


def _resolve_agent_def_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the agent-definition root with `AGENT_DEF_DIR` override support."""

    override = os.environ.get("AGENT_DEF_DIR")
    return resolve_repo_relative_path(
        override if override is not None else parameters.agent_def_dir,
        repo_root=repo_root,
    )


def _resolve_paths(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    tool: SupportedTool | None,
) -> Any:
    """Resolve the demo output layout for one command invocation."""

    if args.demo_output_dir is not None:
        return build_demo_layout(
            demo_output_dir=resolve_repo_relative_path(args.demo_output_dir, repo_root=repo_root)
        )
    if tool is not None:
        return build_demo_layout(
            demo_output_dir=default_demo_output_dir(repo_root=repo_root, tool=tool)
        )
    return build_demo_layout(demo_output_dir=_discover_existing_output_root(repo_root=repo_root))


def _discover_existing_output_root(*, repo_root: Path) -> Path:
    """Auto-select the only existing default tool output root when unambiguous."""

    candidates: list[Path] = []
    for tool in ("claude", "codex"):
        output_root = default_demo_output_dir(repo_root=repo_root, tool=tool)
        if (output_root / "control" / "demo_state.json").is_file():
            candidates.append(output_root)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise DemoPackError(
            "no persisted demo state was found under the default Claude/Codex output roots; "
            "pass `--demo-output-dir`"
        )
    raise DemoPackError(
        "multiple default demo roots contain persisted state; pass `--demo-output-dir`"
    )


def _require_demo_state(paths: DemoPaths) -> DemoState:
    """Load persisted demo state or fail clearly."""

    if not paths.state_path.is_file():
        raise DemoPackError(f"demo state not found: {paths.state_path}")
    return load_demo_state(paths.state_path)


def _command_start(args: argparse.Namespace) -> int:
    """Implement `start`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=args.tool)
    state = _start_demo(
        repo_root=repo_root,
        paths=paths,
        parameters=parameters,
        tool=args.tool,
    )
    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "selected_tool": state.selected_tool,
                "session_manifest_path": str(state.session_manifest_path),
                "gateway_host": state.gateway_host,
                "gateway_port": state.gateway_port,
            },
            indent=2,
        )
    )
    return 0


def _start_demo(
    *,
    repo_root: Path,
    paths: DemoPaths,
    parameters: DemoParameters,
    tool: SupportedTool,
) -> DemoState:
    """Start one mailbox-enabled TUI session for the selected tool."""

    existing_state = load_demo_state(paths.state_path) if paths.state_path.is_file() else None
    if existing_state is not None and existing_state.active:
        if existing_state.selected_tool != tool:
            raise DemoPackError(
                f"demo already started for `{existing_state.selected_tool}` at `{paths.output_root}`"
            )
        return existing_state

    allow_reprovision = existing_state is not None and not existing_state.active
    prepare_output_root(paths=paths, allow_reprovision=allow_reprovision)
    agent_def_dir = _resolve_agent_def_dir(parameters=parameters, repo_root=repo_root)
    project_fixture = resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)
    tool_parameters = parameters.tool_parameters(tool=tool)
    blueprint_path = resolve_repo_relative_path(tool_parameters.blueprint, repo_root=repo_root)
    resolved_launch = resolve_demo_preset_launch(
        agent_def_dir=agent_def_dir,
        preset_path=blueprint_path,
    )
    env = build_demo_environment(paths=paths)

    start_cao_service(
        repo_root=repo_root,
        paths=paths,
        cao_base_url=parameters.cao_base_url,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    build_result = build_brain(
        repo_root=repo_root,
        paths=paths,
        agent_def_dir=agent_def_dir,
        blueprint_path=blueprint_path,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    project_workdir = provision_project_workdir(
        project_fixture=project_fixture,
        project_dir=paths.project_dir,
        allow_reprovision=allow_reprovision,
        build_result=build_result,
    )
    session_payload = start_mailbox_session(
        repo_root=repo_root,
        paths=paths,
        agent_def_dir=agent_def_dir,
        build_result=build_result,
        project_workdir=project_workdir,
        tool_parameters=tool_parameters.model_copy(update={"blueprint": blueprint_path}),
        role_name=resolved_launch.role_name,
        cao_base_url=parameters.cao_base_url,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    session_manifest_path = Path(str(session_payload["session_manifest"])).resolve()
    attach_payload = attach_gateway(
        repo_root=repo_root,
        paths=paths,
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_manifest_path,
        gateway_host=parameters.gateway.host,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    session_details = load_session_details(session_manifest_path=session_manifest_path)
    state = DemoState(
        created_at_utc=utc_now_iso(),
        repo_root=repo_root,
        output_root=paths.output_root,
        selected_tool=tool,
        run_id=build_run_id(),
        agent_def_dir=agent_def_dir,
        project_fixture=project_fixture,
        project_workdir=project_workdir,
        blueprint_path=blueprint_path,
        brain_manifest_path=build_result.manifest_path,
        brain_home_path=build_result.home_path,
        launch_helper_path=build_result.launch_helper_path,
        session_manifest_path=session_manifest_path,
        session_root=Path(session_details["session_root"]).resolve(),
        agent_identity=str(session_details["agent_identity"]),
        agent_name=session_details["agent_name"],
        agent_id=session_details["agent_id"],
        tmux_session_name=str(session_details["tmux_session_name"]),
        terminal_id=session_details["terminal_id"],
        mailbox_principal_id=tool_parameters.mailbox_principal_id,
        mailbox_address=tool_parameters.mailbox_address,
        gateway_root=Path(str(attach_payload["gateway_root"])).resolve(),
        gateway_host=str(attach_payload["gateway_host"]),
        gateway_port=int(attach_payload["gateway_port"]),
        cao_base_url=parameters.cao_base_url,
        cao_profile_store=cao_profile_store(paths=paths),
        launcher_config_path=paths.launcher_config_path,
        cadence_seconds=parameters.drive.cadence_seconds,
        turn_limit=parameters.drive.turn_limit,
        drive_timeout_seconds=parameters.drive.timeout_seconds,
        notifier_interval_seconds=parameters.gateway.notifier_interval_seconds,
    )
    notifier_payload = enable_notifier(state=state)
    write_json(paths.control_dir / "notifier_enable.json", notifier_payload)
    save_demo_state(paths.state_path, state)
    return state


def _command_drive(args: argparse.Namespace) -> int:
    """Implement `drive`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _drive_demo(
        repo_root=repo_root,
        paths=paths,
        parameters=parameters,
        timeout_seconds=args.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "delivery_count": state.delivery_count,
                "processed_turn_count": state.processed_turn_count,
            },
            indent=2,
        )
    )
    return 0


def _drive_demo(
    *,
    repo_root: Path,
    paths: DemoPaths,
    parameters: DemoParameters,
    timeout_seconds: float | None,
) -> DemoState:
    """Run the five-second unread-gated harness loop until three processed turns complete."""

    state = _require_demo_state(paths)
    if not state.active:
        raise DemoPackError("demo is not active; run `start` first")
    resolved_timeout = state.drive_timeout_seconds if timeout_seconds is None else timeout_seconds
    deadline = time.monotonic() + resolved_timeout

    while state.processed_turn_count < state.turn_limit:
        if time.monotonic() >= deadline:
            raise DemoPackError(f"drive timed out after {resolved_timeout:.1f}s")

        mailbox_snapshot = collect_mailbox_snapshot(state)
        state, completed_turns = detect_processed_turns(
            state=state, mailbox_snapshot=mailbox_snapshot
        )
        if completed_turns:
            updated_turns = []
            completed_by_index = {turn.turn_index: turn for turn in completed_turns}
            for turn in state.turns:
                if turn.turn_index in completed_by_index and turn.evidence_snapshot_path is None:
                    updated_turns.append(
                        capture_turn_evidence(
                            paths=paths, state=state, turn=completed_by_index[turn.turn_index]
                        )
                    )
                else:
                    updated_turns.append(turn)
            state = state.model_copy(update={"turns": updated_turns})
            save_demo_state(paths.state_path, state)

        if state.processed_turn_count >= state.turn_limit:
            break

        gateway_status = collect_gateway_status(state)
        if state.delivery_count < state.turn_limit and gateway_can_accept_work(
            gateway_status=gateway_status,
            mailbox_snapshot=mailbox_snapshot,
        ):
            next_turn_index = state.delivery_count + 1
            delivered_turn = deliver_turn_message(
                repo_root=repo_root,
                paths=paths,
                parameters=parameters,
                state=state,
                turn_index=next_turn_index,
            )
            updated_turns = list(state.turns)
            updated_turns.append(delivered_turn)
            state = state.model_copy(update={"turns": updated_turns})
            mailbox_after_delivery = collect_mailbox_snapshot(state)
            observed_turn = observe_unread_delivery(
                turn=state.turns[-1],
                mailbox_snapshot=mailbox_after_delivery,
            )
            updated_turns[-1] = observed_turn
            state = state.model_copy(update={"turns": updated_turns})
            save_demo_state(paths.state_path, state)

        if state.processed_turn_count < state.turn_limit:
            time.sleep(float(state.cadence_seconds))

    save_demo_state(paths.state_path, state)
    return state


def _command_inspect(args: argparse.Namespace) -> int:
    """Implement `inspect`."""

    repo_root = _repo_root()
    _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    inspection = _inspect_demo(paths=paths)
    print(
        json.dumps(
            {
                "inspect_path": str(paths.inspect_path),
                "processed_turn_count": inspection["harness"]["processed_turn_count"],
            },
            indent=2,
        )
    )
    return 0


def _inspect_demo(*, paths: DemoPaths) -> dict[str, Any]:
    """Build and persist one raw inspect snapshot."""

    state = _require_demo_state(paths)
    gateway_status = collect_gateway_status(state)
    notifier_status = collect_notifier_status(state)
    mailbox_snapshot = collect_mailbox_snapshot(state)
    inspection = build_inspect_snapshot(
        state=state,
        gateway_status=gateway_status,
        notifier_status=notifier_status,
        mailbox_snapshot=mailbox_snapshot,
    )
    write_json(paths.inspect_path, inspection)
    return inspection


def _command_verify(args: argparse.Namespace) -> int:
    """Implement `verify`."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    _verify_demo(
        repo_root=repo_root,
        paths=paths,
        expected_report=args.expected_report,
        snapshot=args.snapshot,
    )
    print(
        json.dumps(
            {
                "report_path": str(paths.report_path),
                "sanitized_report_path": str(paths.sanitized_report_path),
            },
            indent=2,
        )
    )
    return 0


def _verify_demo(
    *,
    repo_root: Path,
    paths: DemoPaths,
    expected_report: str,
    snapshot: bool,
) -> None:
    """Build, sanitize, validate, and verify the demo report."""

    state = _require_demo_state(paths)
    inspection = _inspect_demo(paths=paths)
    report = build_report_snapshot(state=state, inspect_snapshot=inspection)
    write_json(paths.report_path, report)
    validate_report_contract(report)
    sanitized = sanitize_report(report)
    write_json(paths.sanitized_report_path, sanitized)
    expected_path = resolve_repo_relative_path(expected_report, repo_root=repo_root)
    if snapshot:
        write_json(expected_path, sanitized)
        return
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    verify_sanitized_report(sanitized, expected)


def _command_stop(args: argparse.Namespace) -> int:
    """Implement `stop`."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    payload = _stop_demo(repo_root=repo_root, paths=paths)
    print(json.dumps(payload, indent=2))
    return 0


def _stop_demo(*, repo_root: Path, paths: DemoPaths) -> dict[str, Any]:
    """Idempotently stop the notifier, session, and CAO while preserving artifacts."""

    if not paths.state_path.is_file():
        return {"already_stopped": True, "detail": "demo state missing"}
    state = load_demo_state(paths.state_path)
    if not state.active:
        return {"already_stopped": True, "detail": "demo already inactive"}

    notifier_payload: dict[str, Any] | None = None
    session_payload: dict[str, Any] | None = None
    cao_payload: dict[str, Any] | None = None
    try:
        notifier_payload = collect_notifier_status(state)
        if notifier_payload.get("enabled"):
            notifier_payload = runtime_helpers.disable_notifier(state=state)
            write_json(paths.control_dir / "notifier_disable.json", notifier_payload)
    except Exception as exc:
        notifier_payload = {"status": "error", "detail": str(exc)}

    try:
        session_payload = stop_session(
            repo_root=repo_root,
            paths=paths,
            state=state,
            timeout_seconds=state.drive_timeout_seconds,
        )
    except Exception as exc:
        session_payload = {"status": "error", "detail": str(exc)}

    try:
        cao_payload = stop_cao_service(
            repo_root=repo_root,
            paths=paths,
            timeout_seconds=state.drive_timeout_seconds,
        )
    except Exception as exc:
        cao_payload = {"status": "error", "detail": str(exc)}

    updated_state = state.model_copy(update={"active": False, "stopped_at_utc": utc_now_iso()})
    save_demo_state(paths.state_path, updated_state)
    return {
        "already_stopped": False,
        "notifier": notifier_payload,
        "session": session_payload,
        "cao": cao_payload,
        "state_path": str(paths.state_path),
    }


def _command_auto(args: argparse.Namespace) -> int:
    """Implement `auto`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=args.tool)
    started = False
    try:
        _start_demo(repo_root=repo_root, paths=paths, parameters=parameters, tool=args.tool)
        started = True
        _drive_demo(
            repo_root=repo_root,
            paths=paths,
            parameters=parameters,
            timeout_seconds=args.timeout_seconds,
        )
        _verify_demo(
            repo_root=repo_root,
            paths=paths,
            expected_report=args.expected_report,
            snapshot=args.snapshot,
        )
    finally:
        if started:
            _stop_demo(repo_root=repo_root, paths=paths)
    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "report_path": str(paths.report_path),
                "sanitized_report_path": str(paths.sanitized_report_path),
            },
            indent=2,
        )
    )
    return 0

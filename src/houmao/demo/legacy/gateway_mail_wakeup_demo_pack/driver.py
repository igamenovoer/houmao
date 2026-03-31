"""CLI driver for the serverless gateway mail wake-up demo pack."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from .mailbox import (
    DemoMailboxError,
    build_run_id,
    collect_mailbox_snapshot,
    collect_output_file_payload,
    deliver_configured_automatic_message,
    deliver_manual_message,
    gateway_can_accept_work,
    observe_delivery_state,
    wait_for_delivery_completion,
)
from .models import (
    DEFAULT_EXPECTED_REPORT_RELATIVE,
    DEFAULT_PARAMETERS_RELATIVE,
    PACK_NAME,
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
    build_demo_environment,
    disable_notifier,
    enable_notifier,
    expose_project_mailbox_skills,
    gateway_status,
    initialize_mailbox,
    load_session_details,
    notifier_status,
    prepare_output_root,
    provision_project_workdir,
    query_agent_show,
    query_agent_state,
    register_mailbox,
    run_launch_command,
    stop_agent,
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
        if args.command == "manual-send":
            return _command_manual_send(args)
        if args.command == "manual-send-many":
            return _command_manual_send_many(args)
        if args.command == "inspect":
            return _command_inspect(args)
        if args.command == "verify":
            return _command_verify(args)
        if args.command == "stop":
            return _command_stop(args)
        if args.command == "auto":
            return _command_auto(args)
        if args.command == "matrix":
            return _command_matrix(args)
        raise DemoPackError(f"unsupported command: {args.command}")
    except (DemoPackError, DemoRuntimeError, DemoMailboxError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the demo-pack CLI parser."""

    parser = argparse.ArgumentParser(description="Gateway mail wake-up demo pack")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    _add_common_arguments(start_parser)
    start_parser.add_argument("--tool", choices=("claude", "codex"), required=True)

    send_parser = subparsers.add_parser("manual-send")
    _add_common_arguments(send_parser)
    send_parser.add_argument("--subject", default=None)
    send_parser.add_argument("--body-content", default=None)
    send_parser.add_argument("--body-file", default=None)

    send_many_parser = subparsers.add_parser("manual-send-many")
    _add_common_arguments(send_many_parser)
    send_many_parser.add_argument("--count", type=int, required=True)
    send_many_parser.add_argument("--subject-prefix", default="Gateway burst")
    send_many_parser.add_argument("--body-content", default=None)
    send_many_parser.add_argument("--body-file", default=None)

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
    auto_parser.add_argument(
        "--expected-report",
        default=DEFAULT_EXPECTED_REPORT_RELATIVE,
        help="Repository-relative or absolute expected sanitized report path.",
    )
    auto_parser.add_argument("--snapshot", action="store_true")

    matrix_parser = subparsers.add_parser("matrix")
    _add_common_arguments(matrix_parser)
    matrix_parser.add_argument(
        "--expected-report",
        default=DEFAULT_EXPECTED_REPORT_RELATIVE,
        help="Repository-relative or absolute expected sanitized report path.",
    )
    matrix_parser.add_argument("--snapshot", action="store_true")

    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments shared across pack commands."""

    parser.add_argument(
        "--demo-output-dir",
        default=None,
        help="Pack-local output root override. For `matrix`, this is the shared tool-root parent.",
    )
    parser.add_argument(
        "--parameters",
        default=DEFAULT_PARAMETERS_RELATIVE,
        help="Repository-relative or absolute tracked parameters file.",
    )


def _repo_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[4]


def _pack_root(*, repo_root: Path) -> Path:
    """Return the repository-relative demo-pack root."""

    return (repo_root / "scripts" / "demo" / PACK_NAME).resolve()


def _load_parameters(args: argparse.Namespace, *, repo_root: Path) -> DemoParameters:
    """Load tracked demo parameters for this invocation."""

    parameters_path = resolve_repo_relative_path(args.parameters, repo_root=repo_root)
    return load_demo_parameters(parameters_path)


def _resolve_agent_def_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the agent-definition root with env override support."""

    override = os.environ.get("AGENT_DEF_DIR") or os.environ.get("HOUMAO_AGENT_DEF_DIR")
    return resolve_repo_relative_path(
        override if override is not None else parameters.agent_def_dir,
        repo_root=repo_root,
    )


def _resolve_paths(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    tool: SupportedTool | None,
) -> DemoPaths:
    """Resolve the demo output layout for one command invocation."""

    if args.demo_output_dir is not None:
        candidate = resolve_repo_relative_path(args.demo_output_dir, repo_root=repo_root)
        _require_pack_local_output_root(candidate, repo_root=repo_root)
        return build_demo_layout(demo_output_dir=candidate)
    if tool is not None:
        return build_demo_layout(
            demo_output_dir=default_demo_output_dir(repo_root=repo_root, tool=tool)
        )
    return build_demo_layout(demo_output_dir=_discover_existing_output_root(repo_root=repo_root))


def _resolve_matrix_paths(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    tool: SupportedTool,
) -> DemoPaths:
    """Resolve one tool-scoped output layout for the `matrix` command."""

    if args.demo_output_dir is None:
        return build_demo_layout(
            demo_output_dir=default_demo_output_dir(repo_root=repo_root, tool=tool)
        )
    base_root = resolve_repo_relative_path(args.demo_output_dir, repo_root=repo_root)
    _require_pack_local_output_root(base_root, repo_root=repo_root)
    return build_demo_layout(demo_output_dir=(base_root / tool))


def _require_pack_local_output_root(output_root: Path, *, repo_root: Path) -> None:
    """Require one selected output root to remain inside the demo pack directory."""

    pack_root = _pack_root(repo_root=repo_root)
    try:
        output_root.resolve().relative_to(pack_root)
    except ValueError as exc:
        raise DemoPackError(
            f"output root must remain inside `{pack_root}`; got `{output_root.resolve()}`"
        ) from exc


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
    state = _start_demo(repo_root=repo_root, paths=paths, parameters=parameters, tool=args.tool)
    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "selected_tool": state.selected_tool,
                "tracked_agent_id": state.tracked_agent_id,
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
    """Start one mailbox-enabled serverless local interactive session."""

    existing_state = load_demo_state(paths.state_path) if paths.state_path.is_file() else None
    if existing_state is not None and existing_state.active:
        if existing_state.selected_tool != tool:
            raise DemoPackError(
                f"demo already started for `{existing_state.selected_tool}` at `{paths.output_root}`"
            )
        return existing_state

    allow_reprovision = existing_state is not None and not existing_state.active
    prepare_output_root(paths=paths, allow_reprovision=allow_reprovision)
    project_fixture = resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)
    tool_parameters = parameters.tool_parameters(tool=tool)
    agent_def_dir = _resolve_agent_def_dir(parameters=parameters, repo_root=repo_root)
    env = build_demo_environment(paths=paths, agent_def_dir=agent_def_dir)
    initialize_mailbox(
        repo_root=repo_root,
        paths=paths,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    project_workdir = provision_project_workdir(
        project_fixture=project_fixture,
        project_dir=paths.project_dir,
        allow_reprovision=allow_reprovision,
    )
    run_id = build_run_id()
    launch_suffix = run_id.rsplit("-", 1)[-1]
    agent_name = f"{tool_parameters.agent_name_prefix}-{launch_suffix}"
    session_name = f"{tool_parameters.session_name_prefix}-{launch_suffix}"
    launch_payload = run_launch_command(
        cwd=project_workdir,
        stdout_path=paths.logs_dir / "agent-launch.stdout",
        stderr_path=paths.logs_dir / "agent-launch.stderr",
        selector=tool_parameters.selector,
        provider=tool_parameters.provider,
        agent_name=agent_name,
        session_name=session_name,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    write_json(paths.launch_path, launch_payload)
    agent_show = query_agent_show(
        repo_root=repo_root,
        paths=paths,
        agent_name=agent_name,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    register_mailbox(
        repo_root=repo_root,
        paths=paths,
        agent_name=agent_name,
        mailbox_principal_id=tool_parameters.mailbox_principal_id,
        mailbox_address=tool_parameters.mailbox_address,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    attach_payload = attach_gateway(
        repo_root=repo_root,
        paths=paths,
        agent_name=agent_name,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    enable_notifier(
        repo_root=repo_root,
        paths=paths,
        agent_name=agent_name,
        interval_seconds=parameters.gateway.notifier_interval_seconds,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )

    session_manifest_path = Path(str(agent_show["identity"]["manifest_path"])).resolve()
    session_details = load_session_details(session_manifest_path=session_manifest_path)
    expose_project_mailbox_skills(
        project_workdir=project_workdir,
        brain_manifest_path=session_details["brain_manifest_path"],
        brain_home_path=session_details["brain_home_path"],
        launch_helper_path=session_details["launch_helper_path"],
    )
    state = DemoState(
        created_at_utc=utc_now_iso(),
        repo_root=repo_root,
        output_root=paths.output_root,
        selected_tool=tool,
        provider=tool_parameters.provider,
        selector=tool_parameters.selector,
        run_id=run_id,
        agent_def_dir=agent_def_dir,
        project_fixture=project_fixture,
        project_workdir=project_workdir,
        brain_manifest_path=session_details["brain_manifest_path"],
        brain_home_path=session_details["brain_home_path"],
        launch_helper_path=session_details["launch_helper_path"],
        session_manifest_path=session_manifest_path,
        session_root=Path(session_details["session_root"]).resolve(),
        tracked_agent_id=str(agent_show["tracked_agent_id"]),
        agent_name=str(agent_show["identity"]["agent_name"]),
        agent_id=agent_show["identity"].get("agent_id"),
        tmux_session_name=agent_show["identity"].get("tmux_session_name"),
        terminal_id=agent_show["identity"].get("terminal_id"),
        mailbox_principal_id=tool_parameters.mailbox_principal_id,
        mailbox_address=tool_parameters.mailbox_address,
        gateway_root=(Path(session_details["session_root"]).resolve() / "gateway"),
        gateway_host=str(attach_payload["gateway_host"]),
        gateway_port=int(attach_payload["gateway_port"]),
        notifier_interval_seconds=parameters.gateway.notifier_interval_seconds,
        idle_timeout_seconds=parameters.automatic.idle_timeout_seconds,
        output_timeout_seconds=parameters.automatic.output_timeout_seconds,
        output_file_path=(
            paths.output_root / parameters.automatic.output_file_relative_path
        ).resolve(),
    )
    save_demo_state(paths.state_path, state)
    _wait_for_session_ready(
        repo_root=repo_root,
        paths=paths,
        state=state,
        timeout_seconds=state.idle_timeout_seconds,
    )
    refreshed_show = query_agent_show(
        repo_root=repo_root,
        paths=paths,
        agent_name=state.agent_name,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    refreshed_state = query_agent_state(
        repo_root=repo_root,
        paths=paths,
        agent_name=state.agent_name,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    del refreshed_show, refreshed_state
    return state


def _wait_for_session_ready(
    *,
    repo_root: Path,
    paths: DemoPaths,
    state: DemoState,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Wait until the launched managed session is visibly ready for gateway work."""

    env = build_demo_environment(paths=paths, agent_def_dir=state.agent_def_dir)
    deadline = time.monotonic() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state_payload = query_agent_state(
            repo_root=repo_root,
            paths=paths,
            agent_name=state.agent_name,
            env=env,
            timeout_seconds=30.0,
        )
        gateway_payload = gateway_status(
            repo_root=repo_root,
            paths=paths,
            agent_name=state.agent_name,
            env=env,
            timeout_seconds=30.0,
        )
        notifier_payload = notifier_status(
            repo_root=repo_root,
            paths=paths,
            agent_name=state.agent_name,
            env=env,
            timeout_seconds=30.0,
        )
        last_payload = {
            "state": state_payload,
            "gateway_status": gateway_payload,
            "notifier_status": notifier_payload,
        }
        state_turn = state_payload.get("turn", {})
        if (
            state_payload.get("availability") == "available"
            and state_turn.get("phase") in {"ready", "unknown"}
            and gateway_payload.get("gateway_health") == "healthy"
            and gateway_payload.get("request_admission") == "open"
            and gateway_payload.get("active_execution") == "idle"
            and int(gateway_payload.get("queue_depth", 1)) == 0
            and bool(notifier_payload.get("enabled"))
        ):
            write_json(paths.ready_wait_path, {"status": "ready", **last_payload})
            return last_payload
        time.sleep(1.0)

    write_json(paths.ready_wait_path, {"status": "timeout", **last_payload})
    raise DemoPackError(f"session did not become ready within {timeout_seconds:.1f}s")


def _command_manual_send(args: argparse.Namespace) -> int:
    """Implement `manual-send`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _require_demo_state(paths)
    if not state.active:
        raise DemoPackError("demo is not active; run `start` first")
    subject = args.subject or parameters.delivery.subject
    body_file = (
        None
        if args.body_file is None
        else resolve_repo_relative_path(args.body_file, repo_root=repo_root)
    )
    delivery = deliver_manual_message(
        repo_root=repo_root,
        paths=paths,
        parameters=parameters,
        state=state,
        subject=subject,
        body_content=args.body_content,
        body_file=body_file,
    )
    state = _append_delivery(paths=paths, state=state, delivery=delivery)
    print(
        json.dumps(
            {
                "delivery_index": delivery.delivery_index,
                "message_id": delivery.message_id,
                "delivery_artifact_path": str(delivery.delivery_artifact_path),
            },
            indent=2,
        )
    )
    return 0


def _command_manual_send_many(args: argparse.Namespace) -> int:
    """Implement `manual-send-many`."""

    if args.count <= 0:
        raise DemoPackError("`--count` must be > 0")
    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _require_demo_state(paths)
    if not state.active:
        raise DemoPackError("demo is not active; run `start` first")
    body_file = (
        None
        if args.body_file is None
        else resolve_repo_relative_path(args.body_file, repo_root=repo_root)
    )
    deliveries = []
    for index in range(1, args.count + 1):
        delivery = deliver_manual_message(
            repo_root=repo_root,
            paths=paths,
            parameters=parameters,
            state=state,
            subject=f"{args.subject_prefix} {index}/{args.count}",
            body_content=args.body_content,
            body_file=body_file,
        )
        deliveries.append(delivery)
        state = _append_delivery(paths=paths, state=state, delivery=delivery)
    print(
        json.dumps(
            {
                "delivery_count": len(deliveries),
                "message_ids": [delivery.message_id for delivery in deliveries],
            },
            indent=2,
        )
    )
    return 0


def _append_delivery(*, paths: DemoPaths, state: DemoState, delivery: Any) -> DemoState:
    """Append one delivery to persisted state and record the immediate unread observation."""

    mailbox_snapshot = collect_mailbox_snapshot(state)
    observed = observe_delivery_state(delivery=delivery, mailbox_snapshot=mailbox_snapshot)
    updated = state.model_copy(update={"deliveries": [*state.deliveries, observed]})
    save_demo_state(paths.state_path, updated)
    return updated


def _command_inspect(args: argparse.Namespace) -> int:
    """Implement `inspect`."""

    repo_root = _repo_root()
    _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    inspection = _inspect_demo(repo_root=repo_root, paths=paths)
    print(
        json.dumps(
            {
                "inspect_path": str(paths.inspect_path),
                "delivery_count": len(inspection["deliveries"]),
            },
            indent=2,
        )
    )
    return 0


def _inspect_demo(*, repo_root: Path, paths: DemoPaths) -> dict[str, Any]:
    """Build and persist one raw inspect snapshot."""

    state = _require_demo_state(paths)
    env = build_demo_environment(paths=paths, agent_def_dir=state.agent_def_dir)
    agent_show = None
    agent_state = None
    gateway_payload = None
    notifier_payload = None
    if state.active:
        try:
            agent_show = query_agent_show(
                repo_root=repo_root,
                paths=paths,
                agent_name=state.agent_name,
                env=env,
                timeout_seconds=30.0,
            )
            agent_state = query_agent_state(
                repo_root=repo_root,
                paths=paths,
                agent_name=state.agent_name,
                env=env,
                timeout_seconds=30.0,
            )
            gateway_payload = gateway_status(
                repo_root=repo_root,
                paths=paths,
                agent_name=state.agent_name,
                env=env,
                timeout_seconds=30.0,
            )
            notifier_payload = notifier_status(
                repo_root=repo_root,
                paths=paths,
                agent_name=state.agent_name,
                env=env,
                timeout_seconds=30.0,
            )
        except Exception:
            agent_show = _load_json_if_present(paths.agent_show_path)
            agent_state = _load_json_if_present(paths.agent_state_path)
            gateway_payload = _load_json_if_present(paths.gateway_attach_path)
            notifier_payload = _load_json_if_present(paths.notifier_enable_path)
    else:
        agent_show = _load_json_if_present(paths.agent_show_path)
        agent_state = _load_json_if_present(paths.agent_state_path)
        gateway_payload = _load_json_if_present(paths.gateway_attach_path)
        notifier_payload = _load_json_if_present(paths.notifier_enable_path)

    mailbox_snapshot = collect_mailbox_snapshot(state)
    output_payload = collect_output_file_payload(
        state=state,
        delivery=(state.deliveries[0] if state.deliveries else None),
    )
    inspection = build_inspect_snapshot(
        state=state,
        agent_show=agent_show,
        agent_state=agent_state,
        gateway_status=gateway_payload,
        notifier_status=notifier_payload,
        mailbox_snapshot=mailbox_snapshot,
        output_payload=output_payload,
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
    inspection = _inspect_demo(repo_root=repo_root, paths=paths)
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
    """Idempotently stop the notifier and managed agent while preserving artifacts."""

    if not paths.state_path.is_file():
        return {"already_stopped": True, "detail": "demo state missing"}
    state = load_demo_state(paths.state_path)
    if not state.active:
        return {"already_stopped": True, "detail": "demo already inactive"}

    env = build_demo_environment(paths=paths, agent_def_dir=state.agent_def_dir)
    notifier_payload: dict[str, Any] | None = None
    stop_payload: dict[str, Any] | None = None
    try:
        current_notifier = notifier_status(
            repo_root=repo_root,
            paths=paths,
            agent_name=state.agent_name,
            env=env,
            timeout_seconds=30.0,
        )
        notifier_payload = (
            disable_notifier(
                repo_root=repo_root,
                paths=paths,
                agent_name=state.agent_name,
                env=env,
                timeout_seconds=30.0,
            )
            if current_notifier.get("enabled")
            else current_notifier
        )
    except Exception as exc:
        notifier_payload = {"status": "error", "detail": str(exc)}

    try:
        stop_payload = stop_agent(
            repo_root=repo_root,
            paths=paths,
            agent_name=state.agent_name,
            env=env,
            timeout_seconds=60.0,
        )
    except Exception as exc:
        stop_payload = {"status": "error", "detail": str(exc)}

    updated_state = state.model_copy(update={"active": False, "stopped_at_utc": utc_now_iso()})
    save_demo_state(paths.state_path, updated_state)
    return {
        "already_stopped": False,
        "notifier": notifier_payload,
        "agent": stop_payload,
        "state_path": str(paths.state_path),
    }


def _command_auto(args: argparse.Namespace) -> int:
    """Implement `auto`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=args.tool)
    _run_auto(
        repo_root=repo_root,
        paths=paths,
        parameters=parameters,
        tool=args.tool,
        expected_report=args.expected_report,
        snapshot=args.snapshot,
    )
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


def _run_auto(
    *,
    repo_root: Path,
    paths: DemoPaths,
    parameters: DemoParameters,
    tool: SupportedTool,
    expected_report: str,
    snapshot: bool,
) -> None:
    """Run the canonical end-to-end wake-up flow for one selected tool."""

    started = False
    try:
        state = _start_demo(repo_root=repo_root, paths=paths, parameters=parameters, tool=tool)
        started = True
        env = build_demo_environment(paths=paths, agent_def_dir=state.agent_def_dir)
        mailbox_snapshot = collect_mailbox_snapshot(state)
        current_gateway_status = gateway_status(
            repo_root=repo_root,
            paths=paths,
            agent_name=state.agent_name,
            env=env,
            timeout_seconds=30.0,
        )
        if not gateway_can_accept_work(
            gateway_status=current_gateway_status,
            mailbox_snapshot=mailbox_snapshot,
        ):
            _wait_for_session_ready(
                repo_root=repo_root,
                paths=paths,
                state=state,
                timeout_seconds=state.idle_timeout_seconds,
            )
        delivery = deliver_configured_automatic_message(
            repo_root=repo_root,
            paths=paths,
            parameters=parameters,
            state=state,
        )
        state = _append_delivery(paths=paths, state=state, delivery=delivery)
        latest_delivery = state.deliveries[-1]
        state, latest_delivery, output_payload = wait_for_delivery_completion(
            paths=paths,
            state=state,
            delivery=latest_delivery,
            timeout_seconds=state.output_timeout_seconds,
        )
        del output_payload, latest_delivery
        save_demo_state(paths.state_path, state)
        _verify_demo(
            repo_root=repo_root,
            paths=paths,
            expected_report=expected_report,
            snapshot=snapshot,
        )
    finally:
        if started:
            _stop_demo(repo_root=repo_root, paths=paths)


def _command_matrix(args: argparse.Namespace) -> int:
    """Implement `matrix`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    results: list[dict[str, Any]] = []
    ok = True
    for tool in ("claude", "codex"):
        paths = _resolve_matrix_paths(args, repo_root=repo_root, tool=tool)
        try:
            _run_auto(
                repo_root=repo_root,
                paths=paths,
                parameters=parameters,
                tool=tool,
                expected_report=args.expected_report,
                snapshot=args.snapshot,
            )
            results.append(
                {
                    "tool": tool,
                    "status": "passed",
                    "output_root": str(paths.output_root),
                    "report_path": str(paths.report_path),
                }
            )
        except Exception as exc:
            ok = False
            results.append(
                {
                    "tool": tool,
                    "status": "failed",
                    "detail": str(exc),
                    "output_root": str(paths.output_root),
                }
            )
    print(json.dumps({"results": results}, indent=2))
    return 0 if ok else 1


def _load_json_if_present(path: Path) -> dict[str, Any] | None:
    """Load one JSON object from disk when present."""

    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DemoPackError(f"expected JSON object in `{path}`")
    return dict(payload)

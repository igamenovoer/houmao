"""CLI driver for the supported single-agent headless gateway wake-up demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import shutil
import sys
import time
from typing import Any

from .mailbox import (
    DemoMailboxError,
    build_run_id,
    collect_actor_mail_check,
    collect_output_file_payload,
    collect_project_mailbox_message,
    collect_project_mailbox_messages,
    default_delivery_subject,
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
    DemoParameters,
    DemoPaths,
    DemoState,
    DeliveryState,
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
    attach_to_demo_session,
    build_demo_environment,
    capture_gateway_console,
    disable_notifier,
    enable_notifier,
    enable_notifier_with_retry,
    ensure_specialist,
    gateway_status,
    get_instance,
    get_specialist,
    import_project_auth_from_fixture,
    initialize_project_mailbox,
    initialize_project_overlay,
    load_session_details,
    notifier_status,
    prepare_output_root,
    prepare_persistent_overlay_roots,
    provision_project_workdir,
    query_agent_show,
    query_agent_state,
    register_live_mailbox_binding,
    register_project_mailbox_account,
    launch_instance,
    stop_instance,
    expose_project_mailbox_skills,
)


class DemoPackError(RuntimeError):
    """Raised when the demo pack cannot continue safely."""


def main(argv: list[str] | None = None) -> int:
    """Run the demo-pack CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return _command_start(args)
        if args.command in {"send", "manual-send"}:
            return _command_send(args)
        if args.command == "attach":
            return _command_attach(args)
        if args.command == "watch-gateway":
            return _command_watch_gateway(args)
        if args.command == "notifier":
            return _command_notifier(args)
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

    parser = argparse.ArgumentParser(description="Single-agent gateway wake-up headless demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    _add_common_arguments(start_parser)
    start_parser.add_argument("--tool", choices=("claude", "codex"), required=True)

    attach_parser = subparsers.add_parser("attach")
    _add_common_arguments(attach_parser)

    send_parser = subparsers.add_parser("send", aliases=["manual-send"])
    _add_common_arguments(send_parser)
    send_parser.add_argument("--subject", default=None)
    send_parser.add_argument("--body-content", default=None)
    send_parser.add_argument("--body-file", default=None)

    watch_parser = subparsers.add_parser("watch-gateway")
    _add_common_arguments(watch_parser)
    watch_parser.add_argument("--follow", action="store_true")
    watch_parser.add_argument("--lines", type=int, default=80)
    watch_parser.add_argument("--poll-interval-seconds", type=float, default=1.0)

    notifier_parser = subparsers.add_parser("notifier")
    _add_common_arguments(notifier_parser)
    notifier_subparsers = notifier_parser.add_subparsers(dest="notifier_command", required=True)
    notifier_subparsers.add_parser("status")
    on_parser = notifier_subparsers.add_parser("on")
    on_parser.add_argument("--seconds", type=int, default=None)
    notifier_subparsers.add_parser("off")
    interval_parser = notifier_subparsers.add_parser("set-interval")
    interval_parser.add_argument("--seconds", type=int, required=True)

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
        help=(
            "Pack-local canonical output-root override. Normal usage defaults to "
            "`scripts/demo/single-agent-gateway-wakeup-headless/outputs/`."
        ),
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
    return build_demo_layout(demo_output_dir=default_demo_output_dir(repo_root=repo_root))


def _require_pack_local_output_root(output_root: Path, *, repo_root: Path) -> None:
    """Require one selected output root to remain inside the demo pack directory."""

    pack_root = _pack_root(repo_root=repo_root)
    try:
        output_root.resolve().relative_to(pack_root)
    except ValueError as exc:
        raise DemoPackError(
            f"output root must remain inside `{pack_root}`; got `{output_root.resolve()}`"
        ) from exc


def _require_demo_state(paths: DemoPaths) -> DemoState:
    """Load persisted demo state or fail clearly."""

    if not paths.state_path.is_file():
        raise DemoPackError(f"demo state not found: {paths.state_path}")
    return load_demo_state(paths.state_path)


def _require_active_demo_state(paths: DemoPaths) -> DemoState:
    """Load persisted demo state and require an active session."""

    state = _require_demo_state(paths)
    if not state.active:
        raise DemoPackError("demo is not active; run `start` first")
    return state


def _followup_command(*, paths: DemoPaths, command: str, repo_root: Path) -> str:
    """Return one exact follow-up demo command for the current output root."""

    base = "scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh "
    first, remainder = command.split(" ", 1) if " " in command else (command, "")
    rendered = base + first
    if paths.output_root != default_demo_output_dir(repo_root=repo_root):
        rendered += f" --demo-output-dir {shlex.quote(str(paths.output_root))}"
    if remainder:
        rendered += f" {remainder}"
    return rendered


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
        gateway_foreground=True,
    )
    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "selected_tool": state.selected_tool,
                "specialist_name": state.specialist_name,
                "tracked_agent_id": state.tracked_agent_id,
                "session_manifest_path": str(state.session_manifest_path),
                "gateway_host": state.gateway_host,
                "gateway_port": state.gateway_port,
                "attach_command": (
                    None
                    if state.tmux_session_name is None
                    else _followup_command(paths=paths, command="attach", repo_root=repo_root)
                ),
                "send_command": _followup_command(paths=paths, command="send", repo_root=repo_root),
                "watch_gateway_command": _followup_command(
                    paths=paths, command="watch-gateway", repo_root=repo_root
                ),
                "notifier_status_command": _followup_command(
                    paths=paths, command="notifier status", repo_root=repo_root
                ),
                "gateway_tmux_window_index": state.gateway_tmux_window_index,
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
    gateway_foreground: bool = False,
) -> DemoState:
    """Start one project-easy mailbox-enabled local headless session."""

    existing_state = load_demo_state(paths.state_path) if paths.state_path.is_file() else None
    if existing_state is not None and existing_state.active:
        if existing_state.selected_tool != tool:
            raise DemoPackError(
                f"demo already started for `{existing_state.selected_tool}` at `{paths.output_root}`"
            )
        return existing_state

    allow_reprovision = True
    prepare_output_root(paths=paths, allow_reprovision=allow_reprovision)
    prepare_persistent_overlay_roots(paths=paths)
    project_fixture = resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)
    system_prompt_file = resolve_repo_relative_path(
        parameters.system_prompt_file, repo_root=repo_root
    )
    tool_parameters = parameters.tool_parameters(tool=tool)
    env = build_demo_environment(paths=paths)
    project_workdir = provision_project_workdir(
        project_fixture=project_fixture,
        project_dir=paths.project_dir,
        allow_reprovision=allow_reprovision,
    )
    initialize_project_overlay(
        paths=paths,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    import_project_auth_from_fixture(
        paths=paths,
        env=env,
        tool=tool,
        tool_parameters=tool_parameters,
        repo_root=repo_root,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    run_id = build_run_id()
    launch_suffix = run_id.rsplit("-", 1)[-1]
    specialist_name = tool_parameters.specialist_name_prefix
    instance_name = f"{tool_parameters.instance_name_prefix}-{launch_suffix}"
    session_name = f"{tool_parameters.session_name_prefix}-{launch_suffix}"
    mailbox_principal_id = instance_name
    mailbox_address = f"{instance_name}@agents.localhost"
    output_dir = (project_workdir / parameters.automatic.output_dir_relative_path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file_path = (
        output_dir / f"{parameters.automatic.output_file_prefix}-{launch_suffix}.md"
    ).resolve()
    expected_output_content = f"{parameters.automatic.output_content_prefix} {launch_suffix}"

    specialist_payload = ensure_specialist(
        paths=paths,
        env=env,
        specialist_name=specialist_name,
        tool=tool,
        tool_parameters=tool_parameters,
        system_prompt_file=system_prompt_file,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    launch_payload = specialist_payload.get("launch", {})
    if launch_payload.get("prompt_mode") != "unattended":
        raise DemoPackError(
            f"specialist `{specialist_name}` did not persist unattended launch posture"
        )
    initialize_project_mailbox(
        paths=paths,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    register_project_mailbox_account(
        paths=paths,
        env=env,
        address=mailbox_address,
        principal_id=mailbox_principal_id,
        output_path=paths.project_agent_mailbox_register_path,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    register_project_mailbox_account(
        paths=paths,
        env=env,
        address=parameters.delivery.sender_address,
        principal_id=parameters.delivery.sender_principal_id,
        output_path=paths.project_operator_mailbox_register_path,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    launch_instance(
        paths=paths,
        env=env,
        specialist_name=specialist_name,
        instance_name=instance_name,
        session_name=session_name,
        mail_root=(paths.overlay_dir / "mailbox").resolve(),
        timeout_seconds=parameters.command_timeout_seconds,
    )
    agent_show = query_agent_show(paths=paths, env=env, agent_name=instance_name)
    register_live_mailbox_binding(
        paths=paths,
        env=env,
        agent_name=instance_name,
        mailbox_principal_id=mailbox_principal_id,
        mailbox_address=mailbox_address,
        mailbox_root=(paths.overlay_dir / "mailbox").resolve(),
        timeout_seconds=parameters.command_timeout_seconds,
    )
    attach_payload = attach_gateway(
        paths=paths,
        env=env,
        agent_name=instance_name,
        timeout_seconds=parameters.command_timeout_seconds,
        foreground=gateway_foreground,
    )
    enable_notifier_with_retry(
        paths=paths,
        env=env,
        agent_name=instance_name,
        interval_seconds=parameters.gateway.notifier_interval_seconds,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    gateway_session_payload = gateway_status(
        paths=paths,
        env=env,
        agent_name=instance_name,
        timeout_seconds=30.0,
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
        setup_name=tool_parameters.setup,
        run_id=run_id,
        project_fixture=project_fixture,
        project_workdir=project_workdir,
        overlay_root=paths.overlay_dir,
        agent_def_dir=(paths.overlay_dir / "agents").resolve(),
        specialist_name=specialist_name,
        instance_name=instance_name,
        session_name=session_name,
        auth_bundle_name=tool_parameters.auth_name,
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
        mailbox_principal_id=mailbox_principal_id,
        mailbox_address=mailbox_address,
        operator_principal_id=parameters.delivery.sender_principal_id,
        operator_address=parameters.delivery.sender_address,
        gateway_root=(Path(session_details["session_root"]).resolve() / "gateway"),
        gateway_host=str(attach_payload["gateway_host"]),
        gateway_port=int(attach_payload["gateway_port"]),
        gateway_tmux_session_name=(
            None
            if not str(gateway_session_payload.get("tmux_session_name") or "").strip()
            else str(gateway_session_payload["tmux_session_name"]).strip()
        ),
        gateway_tmux_window_index=(
            None
            if gateway_session_payload.get("gateway_tmux_window_index") is None
            else str(gateway_session_payload["gateway_tmux_window_index"])
        ),
        notifier_interval_seconds=parameters.gateway.notifier_interval_seconds,
        ready_timeout_seconds=parameters.automatic.ready_timeout_seconds,
        output_timeout_seconds=parameters.automatic.output_timeout_seconds,
        output_file_path=output_file_path,
        output_file_expected_content=expected_output_content,
    )
    save_demo_state(paths.state_path, state)
    _wait_for_session_ready(paths=paths, state=state, timeout_seconds=state.ready_timeout_seconds)
    get_instance(
        paths=paths,
        env=env,
        instance_name=state.instance_name,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    query_agent_show(paths=paths, env=env, agent_name=state.agent_name)
    query_agent_state(
        paths=paths,
        env=env,
        agent_name=state.agent_name,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    return state


def _wait_for_session_ready(
    *,
    paths: DemoPaths,
    state: DemoState,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Wait until the launched managed session is visibly ready for gateway work."""

    env = build_demo_environment(paths=paths)
    deadline = time.monotonic() + timeout_seconds
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        state_payload = query_agent_state(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
            timeout_seconds=30.0,
        )
        gateway_payload = gateway_status(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
            timeout_seconds=30.0,
        )
        notifier_payload = notifier_status(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
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


def _command_attach(args: argparse.Namespace) -> int:
    """Implement `attach`."""

    repo_root = _repo_root()
    _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _require_active_demo_state(paths)
    if state.tmux_session_name is None:
        raise DemoPackError("active demo state does not include a tmux session name")
    attach_to_demo_session(session_name=state.tmux_session_name)
    return 0


def _command_send(args: argparse.Namespace) -> int:
    """Implement `send`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _require_active_demo_state(paths)
    subject = args.subject or default_delivery_subject(parameters=parameters, state=state)
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


def _command_watch_gateway(args: argparse.Namespace) -> int:
    """Implement `watch-gateway`."""

    if args.lines <= 0:
        raise DemoPackError("`--lines` must be > 0")
    if args.poll_interval_seconds <= 0:
        raise DemoPackError("`--poll-interval-seconds` must be > 0")

    repo_root = _repo_root()
    _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _require_active_demo_state(paths)
    env = build_demo_environment(paths=paths)

    try:
        last_rendered: str | None = None
        while True:
            capture = capture_gateway_console(
                paths=paths,
                env=env,
                agent_name=state.agent_name,
                fallback_session_name=state.gateway_tmux_session_name or state.tmux_session_name,
                fallback_window_index=state.gateway_tmux_window_index,
                timeout_seconds=30.0,
                lines=args.lines,
            )
            rendered = capture["text"]
            if args.follow:
                if rendered != last_rendered:
                    sys.stdout.write("\033[2J\033[H")
                    sys.stdout.write(rendered)
                    sys.stdout.flush()
                    last_rendered = rendered
                time.sleep(args.poll_interval_seconds)
                continue
            sys.stdout.write(rendered)
            sys.stdout.flush()
            return 0
    except KeyboardInterrupt:
        return 130


def _command_notifier(args: argparse.Namespace) -> int:
    """Implement `notifier ...`."""

    repo_root = _repo_root()
    _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root, tool=None)
    state = _require_active_demo_state(paths)
    env = build_demo_environment(paths=paths)

    if args.notifier_command == "status":
        payload = notifier_status(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
            timeout_seconds=30.0,
        )
        print(json.dumps(payload, indent=2))
        return 0

    if args.notifier_command == "off":
        payload = disable_notifier(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
            timeout_seconds=30.0,
        )
        print(json.dumps(payload, indent=2))
        return 0

    interval_seconds = args.seconds if args.notifier_command == "set-interval" else args.seconds
    if interval_seconds is None:
        interval_seconds = state.notifier_interval_seconds
    if interval_seconds <= 0:
        raise DemoPackError("notifier interval must be > 0 seconds")
    payload = enable_notifier(
        paths=paths,
        env=env,
        agent_name=state.agent_name,
        interval_seconds=interval_seconds,
        timeout_seconds=30.0,
    )
    updated_state = state.model_copy(update={"notifier_interval_seconds": interval_seconds})
    save_demo_state(paths.state_path, updated_state)
    print(json.dumps(payload, indent=2))
    return 0


def _append_delivery(*, paths: DemoPaths, state: DemoState, delivery: DeliveryState) -> DemoState:
    """Append one delivery to persisted state and record the immediate unread observation."""

    updated_delivery = delivery
    try:
        actor_mail_snapshot = collect_actor_mail_check(paths=paths, state=state, unread_only=False)
        updated_delivery = observe_delivery_state(
            delivery=delivery,
            actor_mail_snapshot=actor_mail_snapshot,
        )
    except Exception:
        updated_delivery = delivery
    updated = state.model_copy(update={"deliveries": [*state.deliveries, updated_delivery]})
    save_demo_state(paths.state_path, updated)
    return updated


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
                "delivery_count": len(inspection["deliveries"]),
            },
            indent=2,
        )
    )
    return 0


def _inspect_demo(*, paths: DemoPaths) -> dict[str, Any]:
    """Build and persist one raw inspect snapshot."""

    state = _require_demo_state(paths)
    env = build_demo_environment(paths=paths)
    specialist_payload = _load_json_if_present(paths.specialist_get_path)
    instance_payload = _load_json_if_present(paths.instance_get_path)
    agent_show = None
    agent_state = None
    gateway_payload = None
    notifier_payload = None
    if state.active:
        try:
            specialist_payload = get_specialist(
                paths=paths,
                env=env,
                specialist_name=state.specialist_name,
                timeout_seconds=30.0,
            )
        except Exception:
            pass
        try:
            instance_payload = get_instance(
                paths=paths,
                env=env,
                instance_name=state.instance_name,
                timeout_seconds=30.0,
            )
        except Exception:
            pass
        try:
            agent_show = query_agent_show(paths=paths, env=env, agent_name=state.agent_name)
            agent_state = query_agent_state(
                paths=paths,
                env=env,
                agent_name=state.agent_name,
                timeout_seconds=30.0,
            )
            gateway_payload = gateway_status(
                paths=paths,
                env=env,
                agent_name=state.agent_name,
                timeout_seconds=30.0,
            )
            notifier_payload = notifier_status(
                paths=paths,
                env=env,
                agent_name=state.agent_name,
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

    actor_mail_check = collect_actor_mail_check(paths=paths, state=state, unread_only=False)
    actor_mail_unread_check = collect_actor_mail_check(paths=paths, state=state, unread_only=True)
    try:
        project_mailbox_list = collect_project_mailbox_messages(paths=paths, state=state)
    except Exception:
        project_mailbox_list = None
    project_mailbox_message = None
    if state.deliveries:
        try:
            project_mailbox_message = collect_project_mailbox_message(
                paths=paths,
                state=state,
                message_id=state.deliveries[0].message_id,
            )
        except Exception:
            project_mailbox_message = None

    output_payload = collect_output_file_payload(
        state=state,
        delivery=(state.deliveries[0] if state.deliveries else None),
    )
    inspection = build_inspect_snapshot(
        state=state,
        specialist=specialist_payload,
        instance=instance_payload,
        agent_show=agent_show,
        agent_state=agent_state,
        gateway_status=gateway_payload,
        notifier_status=notifier_payload,
        actor_mail_check=actor_mail_check,
        actor_mail_unread_check=actor_mail_unread_check,
        project_mailbox_list=project_mailbox_list,
        project_mailbox_message=project_mailbox_message,
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
    payload = _stop_demo(paths=paths)
    print(json.dumps(payload, indent=2))
    return 0


def _stop_demo(*, paths: DemoPaths) -> dict[str, Any]:
    """Idempotently stop the notifier and managed agent while preserving artifacts."""

    if not paths.state_path.is_file():
        return {"already_stopped": True, "detail": "demo state missing"}
    state = load_demo_state(paths.state_path)
    if not state.active:
        return {"already_stopped": True, "detail": "demo already inactive"}

    env = build_demo_environment(paths=paths)
    notifier_payload: dict[str, Any] | None = None
    stop_payload: dict[str, Any] | None = None
    try:
        current_notifier = notifier_status(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
            timeout_seconds=30.0,
        )
        notifier_payload = (
            disable_notifier(
                paths=paths,
                env=env,
                agent_name=state.agent_name,
                timeout_seconds=30.0,
            )
            if current_notifier.get("enabled")
            else current_notifier
        )
    except Exception as exc:
        notifier_payload = {"status": "error", "detail": str(exc)}

    try:
        stop_payload = stop_instance(
            paths=paths,
            env=env,
            instance_name=state.instance_name,
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
        if state.delivery_count != 0:
            raise DemoPackError(
                "automatic workflow requires a fresh run with zero existing deliveries"
            )
        env = build_demo_environment(paths=paths)
        actor_mail_snapshot = collect_actor_mail_check(paths=paths, state=state, unread_only=False)
        current_gateway_status = gateway_status(
            paths=paths,
            env=env,
            agent_name=state.agent_name,
            timeout_seconds=30.0,
        )
        if not gateway_can_accept_work(
            gateway_status=current_gateway_status,
            actor_mail_snapshot=actor_mail_snapshot,
        ):
            _wait_for_session_ready(
                paths=paths, state=state, timeout_seconds=state.ready_timeout_seconds
            )
        delivery = deliver_configured_automatic_message(
            repo_root=repo_root,
            paths=paths,
            parameters=parameters,
            state=state,
        )
        state = _append_delivery(paths=paths, state=state, delivery=delivery)
        latest_delivery = state.deliveries[-1]
        state, latest_delivery, actor_mail_snapshot, output_payload = wait_for_delivery_completion(
            paths=paths,
            state=state,
            delivery=latest_delivery,
            timeout_seconds=state.output_timeout_seconds,
        )
        del latest_delivery, actor_mail_snapshot, output_payload
        save_demo_state(paths.state_path, state)
        _verify_demo(
            repo_root=repo_root,
            paths=paths,
            expected_report=expected_report,
            snapshot=snapshot,
        )
    finally:
        if started:
            _stop_demo(paths=paths)


def _command_matrix(args: argparse.Namespace) -> int:
    """Implement `matrix`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    results: list[dict[str, Any]] = []
    ok = True
    for tool in ("claude", "codex"):
        paths = _resolve_paths(args, repo_root=repo_root, tool=tool)
        try:
            _run_auto(
                repo_root=repo_root,
                paths=paths,
                parameters=parameters,
                tool=tool,
                expected_report=args.expected_report,
                snapshot=args.snapshot,
            )
            matrix_report_path = paths.control_dir / f"matrix-report-{tool}.json"
            matrix_sanitized_report_path = (
                paths.control_dir / f"matrix-report-{tool}.sanitized.json"
            )
            shutil.copy2(paths.report_path, matrix_report_path)
            shutil.copy2(paths.sanitized_report_path, matrix_sanitized_report_path)
            results.append(
                {
                    "tool": tool,
                    "status": "passed",
                    "output_root": str(paths.output_root),
                    "report_path": str(matrix_report_path),
                    "sanitized_report_path": str(matrix_sanitized_report_path),
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

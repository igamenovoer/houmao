"""CLI driver for the manual Kimi writer-team demo pack."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import sys
from typing import Any, Callable

from .models import (
    DEFAULT_PARAMETERS_RELATIVE,
    AgentRuntimeState,
    DemoParameters,
    DemoPaths,
    DemoState,
    TeamMemberParameters,
    build_demo_layout,
    default_demo_output_dir,
    resolve_repo_relative_path,
    utc_now_iso,
)
from .runtime import (
    DemoRuntimeError,
    agent_state,
    attach_to_tmux_session,
    build_demo_environment,
    build_kimi_credential_args,
    build_kimi_credential_args_from_bundle,
    create_profile,
    create_specialist,
    disable_notifier,
    enable_notifier,
    ensure_kimi_command_available,
    gateway_status,
    gateway_tui_state,
    initialize_project_mailbox,
    initialize_project_overlay,
    launch_agent,
    mailbox_status,
    notifier_status,
    prepare_output_root,
    project_agent_get,
    prompt_agent,
    provision_writer_team_project,
    register_project_mailbox_account,
    send_agent_mail,
    stop_agent,
    upsert_kimi_credential,
    wait_for_team_ready,
)
from .store import load_demo_parameters, load_demo_state, save_demo_state, write_json


class DemoPackError(RuntimeError):
    """Raised when the demo pack cannot continue safely."""


def main(argv: list[str] | None = None) -> int:
    """Run the demo-pack CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return _command_start(args)
        if args.command == "attach":
            return _command_attach(args)
        if args.command == "prompt-start":
            return _command_prompt_start(args)
        if args.command == "send-mail":
            return _command_send_mail(args)
        if args.command == "notifier":
            return _command_notifier(args)
        if args.command == "status":
            return _command_status(args)
        if args.command == "inspect":
            return _command_inspect(args)
        if args.command == "stop":
            return _command_stop(args)
        raise DemoPackError(f"unsupported command: {args.command}")
    except (DemoPackError, DemoRuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """Build the demo-pack CLI parser."""

    parser = argparse.ArgumentParser(description="Manual three-agent Kimi writer-team demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    _add_common_arguments(start_parser)
    start_parser.add_argument("--credential-name", default=None)
    start_parser.add_argument("--kimi-code-home", default=None)
    start_parser.add_argument("--kimi-auth-bundle", default=None)
    start_parser.add_argument("--kimi-config-toml", default=None)
    start_parser.add_argument("--kimi-credential-json", default=None)
    start_parser.add_argument("--api-key", default=None)
    start_parser.add_argument("--model-name", default=None)
    start_parser.add_argument("--base-url", default=None)
    start_parser.add_argument("--provider-type", default=None)
    start_parser.add_argument("--code-base-url", default=None)
    start_parser.add_argument("--code-oauth-host", default=None)
    start_parser.add_argument("--oauth-host", default=None)
    start_parser.add_argument("--disable-telemetry", action="store_true")
    start_parser.add_argument("--reset", action="store_true")
    start_parser.add_argument("--skip-ready-wait", action="store_true")
    start_parser.add_argument("--ready-timeout-seconds", type=float, default=None)
    start_parser.add_argument("--notifier-interval-seconds", type=int, default=None)

    attach_parser = subparsers.add_parser("attach")
    _add_common_arguments(attach_parser)
    attach_parser.add_argument("--agent", default="alex-story")

    prompt_parser = subparsers.add_parser("prompt-start")
    _add_common_arguments(prompt_parser)
    prompt_parser.add_argument("--chapters", type=int, default=None)
    prompt_parser.add_argument("--charter-file", default=None)

    send_parser = subparsers.add_parser("send-mail")
    _add_common_arguments(send_parser)
    send_parser.add_argument("--from-agent", required=True)
    send_parser.add_argument("--to-agent", default=None)
    send_parser.add_argument("--to-address", default=None)
    send_parser.add_argument("--subject", required=True)
    send_parser.add_argument("--body-content", default=None)
    send_parser.add_argument("--body-file", default=None)

    notifier_parser = subparsers.add_parser("notifier")
    _add_common_arguments(notifier_parser)
    notifier_parser.add_argument("--agent", default="all")
    notifier_subparsers = notifier_parser.add_subparsers(
        dest="notifier_command",
        required=True,
    )
    notifier_subparsers.add_parser("status")
    on_parser = notifier_subparsers.add_parser("on")
    on_parser.add_argument("--seconds", type=int, default=None)
    notifier_subparsers.add_parser("off")

    status_parser = subparsers.add_parser("status")
    _add_common_arguments(status_parser)

    inspect_parser = subparsers.add_parser("inspect")
    _add_common_arguments(inspect_parser)

    stop_parser = subparsers.add_parser("stop")
    _add_common_arguments(stop_parser)

    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments shared across commands."""

    parser.add_argument(
        "--demo-output-dir",
        default=None,
        help=(
            "Pack-local output-root override. Normal usage defaults to "
            "`scripts/demo/kimi-writer-team-manual/outputs/`."
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
    """Return the repository-relative demo pack root."""

    return (repo_root / "scripts" / "demo" / "kimi-writer-team-manual").resolve()


def _load_parameters(args: argparse.Namespace, *, repo_root: Path) -> DemoParameters:
    """Load tracked demo parameters for one invocation."""

    return load_demo_parameters(resolve_repo_relative_path(args.parameters, repo_root=repo_root))


def _resolve_paths(args: argparse.Namespace, *, repo_root: Path) -> DemoPaths:
    """Resolve the selected demo output layout."""

    if args.demo_output_dir is not None:
        candidate = resolve_repo_relative_path(args.demo_output_dir, repo_root=repo_root)
        _require_pack_local_output_root(candidate, repo_root=repo_root)
        return build_demo_layout(demo_output_dir=candidate)
    return build_demo_layout(demo_output_dir=default_demo_output_dir(repo_root=repo_root))


def _require_pack_local_output_root(output_root: Path, *, repo_root: Path) -> None:
    """Require one selected output root to remain inside the demo pack."""

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
    """Load persisted demo state and require an active run."""

    state = _require_demo_state(paths)
    if not state.active:
        raise DemoPackError("demo is not active; run `start` first")
    return state


def _followup_command(*, paths: DemoPaths, command: str, repo_root: Path) -> str:
    """Return one exact follow-up command for the current output root."""

    base = "scripts/demo/kimi-writer-team-manual/run_demo.sh "
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
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _start_demo(repo_root=repo_root, paths=paths, parameters=parameters, args=args)
    print(
        json.dumps(
            {
                "output_root": str(paths.output_root),
                "project_workdir": str(state.project_workdir),
                "credential_name": state.credential_name,
                "run_id": state.run_id,
                "agents": [
                    {
                        "agent_name": agent.agent_name,
                        "role": agent.role,
                        "session_name": agent.session_name,
                        "attach_command": _followup_command(
                            paths=paths,
                            command=f"attach --agent {agent.agent_name}",
                            repo_root=repo_root,
                        ),
                    }
                    for agent in state.team
                ],
                "prompt_start_command": _followup_command(
                    paths=paths,
                    command="prompt-start --chapters 1",
                    repo_root=repo_root,
                ),
                "status_command": _followup_command(
                    paths=paths,
                    command="status",
                    repo_root=repo_root,
                ),
                "stop_command": _followup_command(paths=paths, command="stop", repo_root=repo_root),
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
    args: argparse.Namespace,
) -> DemoState:
    """Start one manual Kimi writer-team run."""

    existing_state = load_demo_state(paths.state_path) if paths.state_path.is_file() else None
    if existing_state is not None and existing_state.active and not args.reset:
        return existing_state

    ensure_kimi_command_available()
    prepare_output_root(paths=paths, reset=True)
    source_dir = resolve_repo_relative_path(parameters.story_source_dir, repo_root=repo_root)
    project_workdir = provision_writer_team_project(
        source_dir=source_dir,
        project_dir=paths.project_dir,
        reset=True,
    )
    env = build_demo_environment(paths=paths)
    initialize_project_overlay(
        paths=paths,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    credential_name = args.credential_name or parameters.credential_name
    credential_args, credential_source = _resolve_kimi_credential_args(args, repo_root=repo_root)
    upsert_kimi_credential(
        paths=paths,
        env=env,
        credential_name=credential_name,
        credential_args=credential_args,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    _prepare_project_definitions(
        paths=paths,
        env=env,
        parameters=parameters,
        credential_name=credential_name,
    )

    run_id = _build_run_id(parameters=parameters)
    interval_seconds = args.notifier_interval_seconds or parameters.notifier_interval_seconds
    team_state: list[AgentRuntimeState] = []
    for member in parameters.team:
        session_name = f"{member.session_name_prefix}-{run_id.rsplit('-', 1)[-1]}"
        launch_payload = launch_agent(
            paths=paths,
            env=env,
            member=member,
            session_name=session_name,
            timeout_seconds=parameters.command_timeout_seconds,
        )
        enable_notifier(
            paths=paths,
            env=env,
            agent_name=member.agent_name,
            interval_seconds=interval_seconds,
            appendix_text=parameters.notifier_appendix_text,
            timeout_seconds=parameters.command_timeout_seconds,
        )
        team_state.append(_build_agent_state(member, session_name, launch_payload))

    state = DemoState(
        created_at_utc=utc_now_iso(),
        repo_root=repo_root,
        output_root=paths.output_root,
        project_workdir=project_workdir,
        overlay_root=paths.overlay_dir,
        credential_name=credential_name,
        credential_source=credential_source,
        run_id=run_id,
        notifier_interval_seconds=interval_seconds,
        operator_principal_id=parameters.operator.principal_id,
        operator_address=parameters.operator.address,
        team=team_state,
    )
    save_demo_state(paths.state_path, state)
    if not args.skip_ready_wait:
        wait_for_team_ready(
            paths=paths,
            env=env,
            agent_names=[agent.agent_name for agent in state.team],
            timeout_seconds=args.ready_timeout_seconds or parameters.ready_timeout_seconds,
        )
    return state


def _prepare_project_definitions(
    *,
    paths: DemoPaths,
    env: dict[str, str],
    parameters: DemoParameters,
    credential_name: str,
) -> None:
    """Create mailbox, specialists, and profiles for the team."""

    initialize_project_mailbox(
        paths=paths,
        env=env,
        timeout_seconds=parameters.command_timeout_seconds,
    )
    register_project_mailbox_account(
        paths=paths,
        env=env,
        address=parameters.operator.address,
        principal_id=parameters.operator.principal_id,
        stem="mailbox-register-operator",
        timeout_seconds=parameters.command_timeout_seconds,
    )
    for member in parameters.team:
        register_project_mailbox_account(
            paths=paths,
            env=env,
            address=member.mailbox_address,
            principal_id=member.mailbox_principal_id,
            stem=f"mailbox-register-{member.agent_name}",
            timeout_seconds=parameters.command_timeout_seconds,
        )
        create_specialist(
            paths=paths,
            env=env,
            member=member,
            credential_name=credential_name,
            setup_name=parameters.setup_name,
            timeout_seconds=parameters.command_timeout_seconds,
        )
        create_profile(
            paths=paths,
            env=env,
            member=member,
            credential_name=credential_name,
            notifier_appendix_text=parameters.notifier_appendix_text,
            timeout_seconds=parameters.command_timeout_seconds,
        )


def _build_agent_state(
    member: TeamMemberParameters,
    session_name: str,
    launch_payload: dict[str, Any],
) -> AgentRuntimeState:
    """Build persisted state for one launched agent."""

    return AgentRuntimeState(
        role=member.role,
        specialist_name=member.specialist_name,
        profile_name=member.profile_name,
        agent_name=member.agent_name,
        session_name=session_name,
        mailbox_principal_id=member.mailbox_principal_id,
        mailbox_address=member.mailbox_address,
        launch_payload=launch_payload,
        tmux_session_name=str(
            launch_payload.get("tmux_session_name")
            or launch_payload.get("session_name")
            or session_name
        ),
        manifest_path=_optional_path_from_payload(launch_payload, "manifest_path"),
        gateway_host=_optional_str_from_payload(launch_payload, "gateway_host"),
        gateway_port=_optional_int_from_payload(launch_payload, "gateway_port"),
    )


def _resolve_kimi_credential_args(
    args: argparse.Namespace,
    *,
    repo_root: Path,
) -> tuple[list[str], str]:
    """Resolve Kimi credential arguments from CLI inputs and environment defaults."""

    explicit_code_home = args.kimi_code_home
    if explicit_code_home is None and not _has_explicit_credential_input(args):
        explicit_code_home = os.environ.get("KIMI_CODE_HOME")
    if args.kimi_auth_bundle is not None:
        bundle_dir = resolve_repo_relative_path(args.kimi_auth_bundle, repo_root=repo_root)
        return build_kimi_credential_args_from_bundle(bundle_dir=bundle_dir)

    code_home = None if explicit_code_home is None else Path(explicit_code_home).expanduser()
    config_toml = (
        None
        if args.kimi_config_toml is None
        else resolve_repo_relative_path(args.kimi_config_toml, repo_root=repo_root)
    )
    credential_json = (
        None
        if args.kimi_credential_json is None
        else resolve_repo_relative_path(args.kimi_credential_json, repo_root=repo_root)
    )
    credential_args = build_kimi_credential_args(
        api_key=args.api_key,
        model_name=args.model_name,
        base_url=args.base_url,
        provider_type=args.provider_type,
        code_base_url=args.code_base_url,
        code_oauth_host=args.code_oauth_host,
        oauth_host=args.oauth_host,
        disable_telemetry=bool(args.disable_telemetry),
        code_home=code_home,
        config_toml=config_toml,
        credential_json=credential_json,
    )
    if code_home is not None:
        return credential_args, f"code-home:{code_home.resolve()}"
    if args.api_key:
        return credential_args, "env-model-api-key"
    return credential_args, "direct-files"


def _has_explicit_credential_input(args: argparse.Namespace) -> bool:
    """Return whether CLI credential input was supplied."""

    return any(
        value
        for value in (
            args.kimi_auth_bundle,
            args.kimi_config_toml,
            args.kimi_credential_json,
            args.api_key,
            args.model_name,
            args.base_url,
            args.provider_type,
            args.code_base_url,
            args.code_oauth_host,
            args.oauth_host,
        )
    ) or bool(args.disable_telemetry)


def _build_run_id(*, parameters: DemoParameters) -> str:
    """Return one demo run id."""

    return f"{parameters.run_id_prefix}-{utc_now_iso().replace(':', '').replace('-', '')}"


def _command_attach(args: argparse.Namespace) -> int:
    """Implement `attach`."""

    repo_root = _repo_root()
    _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_active_demo_state(paths)
    agent = state.agent(args.agent)
    attach_to_tmux_session(session_name=agent.tmux_session_name or agent.session_name)
    return 0


def _command_prompt_start(args: argparse.Namespace) -> int:
    """Implement `prompt-start`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_active_demo_state(paths)
    chapters = args.chapters or parameters.default_chapter_count
    if chapters <= 0:
        raise DemoPackError("`--chapters` must be > 0")
    prompt_text = _load_or_render_start_charter(
        args=args,
        repo_root=repo_root,
        parameters=parameters,
        state=state,
        chapters=chapters,
    )
    delivery_path = paths.deliveries_dir / f"start-charter-{chapters}.md"
    delivery_path.write_text(prompt_text, encoding="utf-8")
    env = build_demo_environment(paths=paths)
    payload = prompt_agent(
        paths=paths,
        env=env,
        agent_name=parameters.story_member.agent_name,
        prompt_text=prompt_text,
        stem="prompt-start",
        timeout_seconds=parameters.command_timeout_seconds,
    )
    print(
        json.dumps(
            {
                "agent_name": parameters.story_member.agent_name,
                "chapters": chapters,
                "charter_path": str(delivery_path),
                "prompt_result": payload,
            },
            indent=2,
        )
    )
    return 0


def _load_or_render_start_charter(
    *,
    args: argparse.Namespace,
    repo_root: Path,
    parameters: DemoParameters,
    state: DemoState,
    chapters: int,
) -> str:
    """Load an explicit start charter or render the tracked template."""

    if args.charter_file is not None:
        return resolve_repo_relative_path(args.charter_file, repo_root=repo_root).read_text(
            encoding="utf-8"
        )
    template_path = resolve_repo_relative_path(
        parameters.start_charter_template, repo_root=repo_root
    )
    return render_start_charter(
        template_path.read_text(encoding="utf-8"),
        run_id=state.run_id,
        chapter_count=chapters,
    )


def render_start_charter(template: str, *, run_id: str, chapter_count: int) -> str:
    """Render the tracked start-charter template."""

    return (
        template.replace("__RUN_ID__", run_id)
        .replace("__CHAPTER_COUNT__", str(chapter_count))
        .replace("__CHAPTER_COUNT_WORD__", str(chapter_count))
    )


def _command_send_mail(args: argparse.Namespace) -> int:
    """Implement `send-mail`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    _require_active_demo_state(paths)
    to_address = _resolve_to_address(args=args, parameters=parameters)
    body_text = _resolve_body_text(args=args, repo_root=repo_root)
    env = build_demo_environment(paths=paths)
    payload = send_agent_mail(
        paths=paths,
        env=env,
        from_agent_name=args.from_agent,
        to_address=to_address,
        subject=args.subject,
        body_text=body_text,
        stem=f"send-mail-{args.from_agent}",
        timeout_seconds=parameters.command_timeout_seconds,
    )
    print(json.dumps(payload, indent=2))
    return 0


def _resolve_to_address(*, args: argparse.Namespace, parameters: DemoParameters) -> str:
    """Resolve the recipient address for `send-mail`."""

    if args.to_address is not None and args.to_agent is not None:
        raise DemoPackError("pass only one of `--to-agent` or `--to-address`")
    if args.to_address is not None:
        return str(args.to_address)
    if args.to_agent is not None:
        return parameters.member_by_agent_name(args.to_agent).mailbox_address
    raise DemoPackError("pass `--to-agent` or `--to-address`")


def _resolve_body_text(*, args: argparse.Namespace, repo_root: Path) -> str:
    """Resolve the body text for `send-mail`."""

    if args.body_content is not None and args.body_file is not None:
        raise DemoPackError("pass only one of `--body-content` or `--body-file`")
    if args.body_content is not None:
        return str(args.body_content)
    if args.body_file is not None:
        return resolve_repo_relative_path(args.body_file, repo_root=repo_root).read_text(
            encoding="utf-8"
        )
    raise DemoPackError("pass `--body-content` or `--body-file`")


def _command_notifier(args: argparse.Namespace) -> int:
    """Implement `notifier ...`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_active_demo_state(paths)
    env = build_demo_environment(paths=paths)
    agent_names = _selected_agent_names(state=state, selected=args.agent)

    results: dict[str, Any] = {}
    for agent_name in agent_names:
        if args.notifier_command == "status":
            results[agent_name] = notifier_status(
                paths=paths,
                env=env,
                agent_name=agent_name,
                timeout_seconds=parameters.command_timeout_seconds,
            )
        elif args.notifier_command == "off":
            results[agent_name] = disable_notifier(
                paths=paths,
                env=env,
                agent_name=agent_name,
                timeout_seconds=parameters.command_timeout_seconds,
            )
        else:
            interval_seconds = args.seconds or state.notifier_interval_seconds
            results[agent_name] = enable_notifier(
                paths=paths,
                env=env,
                agent_name=agent_name,
                interval_seconds=interval_seconds,
                appendix_text=parameters.notifier_appendix_text,
                timeout_seconds=parameters.command_timeout_seconds,
            )
    print(json.dumps(results, indent=2))
    return 0


def _selected_agent_names(*, state: DemoState, selected: str) -> list[str]:
    """Return the selected agent names for a command."""

    if selected == "all":
        return [agent.agent_name for agent in state.team]
    state.agent(selected)
    return [selected]


def _command_status(args: argparse.Namespace) -> int:
    """Implement `status`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    payload = _collect_status(paths=paths, parameters=parameters, state=state)
    print(json.dumps(payload, indent=2))
    return 0


def _command_inspect(args: argparse.Namespace) -> int:
    """Implement `inspect`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    payload = _collect_status(paths=paths, parameters=parameters, state=state)
    payload["artifacts"] = _collect_story_artifacts(state.project_workdir)
    write_json(paths.control_json_path("inspect"), payload)
    print(json.dumps({"inspect_path": str(paths.control_json_path("inspect"))}, indent=2))
    return 0


AgentCollector = Callable[
    [DemoPaths, dict[str, str], str, float],
    dict[str, Any],
]


def _collect_status(
    *,
    paths: DemoPaths,
    parameters: DemoParameters,
    state: DemoState,
) -> dict[str, Any]:
    """Collect a best-effort live status snapshot."""

    env = build_demo_environment(paths=paths)
    agents: dict[str, Any] = {}
    for agent in state.team:
        agents[agent.agent_name] = _collect_agent_status(
            paths=paths,
            env=env,
            agent_name=agent.agent_name,
            timeout_seconds=parameters.command_timeout_seconds,
        )
    return {
        "active": state.active,
        "run_id": state.run_id,
        "project_workdir": str(state.project_workdir),
        "overlay_root": str(state.overlay_root),
        "credential_name": state.credential_name,
        "agents": agents,
    }


def _collect_agent_status(
    *,
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Collect best-effort status for one agent."""

    collectors: dict[str, AgentCollector] = {
        "project_agent": _project_agent_get_adapter,
        "agent_state": _agent_state_adapter,
        "gateway_status": _gateway_status_adapter,
        "gateway_tui_state": _gateway_tui_state_adapter,
        "mailbox_status": _mailbox_status_adapter,
        "notifier_status": _notifier_status_adapter,
    }
    payload: dict[str, Any] = {}
    for key, collector in collectors.items():
        try:
            payload[key] = collector(paths, env, agent_name, timeout_seconds)
        except Exception as exc:
            payload[key] = {"error": str(exc)}
    return payload


def _project_agent_get_adapter(
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Adapt project-agent get to the generic collector signature."""

    return project_agent_get(
        paths=paths,
        env=env,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
    )


def _agent_state_adapter(
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Adapt agent state to the generic collector signature."""

    return agent_state(paths=paths, env=env, agent_name=agent_name, timeout_seconds=timeout_seconds)


def _gateway_status_adapter(
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Adapt gateway status to the generic collector signature."""

    return gateway_status(
        paths=paths,
        env=env,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
    )


def _gateway_tui_state_adapter(
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Adapt gateway TUI state to the generic collector signature."""

    return gateway_tui_state(
        paths=paths,
        env=env,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
    )


def _mailbox_status_adapter(
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Adapt mailbox status to the generic collector signature."""

    return mailbox_status(
        paths=paths,
        env=env,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
    )


def _notifier_status_adapter(
    paths: DemoPaths,
    env: dict[str, str],
    agent_name: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Adapt notifier status to the generic collector signature."""

    return notifier_status(
        paths=paths,
        env=env,
        agent_name=agent_name,
        timeout_seconds=timeout_seconds,
    )


def _collect_story_artifacts(project_workdir: Path) -> dict[str, list[str]]:
    """Collect story artifact paths written by the team."""

    story_root = project_workdir / "story"
    artifact_dirs = {
        "chapters": story_root / "chapters",
        "characters": story_root / "characters",
        "review": story_root / "review",
    }
    artifacts: dict[str, list[str]] = {}
    for key, directory in artifact_dirs.items():
        if not directory.is_dir():
            artifacts[key] = []
            continue
        artifacts[key] = [str(path) for path in sorted(directory.glob("*.md"))]
    return artifacts


def _command_stop(args: argparse.Namespace) -> int:
    """Implement `stop`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    if not paths.state_path.is_file():
        print(json.dumps({"already_stopped": True, "detail": "demo state missing"}, indent=2))
        return 0
    state = load_demo_state(paths.state_path)
    if not state.active:
        print(json.dumps({"already_stopped": True, "detail": "demo already inactive"}, indent=2))
        return 0

    env = build_demo_environment(paths=paths)
    results: dict[str, Any] = {}
    for agent in state.team:
        agent_result: dict[str, Any] = {}
        try:
            agent_result["notifier"] = disable_notifier(
                paths=paths,
                env=env,
                agent_name=agent.agent_name,
                timeout_seconds=parameters.command_timeout_seconds,
            )
        except Exception as exc:
            agent_result["notifier"] = {"error": str(exc)}
        try:
            agent_result["stop"] = stop_agent(
                paths=paths,
                env=env,
                agent_name=agent.agent_name,
                timeout_seconds=parameters.command_timeout_seconds,
            )
        except Exception as exc:
            agent_result["stop"] = {"error": str(exc)}
        results[agent.agent_name] = agent_result
    updated_state = state.model_copy(update={"active": False, "stopped_at_utc": utc_now_iso()})
    save_demo_state(paths.state_path, updated_state)
    print(json.dumps({"already_stopped": False, "agents": results}, indent=2))
    return 0


def _optional_path_from_payload(payload: dict[str, Any], key: str) -> Path | None:
    """Return an optional path value from a payload."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(value).resolve()


def _optional_str_from_payload(payload: dict[str, Any], key: str) -> str | None:
    """Return an optional string value from a payload."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _optional_int_from_payload(payload: dict[str, Any], key: str) -> int | None:
    """Return an optional integer value from a payload."""

    value = payload.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


if __name__ == "__main__":
    raise SystemExit(main())

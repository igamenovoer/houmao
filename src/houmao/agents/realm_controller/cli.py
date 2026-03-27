"""CLI entrypoint for realm controller workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

from houmao.agents.brain_builder import (
    BuildRequest,
    build_brain_home,
    load_launch_overrides_input,
)
from houmao.mailbox.protocol import mailbox_address_path_segment

from .agent_identity import AGENT_DEF_DIR_ENV_VAR, is_path_like_agent_identity
from .errors import BrainLaunchRuntimeError
from .loaders import load_blueprint, load_brain_recipe_from_path
from .mail_commands import (
    ensure_mailbox_command_ready,
    load_mail_body_file,
    prepare_mail_prompt,
    run_mail_prompt,
    validate_attachment_paths,
)
from .models import BackendKind
from .registry_storage import cleanup_stale_live_agent_records
from .runtime import (
    AgentIdentityResolution,
    resolve_agent_identity,
    resume_runtime_session,
    start_runtime_session,
)

_DEFAULT_AGENT_DEF_DIR = Path(".agentsys") / "agents"
_AMBIENT_AGENT_DEF_DIR_HELP = (
    "Agent definition directory root (contains tools/, skills/, and roles/). "
    "Precedence: CLI > AGENTSYS_AGENT_DEF_DIR > <pwd>/.agentsys/agents."
)
_CONTROL_AGENT_DEF_DIR_HELP = (
    "Agent definition directory root (contains tools/, skills/, and roles/). "
    "For manifest-path control: CLI > AGENTSYS_AGENT_DEF_DIR > <pwd>/.agentsys/agents. "
    "For name-based tmux control: explicit CLI override or the addressed session's "
    "AGENTSYS_AGENT_DEF_DIR."
)
_DEPRECATED_CAO_RUNTIME_GUIDANCE = (
    "Standalone backend='cao_rest' operator workflows are retired. "
    "Use `houmao-server` with `houmao-mgr` instead."
)


def main(argv: list[str] | None = None) -> int:
    """Run the brain launch runtime CLI.

    Parameters
    ----------
    argv:
        Optional argument list. Defaults to `sys.argv[1:]`.

    Returns
    -------
    int
        Process exit code.
    """

    parser = _build_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    try:
        if args.command == "build-brain":
            return _cmd_build_brain(args)
        if args.command == "start-session":
            return _cmd_start_session(args)
        if args.command == "send-prompt":
            return _cmd_send_prompt(args)
        if args.command == "gateway-send-prompt":
            return _cmd_gateway_send_prompt(args)
        if args.command == "send-keys":
            return _cmd_send_keys(args)
        if args.command == "gateway-interrupt":
            return _cmd_gateway_interrupt(args)
        if args.command == "stop-session":
            return _cmd_stop_session(args)
        if args.command == "attach-gateway":
            return _cmd_attach_gateway(args)
        if args.command == "detach-gateway":
            return _cmd_detach_gateway(args)
        if args.command == "gateway-status":
            return _cmd_gateway_status(args)
        if args.command == "cleanup-registry":
            return _cmd_cleanup_registry(args)
        if args.command == "mail":
            return _cmd_mail(args)
    except BrainLaunchRuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Realm controller CLI (build/start/prompt/stop).")
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build-brain", help="Build a brain home")
    build.add_argument(
        "--agent-def-dir",
        default=None,
        help=_AMBIENT_AGENT_DEF_DIR_HELP,
    )
    build.add_argument("--runtime-root", default=None, help="Runtime root")
    build.add_argument("--preset", help="Path to role-scoped preset")
    build.add_argument("--recipe", help=argparse.SUPPRESS)
    build.add_argument("--blueprint", help=argparse.SUPPRESS)
    build.add_argument("--tool", help="Tool name")
    build.add_argument("--skill", dest="skills", action="append", default=[])
    build.add_argument("--setup", help="Tool setup bundle name")
    build.add_argument("--config-profile", help=argparse.SUPPRESS)
    build.add_argument("--auth", help="Tool auth bundle name")
    build.add_argument("--cred-profile", help=argparse.SUPPRESS)
    build.add_argument(
        "--launch-overrides",
        help="Path to launch-overrides YAML/JSON, or an inline JSON object",
    )
    build.add_argument("--home-id", help="Optional home id")
    build.add_argument("--reuse-home", action="store_true", help="Allow reusing home id")

    start = subparsers.add_parser("start-session", help="Start a local/CAO session")
    start.add_argument(
        "--agent-def-dir",
        default=None,
        help=_AMBIENT_AGENT_DEF_DIR_HELP,
    )
    start.add_argument("--runtime-root", default=None, help="Runtime root")
    start.add_argument("--brain-manifest", required=True, help="Built brain manifest path")
    start.add_argument("--role", help="Role name")
    start.add_argument("--blueprint", help=argparse.SUPPRESS)
    start.add_argument(
        "--backend",
        choices=[
            "local_interactive",
            "codex_headless",
            "codex_app_server",
            "claude_headless",
            "gemini_headless",
            "cao_rest",
            "houmao_server_rest",
        ],
        help="Backend override",
    )
    start.add_argument("--workdir", default=".", help="Working directory")
    start.add_argument("--cao-base-url", default="http://localhost:9889")
    start.add_argument("--houmao-base-url", default="http://127.0.0.1:9889")
    start.add_argument("--cao-profile-store", help="CAO profile store override")
    start.add_argument(
        "--cao-parsing-mode",
        choices=["cao_only", "shadow_only"],
        help="CAO parsing mode override",
    )
    start.add_argument(
        "--agent-identity",
        help="Optional tmux-backed agent name",
    )
    start.add_argument(
        "--agent-id",
        help="Optional authoritative agent id override for tmux-backed sessions.",
    )
    start.add_argument(
        "--mailbox-transport",
        choices=["filesystem", "stalwart", "none"],
        help="Optional mailbox transport override",
    )
    start.add_argument(
        "--mailbox-root",
        help="Optional filesystem mailbox root override",
    )
    start.add_argument(
        "--mailbox-principal-id",
        help="Optional mailbox principal-id override",
    )
    start.add_argument(
        "--mailbox-address",
        help="Optional mailbox address override",
    )
    start.add_argument(
        "--mailbox-stalwart-base-url",
        help="Optional Stalwart base URL override used to derive JMAP and management URLs.",
    )
    start.add_argument(
        "--mailbox-stalwart-jmap-url",
        help="Optional Stalwart JMAP URL override.",
    )
    start.add_argument(
        "--mailbox-stalwart-management-url",
        help="Optional Stalwart management API URL override.",
    )
    start.add_argument(
        "--mailbox-stalwart-login-identity",
        help="Optional Stalwart login identity override.",
    )
    start.add_argument(
        "--gateway-auto-attach",
        action="store_true",
        help="Attach a live gateway immediately after session startup.",
    )
    start.add_argument(
        "--gateway-host",
        choices=["127.0.0.1", "0.0.0.0"],
        help="Optional gateway listener host override for attach actions.",
    )
    start.add_argument(
        "--gateway-port",
        type=int,
        help="Optional gateway listener port override for attach actions.",
    )

    prompt = subparsers.add_parser("send-prompt", help="Send a prompt to a resumed session")
    prompt.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    prompt.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(prompt)
    prompt.add_argument("--prompt", required=True, help="Prompt text")

    gateway_prompt = subparsers.add_parser(
        "gateway-send-prompt",
        help="Submit a prompt through an already attached live gateway",
    )
    gateway_prompt.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    gateway_prompt.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(gateway_prompt)
    gateway_prompt.add_argument("--prompt", required=True, help="Prompt text")

    send_keys = subparsers.add_parser(
        "send-keys",
        help="Send raw control input to a resumed session",
    )
    send_keys.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    send_keys.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(send_keys)
    send_keys.add_argument(
        "--sequence",
        required=True,
        help="Mixed literal/special-key control-input sequence",
    )
    send_keys.add_argument(
        "--escape-special-keys",
        action="store_true",
        help="Send the full sequence literally without parsing <[key-name]> tokens",
    )

    gateway_interrupt = subparsers.add_parser(
        "gateway-interrupt",
        help="Submit an interrupt through an already attached live gateway",
    )
    gateway_interrupt.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    gateway_interrupt.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(gateway_interrupt)

    cleanup_registry = subparsers.add_parser(
        "cleanup-registry",
        help="Remove stale shared-registry live-agent directories",
    )
    cleanup_registry.add_argument(
        "--grace-seconds",
        type=int,
        default=300,
        help="Extra grace period after lease expiry before removing stale directories.",
    )

    stop = subparsers.add_parser("stop-session", help="Stop a session")
    stop.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    stop.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(stop)
    stop.add_argument(
        "--force-cleanup",
        action="store_true",
        help="For tmux-backed headless sessions, also delete tmux session",
    )

    attach_gateway = subparsers.add_parser(
        "attach-gateway",
        help="Attach a live gateway to a running runtime-owned session",
    )
    attach_gateway.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    attach_gateway.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(attach_gateway)
    attach_gateway.add_argument(
        "--gateway-host",
        choices=["127.0.0.1", "0.0.0.0"],
        help="Optional listener host override.",
    )
    attach_gateway.add_argument(
        "--gateway-port",
        type=int,
        help="Optional listener port override.",
    )

    detach_gateway = subparsers.add_parser(
        "detach-gateway",
        help="Detach a live gateway without stopping the managed session",
    )
    detach_gateway.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    detach_gateway.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(detach_gateway)

    gateway_status = subparsers.add_parser(
        "gateway-status",
        help="Read gateway status from the live gateway or stable state artifact",
    )
    gateway_status.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    gateway_status.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(gateway_status)

    mail = subparsers.add_parser("mail", help="Run mailbox operations against a resumed session")
    mail_subparsers = mail.add_subparsers(dest="mail_command")

    mail_check = mail_subparsers.add_parser("check", help="Ask a session to check its mailbox")
    _add_mail_common_args(mail_check)
    mail_check.add_argument("--unread-only", action="store_true")
    mail_check.add_argument("--limit", type=int)
    mail_check.add_argument("--since", help="Optional RFC3339 lower bound")

    mail_send = mail_subparsers.add_parser("send", help="Ask a session to send mailbox content")
    _add_mail_common_args(mail_send)
    mail_send.add_argument("--to", action="append", required=True, dest="to_recipients")
    mail_send.add_argument("--cc", action="append", default=[], dest="cc_recipients")
    mail_send.add_argument("--subject", required=True)
    mail_send.add_argument("--body-file")
    mail_send.add_argument("--body-content")
    mail_send.add_argument("--attach", action="append", default=[], dest="attachments")

    mail_reply = mail_subparsers.add_parser(
        "reply",
        help="Ask a session to reply to an existing mailbox message",
    )
    _add_mail_common_args(mail_reply)
    reply_target_group = mail_reply.add_mutually_exclusive_group(required=True)
    reply_target_group.add_argument(
        "--message-ref",
        dest="message_ref",
        help="Opaque message reference from shared mailbox check results",
    )
    reply_target_group.add_argument(
        "--message-id",
        dest="message_ref",
        help=argparse.SUPPRESS,
    )
    mail_reply.add_argument("--body-file")
    mail_reply.add_argument("--body-content")
    mail_reply.add_argument("--attach", action="append", default=[], dest="attachments")

    return parser


def _cmd_build_brain(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir = _resolve_agent_def_dir(args.agent_def_dir, cwd=cwd)
    runtime_root = _optional_path(args.runtime_root, base=cwd)

    recipe = None
    preset_path: Path | None = None
    requested_preset = args.preset or args.recipe
    if requested_preset:
        preset_path = _resolve_path(requested_preset, base=agent_def_dir)
        recipe = load_brain_recipe_from_path(preset_path)
    elif args.blueprint:
        blueprint = load_blueprint(_resolve_path(args.blueprint, base=agent_def_dir))
        preset_path = blueprint.brain_recipe_path
        recipe = load_brain_recipe_from_path(preset_path)

    direct_launch_overrides = (
        load_launch_overrides_input(
            args.launch_overrides,
            base=cwd,
            source="--launch-overrides",
        )
        if args.launch_overrides
        else None
    )

    tool = args.tool or (recipe.tool if recipe else None)
    skills = list(args.skills) if args.skills else (recipe.skills if recipe else [])
    setup = args.setup or args.config_profile or (recipe.setup if recipe else None)
    auth = args.auth or args.cred_profile or (recipe.auth if recipe else None)

    missing: list[str] = []
    if not tool:
        missing.append("--tool")
    if not skills:
        missing.append("--skill (repeatable)")
    if not setup:
        missing.append("--setup")
    if not auth:
        missing.append("--auth")
    if missing:
        raise BrainLaunchRuntimeError(f"Missing required build inputs: {', '.join(missing)}")

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=runtime_root,
            tool=str(tool),
            skills=[str(skill) for skill in skills],
            setup=str(setup),
            auth=str(auth),
            preset_path=preset_path,
            preset_launch_overrides=recipe.launch_overrides if recipe else None,
            mailbox=recipe.mailbox if recipe else None,
            agent_name=recipe.default_agent_name if recipe else None,
            home_id=args.home_id,
            reuse_home=bool(args.reuse_home),
            launch_overrides=direct_launch_overrides,
            extra=recipe.extra if recipe else None,
        )
    )

    print(
        json.dumps(
            {
                "home_id": result.home_id,
                "home_path": str(result.home_path),
                "manifest_path": str(result.manifest_path),
                "launch_helper_path": str(result.launch_helper_path),
            },
            indent=2,
        )
    )
    return 0


def _reject_deprecated_raw_cao_backend(*, backend: BackendKind | None) -> None:
    """Reject public raw CAO-backed start requests with migration guidance."""

    if backend == "cao_rest":
        raise BrainLaunchRuntimeError(_DEPRECATED_CAO_RUNTIME_GUIDANCE)


def _reject_deprecated_cao_runtime_controller(controller: object) -> None:
    """Reject public control flows bound to deprecated raw CAO-backed sessions."""

    launch_plan = getattr(controller, "launch_plan", None)
    backend = getattr(launch_plan, "backend", None)
    if backend == "cao_rest":
        raise BrainLaunchRuntimeError(_DEPRECATED_CAO_RUNTIME_GUIDANCE)


def _cmd_start_session(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir = _resolve_agent_def_dir(args.agent_def_dir, cwd=cwd)
    blueprint = (
        load_blueprint(_resolve_path(args.blueprint, base=agent_def_dir))
        if args.blueprint
        else None
    )
    role_name = str(args.role) if args.role else _resolve_role(args, agent_def_dir=agent_def_dir)
    backend: BackendKind | None = args.backend
    _reject_deprecated_raw_cao_backend(backend=backend)

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=_resolve_path(args.brain_manifest, base=cwd),
        role_name=role_name,
        runtime_root=_optional_path(args.runtime_root, base=cwd),
        backend=backend,
        working_directory=_resolve_path(args.workdir, base=cwd),
        api_base_url=(
            args.houmao_base_url if backend == "houmao_server_rest" else args.cao_base_url
        ),
        cao_profile_store_dir=_optional_path(args.cao_profile_store, base=cwd),
        agent_identity=args.agent_identity,
        agent_id=args.agent_id,
        cao_parsing_mode=args.cao_parsing_mode,
        mailbox_transport=args.mailbox_transport,
        mailbox_root=_optional_path(args.mailbox_root, base=cwd),
        mailbox_principal_id=args.mailbox_principal_id,
        mailbox_address=args.mailbox_address,
        mailbox_stalwart_base_url=args.mailbox_stalwart_base_url,
        mailbox_stalwart_jmap_url=args.mailbox_stalwart_jmap_url,
        mailbox_stalwart_management_url=args.mailbox_stalwart_management_url,
        mailbox_stalwart_login_identity=args.mailbox_stalwart_login_identity,
        blueprint_gateway_defaults=blueprint.gateway if blueprint is not None else None,
        gateway_auto_attach=bool(args.gateway_auto_attach),
        gateway_host=args.gateway_host,
        gateway_port=args.gateway_port,
    )

    for warning in controller.agent_identity_warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for warning in controller.startup_warnings:
        print(f"warning: {warning}", file=sys.stderr)

    payload: dict[str, object] = {
        "session_manifest": str(controller.manifest_path),
        "backend": controller.launch_plan.backend,
        "tool": controller.launch_plan.tool,
    }
    agent_identity = getattr(controller, "agent_identity", None)
    if agent_identity is not None:
        payload["agent_identity"] = agent_identity
        payload["agent_name"] = agent_identity
    agent_id = getattr(controller, "agent_id", None)
    if agent_id is not None:
        payload["agent_id"] = agent_id
    tmux_session_name = getattr(controller, "tmux_session_name", None)
    if tmux_session_name is not None:
        payload["tmux_session_name"] = tmux_session_name
    job_dir = getattr(controller, "job_dir", None)
    if job_dir is not None:
        payload["job_dir"] = str(job_dir)
    parsing_mode = getattr(controller, "parsing_mode", None)
    if parsing_mode is not None:
        payload["parsing_mode"] = parsing_mode
    gateway_host = getattr(controller, "gateway_host", None)
    if gateway_host is not None:
        payload["gateway_host"] = gateway_host
    gateway_port = getattr(controller, "gateway_port", None)
    if gateway_port is not None:
        payload["gateway_port"] = gateway_port
    gateway_auto_attach_error = getattr(controller, "gateway_auto_attach_error", None)
    if gateway_auto_attach_error is not None:
        payload["gateway_auto_attach_error"] = gateway_auto_attach_error
    mailbox = getattr(controller.launch_plan, "mailbox", None)
    if mailbox is not None:
        payload["mailbox"] = mailbox.redacted_payload()
    launch_policy_provenance = getattr(controller.launch_plan, "launch_policy_provenance", None)
    if launch_policy_provenance is not None:
        payload["launch_policy_provenance"] = launch_policy_provenance.to_payload()
    launch_plan_metadata = getattr(controller.launch_plan, "metadata", None)
    launch_policy_metadata = (
        launch_plan_metadata.get("launch_policy")
        if isinstance(launch_plan_metadata, dict)
        else None
    )
    if isinstance(launch_policy_metadata, dict):
        payload["launch_policy"] = launch_policy_metadata

    print(json.dumps(payload, indent=2))
    return 2 if gateway_auto_attach_error is not None else 0


def _cmd_send_prompt(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)

    events = controller.send_prompt(args.prompt)
    for event in events:
        print(json.dumps(asdict(event), sort_keys=True))
    _emit_controller_operation_warnings(controller)
    return 0


def _cmd_gateway_send_prompt(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)
    payload = controller.send_prompt_via_gateway(args.prompt)
    print(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _cmd_send_keys(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)

    result = controller.send_input_ex(
        args.sequence,
        escape_special_keys=bool(args.escape_special_keys),
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    _emit_controller_operation_warnings(controller)
    return 0 if result.status == "ok" else 2


def _cmd_gateway_interrupt(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)
    payload = controller.interrupt_via_gateway()
    print(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _cmd_stop_session(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)

    result = controller.stop(force_cleanup=bool(args.force_cleanup))
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    _emit_controller_operation_warnings(controller)
    return 0 if result.status == "ok" else 2


def _cmd_attach_gateway(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)
    result = controller.attach_gateway(
        host_override=args.gateway_host,
        port_override=args.gateway_port,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.status == "ok" else 2


def _cmd_detach_gateway(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)
    result = controller.detach_gateway()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.status == "ok" else 2


def _cmd_gateway_status(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)
    payload = controller.gateway_status()
    print(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def _cmd_cleanup_registry(args: argparse.Namespace) -> int:
    grace_seconds = int(args.grace_seconds)
    if grace_seconds < 0:
        raise BrainLaunchRuntimeError("--grace-seconds must be >= 0.")

    result = cleanup_stale_live_agent_records(
        grace_period=timedelta(seconds=grace_seconds),
    )
    removed_agent_ids = tuple(
        getattr(result, "removed_agent_ids", getattr(result, "removed_agent_keys", ()))
    )
    preserved_agent_ids = tuple(
        getattr(result, "preserved_agent_ids", getattr(result, "preserved_agent_keys", ()))
    )
    failed_agent_ids = tuple(
        getattr(result, "failed_agent_ids", getattr(result, "failed_agent_keys", ()))
    )
    payload = {
        "registry_root": str(result.registry_root),
        "grace_seconds": grace_seconds,
        "removed_agent_ids": list(removed_agent_ids),
        "preserved_agent_ids": list(preserved_agent_ids),
        "failed_agent_ids": list(failed_agent_ids),
        "removed_count": len(removed_agent_ids),
        "preserved_count": len(preserved_agent_ids),
        "failed_count": len(failed_agent_ids),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_mail(args: argparse.Namespace) -> int:
    if args.mail_command is None:
        raise BrainLaunchRuntimeError("mail requires a subcommand: check, send, or reply.")

    cwd = Path.cwd().resolve()
    agent_def_dir, resolved = _resolve_control_target(
        agent_identity=args.agent_identity,
        agent_def_dir_cli_value=args.agent_def_dir,
        cwd=cwd,
    )
    for warning in resolved.warnings:
        print(f"warning: {warning}", file=sys.stderr)

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=resolved.session_manifest_path,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    _reject_deprecated_cao_runtime_controller(controller)
    mailbox = ensure_mailbox_command_ready(
        controller.launch_plan,
        tmux_session_name=getattr(controller, "tmux_session_name", None),
    )
    prefer_live_gateway = False
    try:
        gateway_status = controller.gateway_status()
        prefer_live_gateway = (
            gateway_status.gateway_health == "healthy"
            and gateway_status.gateway_host == "127.0.0.1"
        )
    except Exception:
        prefer_live_gateway = False
    prompt_request = prepare_mail_prompt(
        launch_plan=controller.launch_plan,
        operation=args.mail_command,
        args=_mail_args_from_cli(args, cwd=cwd),
        prefer_live_gateway=prefer_live_gateway,
        tmux_session_name=getattr(controller, "tmux_session_name", None),
    )
    result = run_mail_prompt(
        send_prompt=controller.send_prompt,
        send_mail_prompt=(
            controller.send_mail_prompt
            if callable(getattr(controller, "send_mail_prompt", None))
            else None
        ),
        prompt_request=prompt_request,
        mailbox=mailbox,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    _emit_controller_operation_warnings(controller)
    return 0


def _emit_controller_operation_warnings(controller: object) -> None:
    """Print non-fatal controller warnings for the just-finished operation."""

    consume = getattr(controller, "consume_operation_warnings", None)
    if not callable(consume):
        return
    for warning in consume():
        print(f"warning: {warning}", file=sys.stderr)


def _resolve_path(value: str, *, base: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _optional_path(value: str | None, *, base: Path) -> Path | None:
    if value is None:
        return None
    return _resolve_path(value, base=base)


def _resolve_role(args: argparse.Namespace, *, agent_def_dir: Path) -> str:
    if args.role:
        return str(args.role)
    if args.blueprint:
        blueprint = load_blueprint(_resolve_path(args.blueprint, base=agent_def_dir))
        return blueprint.role
    raise BrainLaunchRuntimeError("start-session requires --role (or legacy --blueprint)")


def _resolve_control_target(
    *,
    agent_identity: str,
    agent_def_dir_cli_value: str | None,
    cwd: Path,
) -> tuple[Path, AgentIdentityResolution]:
    """Resolve control target identity plus the effective agent-definition root."""

    if is_path_like_agent_identity(agent_identity):
        return (
            _resolve_agent_def_dir(agent_def_dir_cli_value, cwd=cwd),
            resolve_agent_identity(agent_identity=agent_identity, base=cwd),
        )

    resolved = resolve_agent_identity(
        agent_identity=agent_identity,
        base=cwd,
        explicit_agent_def_dir=_resolve_explicit_agent_def_dir_override(
            agent_def_dir_cli_value,
            cwd=cwd,
        ),
    )
    if resolved.agent_def_dir is None:
        raise BrainLaunchRuntimeError(
            "Name-based session control requires a resolved agent definition directory."
        )
    return resolved.agent_def_dir, resolved


def _resolve_explicit_agent_def_dir_override(cli_value: str | None, *, cwd: Path) -> Path | None:
    """Resolve only the explicit CLI override for name-based control flows."""

    if cli_value is None:
        return None
    return _resolve_path(cli_value, base=cwd)


def _resolve_agent_def_dir(cli_value: str | None, *, cwd: Path) -> Path:
    if cli_value is not None:
        return _resolve_path(cli_value, base=cwd)

    env_value = os.environ.get(AGENT_DEF_DIR_ENV_VAR)
    if env_value:
        return _resolve_path(env_value, base=cwd)

    return (cwd / _DEFAULT_AGENT_DEF_DIR).resolve()


def _add_mail_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--agent-def-dir",
        default=None,
        help=_CONTROL_AGENT_DEF_DIR_HELP,
    )
    parser.add_argument(
        "--agent-identity",
        required=True,
        help="Agent name or manifest path",
    )
    _add_cao_parsing_mode_arg(parser)


def _add_cao_parsing_mode_arg(parser: argparse.ArgumentParser) -> None:
    """Add one optional CAO parsing-mode override for resumed session control."""

    parser.add_argument(
        "--cao-parsing-mode",
        choices=["cao_only", "shadow_only"],
        help=(
            "CAO parsing mode override for resumed control commands. "
            "Default posture is shadow_only; use cao_only only for advanced debugging "
            "or native CAO-path validation."
        ),
    )


def _mail_args_from_cli(args: argparse.Namespace, *, cwd: Path) -> dict[str, object]:
    if args.mail_command == "check":
        payload: dict[str, object] = {}
        if bool(args.unread_only):
            payload["unread_only"] = True
        if args.limit is not None:
            payload["limit"] = int(args.limit)
        if args.since is not None:
            payload["since"] = str(args.since)
        return payload

    attachments = validate_attachment_paths(
        [_resolve_path(value, base=cwd) for value in list(getattr(args, "attachments", ()) or ())]
    )
    body_file = getattr(args, "body_file", None)
    body_content = getattr(args, "body_content", None)
    if body_file and body_content:
        raise BrainLaunchRuntimeError(
            f"mail {args.mail_command} accepts only one of --body-file or --body-content."
        )
    body_markdown = load_mail_body_file(_resolve_path(body_file, base=cwd)) if body_file else None
    if body_markdown is None and (body_content is None or not str(body_content).strip()):
        raise BrainLaunchRuntimeError(
            f"mail {args.mail_command} requires explicit body content via --body-file or --body-content."
        )
    if body_markdown is None:
        body_markdown = str(body_content)

    if args.mail_command == "send":
        return {
            "to": _validated_mailbox_addresses(list(args.to_recipients)),
            "cc": _validated_mailbox_addresses(list(args.cc_recipients)),
            "subject": str(args.subject),
            "body_content": body_markdown,
            "attachments": attachments,
        }
    if args.mail_command == "reply":
        return {
            "message_ref": str(args.message_ref),
            "body_content": body_markdown,
            "attachments": attachments,
        }
    raise BrainLaunchRuntimeError(f"Unsupported mail subcommand: {args.mail_command!r}")


def _validated_mailbox_addresses(values: list[str]) -> list[str]:
    """Validate full mailbox recipient addresses for runtime mail commands."""

    normalized: list[str] = []
    for value in values:
        try:
            normalized.append(mailbox_address_path_segment(str(value)))
        except RuntimeError as exc:
            raise BrainLaunchRuntimeError(
                f"mail recipients must use full mailbox addresses; got `{value}` ({exc})"
            ) from exc
    return normalized

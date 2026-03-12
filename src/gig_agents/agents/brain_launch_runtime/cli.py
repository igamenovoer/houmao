"""CLI entrypoint for brain launch runtime workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from gig_agents.agents.brain_builder import BuildRequest, build_brain_home

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
from .runtime import (
    AgentIdentityResolution,
    resolve_agent_identity,
    resume_runtime_session,
    start_runtime_session,
)

_DEFAULT_AGENT_DEF_DIR = Path(".agentsys") / "agents"
_AMBIENT_AGENT_DEF_DIR_HELP = (
    "Agent definition directory root (contains brains/, roles/, blueprints/). "
    "Precedence: CLI > AGENTSYS_AGENT_DEF_DIR > <pwd>/.agentsys/agents."
)
_CONTROL_AGENT_DEF_DIR_HELP = (
    "Agent definition directory root (contains brains/, roles/, blueprints/). "
    "For manifest-path control: CLI > AGENTSYS_AGENT_DEF_DIR > <pwd>/.agentsys/agents. "
    "For name-based tmux control: explicit CLI override or the addressed session's "
    "AGENTSYS_AGENT_DEF_DIR."
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
        if args.command == "send-keys":
            return _cmd_send_keys(args)
        if args.command == "stop-session":
            return _cmd_stop_session(args)
        if args.command == "mail":
            return _cmd_mail(args)
    except BrainLaunchRuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Brain launch runtime CLI (build/start/prompt/stop)."
    )
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build-brain", help="Build a brain home")
    build.add_argument(
        "--agent-def-dir",
        default=None,
        help=_AMBIENT_AGENT_DEF_DIR_HELP,
    )
    build.add_argument("--runtime-root", default="tmp/agents-runtime", help="Runtime root")
    build.add_argument("--recipe", help="Path to brain recipe")
    build.add_argument("--blueprint", help="Path to blueprint")
    build.add_argument("--tool", help="Tool name")
    build.add_argument("--skill", dest="skills", action="append", default=[])
    build.add_argument("--config-profile", help="Config profile")
    build.add_argument("--cred-profile", help="Credential profile")
    build.add_argument("--home-id", help="Optional home id")
    build.add_argument("--reuse-home", action="store_true", help="Allow reusing home id")

    start = subparsers.add_parser("start-session", help="Start a local/CAO session")
    start.add_argument(
        "--agent-def-dir",
        default=None,
        help=_AMBIENT_AGENT_DEF_DIR_HELP,
    )
    start.add_argument("--runtime-root", default="tmp/agents-runtime", help="Runtime root")
    start.add_argument("--brain-manifest", required=True, help="Built brain manifest path")
    start.add_argument("--role", help="Role name")
    start.add_argument("--blueprint", help="Optional blueprint to source role from")
    start.add_argument(
        "--backend",
        choices=[
            "codex_headless",
            "codex_app_server",
            "claude_headless",
            "gemini_headless",
            "cao_rest",
        ],
        help="Backend override",
    )
    start.add_argument("--workdir", default=".", help="Working directory")
    start.add_argument("--cao-base-url", default="http://localhost:9889")
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
        "--mailbox-transport",
        choices=["filesystem", "none"],
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
    prompt.add_argument("--prompt", required=True, help="Prompt text")

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
    stop.add_argument(
        "--force-cleanup",
        action="store_true",
        help="For tmux-backed headless sessions, also delete tmux session",
    )

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
    mail_send.add_argument("--instruction")
    mail_send.add_argument("--body-file")
    mail_send.add_argument("--attach", action="append", default=[], dest="attachments")

    mail_reply = mail_subparsers.add_parser(
        "reply",
        help="Ask a session to reply to an existing mailbox message",
    )
    _add_mail_common_args(mail_reply)
    mail_reply.add_argument("--message-id", required=True)
    mail_reply.add_argument("--instruction")
    mail_reply.add_argument("--body-file")
    mail_reply.add_argument("--attach", action="append", default=[], dest="attachments")

    return parser


def _cmd_build_brain(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir = _resolve_agent_def_dir(args.agent_def_dir, cwd=cwd)
    runtime_root = _resolve_path(args.runtime_root, base=cwd)

    recipe = None
    if args.recipe:
        recipe = load_brain_recipe_from_path(_resolve_path(args.recipe, base=agent_def_dir))
    elif args.blueprint:
        blueprint = load_blueprint(_resolve_path(args.blueprint, base=agent_def_dir))
        recipe = load_brain_recipe_from_path(blueprint.brain_recipe_path)

    tool = args.tool or (recipe.tool if recipe else None)
    skills = list(args.skills) if args.skills else (recipe.skills if recipe else [])
    config_profile = args.config_profile or (recipe.config_profile if recipe else None)
    credential_profile = args.cred_profile or (recipe.credential_profile if recipe else None)

    missing: list[str] = []
    if not tool:
        missing.append("--tool")
    if not skills:
        missing.append("--skill (repeatable)")
    if not config_profile:
        missing.append("--config-profile")
    if not credential_profile:
        missing.append("--cred-profile")
    if missing:
        raise BrainLaunchRuntimeError(f"Missing required build inputs: {', '.join(missing)}")

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=runtime_root,
            tool=str(tool),
            skills=[str(skill) for skill in skills],
            config_profile=str(config_profile),
            credential_profile=str(credential_profile),
            mailbox=recipe.mailbox if recipe else None,
            home_id=args.home_id,
            reuse_home=bool(args.reuse_home),
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


def _cmd_start_session(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    agent_def_dir = _resolve_agent_def_dir(args.agent_def_dir, cwd=cwd)
    role_name = _resolve_role(args, agent_def_dir=agent_def_dir)
    backend: BackendKind | None = args.backend

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=_resolve_path(args.brain_manifest, base=cwd),
        role_name=role_name,
        runtime_root=_resolve_path(args.runtime_root, base=cwd),
        backend=backend,
        working_directory=_resolve_path(args.workdir, base=cwd),
        api_base_url=args.cao_base_url,
        cao_profile_store_dir=_optional_path(args.cao_profile_store, base=cwd),
        agent_identity=args.agent_identity,
        cao_parsing_mode=args.cao_parsing_mode,
        mailbox_transport=args.mailbox_transport,
        mailbox_root=_optional_path(args.mailbox_root, base=cwd),
        mailbox_principal_id=args.mailbox_principal_id,
        mailbox_address=args.mailbox_address,
    )

    for warning in controller.agent_identity_warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for warning in controller.startup_warnings:
        print(f"warning: {warning}", file=sys.stderr)

    payload = {
        "session_manifest": str(controller.manifest_path),
        "backend": controller.launch_plan.backend,
        "tool": controller.launch_plan.tool,
    }
    if controller.agent_identity is not None:
        payload["agent_identity"] = controller.agent_identity
    if controller.parsing_mode is not None:
        payload["parsing_mode"] = controller.parsing_mode
    mailbox = getattr(controller.launch_plan, "mailbox", None)
    if mailbox is not None:
        payload["mailbox"] = mailbox.redacted_payload()

    print(json.dumps(payload, indent=2))
    return 0


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
    )

    events = controller.send_prompt(args.prompt)
    for event in events:
        print(json.dumps(asdict(event), sort_keys=True))
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
    )

    result = controller.send_input_ex(
        args.sequence,
        escape_special_keys=bool(args.escape_special_keys),
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.status == "ok" else 2


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
    )

    result = controller.stop(force_cleanup=bool(args.force_cleanup))
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.status == "ok" else 2


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
    )
    mailbox = ensure_mailbox_command_ready(controller.launch_plan)
    prompt_request = prepare_mail_prompt(
        launch_plan=controller.launch_plan,
        operation=args.mail_command,
        args=_mail_args_from_cli(args, cwd=cwd),
    )
    result = run_mail_prompt(
        send_prompt=controller.send_prompt,
        prompt_request=prompt_request,
        mailbox=mailbox,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


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
    raise BrainLaunchRuntimeError("start-session requires --role or --blueprint")


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
    body_markdown = (
        load_mail_body_file(_resolve_path(args.body_file, base=cwd))
        if getattr(args, "body_file", None)
        else None
    )
    instruction = str(args.instruction) if getattr(args, "instruction", None) is not None else None
    if body_markdown is None and (instruction is None or not instruction.strip()):
        raise BrainLaunchRuntimeError(
            f"mail {args.mail_command} requires --instruction or --body-file."
        )

    if args.mail_command == "send":
        return {
            "to": [str(value) for value in args.to_recipients],
            "cc": [str(value) for value in args.cc_recipients],
            "subject": str(args.subject),
            "instruction": instruction,
            "body_markdown": body_markdown,
            "attachments": attachments,
        }
    if args.mail_command == "reply":
        return {
            "message_id": str(args.message_id),
            "instruction": instruction,
            "body_markdown": body_markdown,
            "attachments": attachments,
        }
    raise BrainLaunchRuntimeError(f"Unsupported mail subcommand: {args.mail_command!r}")

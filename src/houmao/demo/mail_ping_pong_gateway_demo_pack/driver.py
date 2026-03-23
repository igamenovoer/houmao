"""CLI driver for the headless mail ping-pong gateway demo pack."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoManagedAgentSubmitPromptRequest

from .agents import (
    attach_gateway_and_enable_notifier,
    build_demo_environment,
    build_participant_brain,
    disable_notifier,
    enable_notifier,
    ensure_project_workdir_from_fixture,
    expose_runtime_skills_in_project,
    launch_participant,
    stop_participant,
)
from .events import build_conversation_events, build_progress_summary, collect_conversation_evidence
from .models import (
    DEFAULT_DEMO_OUTPUT_DIR_RELATIVE,
    DEFAULT_EXPECTED_REPORT_RELATIVE,
    DEFAULT_PARAMETERS_RELATIVE,
    DemoState,
    KickoffRequestState,
    build_demo_layout,
    load_demo_parameters,
    load_demo_state,
    resolve_repo_relative_path,
    save_demo_state,
    utc_now_iso,
    write_json,
    write_json_lines,
)
from .reporting import (
    build_inspect_snapshot,
    build_report_snapshot,
    sanitize_report,
    verify_sanitized_report,
)
from .server import DemoServerError, choose_free_loopback_port, start_demo_server, stop_demo_server


class DemoPackError(RuntimeError):
    """Raised when the demo pack cannot continue safely."""


def main(argv: list[str] | None = None) -> int:
    """Run the demo-pack CLI."""

    parser = argparse.ArgumentParser(description="Headless mail ping-pong gateway demo pack")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("start", "kickoff", "pause", "continue", "inspect", "stop"):
        command_parser = subparsers.add_parser(name)
        _add_common_arguments(command_parser)

    wait_parser = subparsers.add_parser("wait")
    _add_common_arguments(wait_parser)
    wait_parser.add_argument("--timeout-seconds", type=float, default=None)
    wait_parser.add_argument("--poll-interval-seconds", type=float, default=None)

    verify_parser = subparsers.add_parser("verify")
    _add_common_arguments(verify_parser)
    verify_parser.add_argument(
        "--expected-report",
        default=DEFAULT_EXPECTED_REPORT_RELATIVE,
        help="Repository-relative or absolute expected report snapshot path.",
    )
    verify_parser.add_argument("--snapshot", action="store_true")

    auto_parser = subparsers.add_parser("auto")
    _add_common_arguments(auto_parser)
    auto_parser.add_argument("--timeout-seconds", type=float, default=None)
    auto_parser.add_argument("--poll-interval-seconds", type=float, default=None)
    auto_parser.add_argument(
        "--expected-report",
        default=DEFAULT_EXPECTED_REPORT_RELATIVE,
        help="Repository-relative or absolute expected report snapshot path.",
    )
    auto_parser.add_argument("--snapshot", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            return _command_start(args)
        if args.command == "kickoff":
            return _command_kickoff(args)
        if args.command == "wait":
            return _command_wait(args)
        if args.command == "pause":
            return _command_pause(args)
        if args.command == "continue":
            return _command_continue(args)
        if args.command == "inspect":
            return _command_inspect(args)
        if args.command == "verify":
            return _command_verify(args)
        if args.command == "stop":
            return _command_stop(args)
        if args.command == "auto":
            return _command_auto(args)
        raise DemoPackError(f"unsupported command: {args.command}")
    except (DemoPackError, DemoServerError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _command_start(args: argparse.Namespace) -> int:
    """Implement `start`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    existing_state = load_demo_state(paths.state_path) if paths.state_path.is_file() else None
    if existing_state is not None and existing_state.active:
        print(f"demo already started: {paths.state_path}")
        return 0

    allow_reprovision = existing_state is not None and not existing_state.active
    _prepare_output_root(paths, allow_reprovision=allow_reprovision)
    agent_def_dir = _resolve_agent_def_dir(parameters=parameters, repo_root=repo_root)
    project_fixture = resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)
    env = build_demo_environment(paths=paths)
    api_base_url = f"http://127.0.0.1:{choose_free_loopback_port()}"
    server_state = start_demo_server(
        api_base_url=api_base_url,
        paths=paths,
        env=env,
        timeout_seconds=parameters.server_start_timeout_seconds,
    )
    client = HoumaoServerClient(api_base_url)
    launched_roles: list[str] = []
    try:
        initiator_project = ensure_project_workdir_from_fixture(
            project_fixture=project_fixture,
            project_workdir=paths.initiator_project_dir,
            allow_reprovision=allow_reprovision,
        )
        responder_project = ensure_project_workdir_from_fixture(
            project_fixture=project_fixture,
            project_workdir=paths.responder_project_dir,
            allow_reprovision=allow_reprovision,
        )
        build_suffix = utc_now_iso().replace("-", "").replace(":", "").replace("+00:00", "Z")
        initiator_build = build_participant_brain(
            agent_def_dir=agent_def_dir,
            runtime_root=paths.runtime_root,
            participant=parameters.initiator,
            home_id=f"mail-ping-pong-initiator-{build_suffix}",
        )
        responder_build = build_participant_brain(
            agent_def_dir=agent_def_dir,
            runtime_root=paths.runtime_root,
            participant=parameters.responder,
            home_id=f"mail-ping-pong-responder-{build_suffix}",
        )
        expose_runtime_skills_in_project(
            project_workdir=initiator_project,
            build_result=initiator_build,
        )
        expose_runtime_skills_in_project(
            project_workdir=responder_project,
            build_result=responder_build,
        )
        initiator = launch_participant(
            client=client,
            agent_def_dir=agent_def_dir,
            layout=paths,
            participant=parameters.initiator,
            build_result=initiator_build,
            working_directory=initiator_project,
            role="initiator",
        )
        launched_roles.append("initiator")
        responder = launch_participant(
            client=client,
            agent_def_dir=agent_def_dir,
            layout=paths,
            participant=parameters.responder,
            build_result=responder_build,
            working_directory=responder_project,
            role="responder",
        )
        launched_roles.append("responder")
        initiator = attach_gateway_and_enable_notifier(
            client=client,
            participant=initiator,
            notifier_interval_seconds=parameters.gateway.notifier_interval_seconds,
        )
        responder = attach_gateway_and_enable_notifier(
            client=client,
            participant=responder,
            notifier_interval_seconds=parameters.gateway.notifier_interval_seconds,
        )
        state = DemoState(
            created_at_utc=utc_now_iso(),
            repo_root=repo_root,
            output_root=paths.output_root,
            agent_def_dir=agent_def_dir,
            api_base_url=api_base_url,
            mailbox_root=paths.mailbox_root,
            project_fixture=project_fixture,
            round_limit=parameters.conversation.round_limit,
            wait_defaults=parameters.wait_defaults,
            server=server_state,
            initiator=initiator,
            responder=responder,
        )
        save_demo_state(paths.state_path, state)
    except Exception:
        _best_effort_partial_stop(
            client=client,
            launched_roles=launched_roles,
            initiator=locals().get("initiator"),
            responder=locals().get("responder"),
            server_state=server_state,
            timeout_seconds=parameters.stop_timeout_seconds,
        )
        raise

    print(
        json.dumps({"output_root": str(paths.output_root), "api_base_url": api_base_url}, indent=2)
    )
    return 0


def _command_kickoff(args: argparse.Namespace) -> int:
    """Implement `kickoff`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    if state.kickoff_request is not None and state.thread_key is not None:
        print(f"kickoff already submitted: {state.kickoff_request.request_id}")
        return 0
    thread_key = state.thread_key or _generate_thread_key()
    prompt = _build_kickoff_prompt(parameters=parameters, state=state, thread_key=thread_key)
    client = HoumaoServerClient(state.api_base_url)
    accepted = client.submit_managed_agent_request(
        state.initiator.tracked_agent_id,
        HoumaoManagedAgentSubmitPromptRequest(prompt=prompt),
    )
    kickoff_request = KickoffRequestState(
        submitted_at_utc=utc_now_iso(),
        request_id=accepted.request_id,
        disposition=accepted.disposition,
        headless_turn_id=accepted.headless_turn_id,
        headless_turn_index=accepted.headless_turn_index,
        prompt=prompt,
    )
    updated_state = state.model_copy(
        update={"thread_key": thread_key, "kickoff_request": kickoff_request}
    )
    save_demo_state(paths.state_path, updated_state)
    write_json(
        paths.kickoff_request_path,
        {
            "thread_key": thread_key,
            **kickoff_request.model_dump(mode="json"),
        },
    )
    print(json.dumps({"thread_key": thread_key, "request_id": accepted.request_id}, indent=2))
    return 0


def _command_wait(args: argparse.Namespace) -> int:
    """Implement `wait`."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    timeout_seconds = args.timeout_seconds or state.wait_defaults.timeout_seconds
    poll_interval_seconds = args.poll_interval_seconds or state.wait_defaults.poll_interval_seconds
    deadline = time.monotonic() + timeout_seconds
    last_signature: tuple[int, int, int, int] | None = None
    while True:
        _state = _require_demo_state(paths)
        client = HoumaoServerClient(_state.api_base_url) if _state.active else None
        progress, _inspect, report_payload = _refresh_artifacts(
            paths=paths, state=_state, client=client
        )
        signature = (
            progress.message_count,
            progress.completed_turn_count,
            progress.unread_by_role.get("initiator", 0),
            progress.unread_by_role.get("responder", 0),
        )
        if signature != last_signature:
            print(
                "progress "
                f"messages={progress.message_count}/{progress.expected_messages} "
                f"turns={progress.completed_turn_count}/{progress.expected_turns} "
                f"unread={progress.unread_by_role}"
            )
            last_signature = signature
        if progress.success:
            print(paths.report_path)
            return 0
        if time.monotonic() >= deadline:
            print(
                progress.incomplete_reason or "timed out waiting for completion",
                file=sys.stderr,
            )
            return 1
        time.sleep(poll_interval_seconds)


def _command_pause(args: argparse.Namespace) -> int:
    """Implement `pause`."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    client = HoumaoServerClient(state.api_base_url)
    for participant in (state.initiator, state.responder):
        disable_notifier(client=client, participant=participant)
    print("paused")
    return 0


def _command_continue(args: argparse.Namespace) -> int:
    """Implement `continue`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    client = HoumaoServerClient(state.api_base_url)
    for participant in (state.initiator, state.responder):
        enable_notifier(
            client=client,
            participant=participant,
            notifier_interval_seconds=parameters.gateway.notifier_interval_seconds,
        )
    print("continued")
    return 0


def _command_inspect(args: argparse.Namespace) -> int:
    """Implement `inspect`."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root)
    state = _require_demo_state(paths)
    client = HoumaoServerClient(state.api_base_url) if state.active else None
    _refresh_artifacts(paths=paths, state=state, client=client)
    print(paths.inspect_path)
    return 0


def _command_verify(args: argparse.Namespace) -> int:
    """Implement `verify`."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root)
    expected_report_path = resolve_repo_relative_path(args.expected_report, repo_root=repo_root)
    state = _require_demo_state(paths)
    client = HoumaoServerClient(state.api_base_url) if state.active else None
    progress, _inspect, report_payload = _refresh_artifacts(paths=paths, state=state, client=client)
    sanitized = sanitize_report(report_payload)
    if args.snapshot:
        write_json(expected_report_path, sanitized)
        print(f"snapshot updated: {expected_report_path}")
        return 0
    expected = json.loads(expected_report_path.read_text(encoding="utf-8"))
    if not progress.success:
        raise DemoPackError(progress.incomplete_reason or "demo report is incomplete")
    verify_sanitized_report(sanitized, expected)
    print("verification passed")
    return 0


def _command_stop(args: argparse.Namespace) -> int:
    """Implement `stop`."""

    repo_root = _repo_root()
    parameters = _load_parameters(args, repo_root=repo_root)
    paths = _resolve_paths(args, repo_root=repo_root)
    if not paths.state_path.is_file():
        print("nothing to stop")
        return 0
    state = load_demo_state(paths.state_path)
    client: HoumaoServerClient | None = None
    if state.active:
        client = HoumaoServerClient(state.api_base_url)
        for participant in (state.initiator, state.responder):
            try:
                disable_notifier(client=client, participant=participant)
            except Exception:
                pass
        for participant in (state.initiator, state.responder):
            try:
                stop_participant(client=client, participant=participant)
            except Exception:
                pass
        stop_demo_server(state.server, timeout_seconds=parameters.stop_timeout_seconds)
        state = state.model_copy(update={"active": False, "stopped_at_utc": utc_now_iso()})
        save_demo_state(paths.state_path, state)
    _refresh_artifacts(paths=paths, state=state, client=None)
    print("stopped")
    return 0


def _command_auto(args: argparse.Namespace) -> int:
    """Implement the full automatic walkthrough."""

    repo_root = _repo_root()
    paths = _resolve_paths(args, repo_root=repo_root)
    if not paths.state_path.is_file() or not load_demo_state(paths.state_path).active:
        start_args = argparse.Namespace(
            demo_output_dir=args.demo_output_dir,
            parameters=args.parameters,
        )
        result = _command_start(start_args)
        if result != 0:
            return result
    state = _require_demo_state(paths)
    if state.kickoff_request is None:
        kickoff_args = argparse.Namespace(
            demo_output_dir=args.demo_output_dir,
            parameters=args.parameters,
        )
        result = _command_kickoff(kickoff_args)
        if result != 0:
            return result
    wait_args = argparse.Namespace(
        demo_output_dir=args.demo_output_dir,
        parameters=args.parameters,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    wait_result = _command_wait(wait_args)
    if wait_result != 0:
        return wait_result
    verify_args = argparse.Namespace(
        demo_output_dir=args.demo_output_dir,
        parameters=args.parameters,
        expected_report=args.expected_report,
        snapshot=args.snapshot,
    )
    return _command_verify(verify_args)


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the standard pack arguments to one subcommand parser."""

    parser.add_argument(
        "--demo-output-dir",
        default=DEFAULT_DEMO_OUTPUT_DIR_RELATIVE,
        help="Repository-relative or absolute output root.",
    )
    parser.add_argument(
        "--parameters",
        default=DEFAULT_PARAMETERS_RELATIVE,
        help="Repository-relative or absolute demo-parameters JSON path.",
    )


def _load_parameters(args: argparse.Namespace, *, repo_root: Path):
    """Load tracked demo parameters using repository-relative resolution."""

    parameters_path = resolve_repo_relative_path(args.parameters, repo_root=repo_root)
    return load_demo_parameters(parameters_path)


def _resolve_agent_def_dir(*, parameters, repo_root: Path) -> Path:
    """Resolve the effective agent-definition directory with env override support."""

    env_override = os.environ.get("AGENT_DEF_DIR")
    if env_override is not None and env_override.strip():
        return resolve_repo_relative_path(env_override, repo_root=repo_root)
    return resolve_repo_relative_path(parameters.agent_def_dir, repo_root=repo_root)


def _resolve_paths(args: argparse.Namespace, *, repo_root: Path):
    """Resolve the selected output-root layout."""

    demo_output_dir = resolve_repo_relative_path(args.demo_output_dir, repo_root=repo_root)
    return build_demo_layout(demo_output_dir=demo_output_dir)


def _prepare_output_root(paths, *, allow_reprovision: bool) -> None:
    """Prepare the selected output root for a fresh start."""

    if allow_reprovision and paths.output_root.exists():
        shutil.rmtree(paths.output_root)
    elif paths.output_root.exists() and any(paths.output_root.iterdir()):
        raise DemoPackError(
            "selected demo output root already contains artifacts and is not resumable; "
            "stop the prior run or choose another --demo-output-dir"
        )
    for directory in (
        paths.control_dir,
        paths.server_home_dir,
        paths.server_logs_dir,
        paths.monitor_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def _require_demo_state(paths) -> DemoState:
    """Load one required persisted demo state."""

    if not paths.state_path.is_file():
        raise DemoPackError(f"demo state not found: {paths.state_path}")
    return load_demo_state(paths.state_path)


def _generate_thread_key() -> str:
    """Return one run-specific human-readable thread key."""

    stamp = utc_now_iso().replace("+00:00", "Z").replace(":", "").replace("-", "")
    return f"mail-ping-pong-{stamp}-{uuid.uuid4().hex[:6]}"


def _build_kickoff_prompt(*, parameters, state: DemoState, thread_key: str) -> str:
    """Build the stable kickoff prompt for the initiator."""

    subject = parameters.conversation.subject_template.format(
        thread_key=thread_key,
        round_index=1,
    )
    return "\n".join(
        [
            (
                "Use the runtime-owned mailbox skill document `email-via-filesystem` for all "
                "mailbox actions in this demo."
            ),
            (
                "Open and follow the exact mailbox skill file "
                "`skills/mailbox/email-via-filesystem/SKILL.md` from the project worktree. "
                "The same document may also be mirrored at "
                "`skills/.system/mailbox/email-via-filesystem/SKILL.md`, but prefer the "
                "visible `skills/mailbox/...` path."
            ),
            ("Do not search for that file with `rg`, `find`, or slash-skill lookup first."),
            ("Treat it as a runtime-owned skill document, not as a registered slash skill."),
            (
                "When a live loopback gateway mailbox facade is attached, keep routine mailbox "
                "work on the shared gateway mailbox operations instead of reconstructing "
                "transport-local helper recipes."
            ),
            (
                "Do not inspect repo docs or OpenAPI to rediscover routine shared mailbox "
                "request shapes during this turn."
            ),
            "Stable shared mailbox request shapes for this workflow:",
            (
                "`POST /v1/mail/send` -> "
                '`{"schema_version":1,"to":["recipient@agents.localhost"],'
                '"subject":"...","body_content":"...","attachments":[]}`'
            ),
            (
                "`POST /v1/mail/reply` -> "
                '`{"schema_version":1,"message_ref":"<opaque message_ref>",'
                '"body_content":"...","attachments":[]}`'
            ),
            (
                "`POST /v1/mail/state` -> "
                '`{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}`'
            ),
            f"Start a ping-pong conversation with `{state.responder.mailbox_address}`.",
            f"Thread key: {thread_key}",
            f"Round limit: {state.round_limit}",
            f"Subject template: {parameters.conversation.subject_template}",
            "",
            "Send round 1 now.",
            "Every message you send in this thread must include these exact visible lines near the top:",
            f"Thread-Key: {thread_key}",
            "Round: <current round number>",
            f"Round-Limit: {state.round_limit}",
            "Sender-Role: initiator",
            "Next-Role: responder",
            "",
            "For round 1, use this exact subject:",
            subject,
            "",
            "The responder should reply in the same thread with the current UTC time.",
            (
                "Later wake-up turns will nominate one actionable unread target by shared "
                "`message_ref` and optional `thread_ref`."
            ),
            (
                "Use shared mailbox operations for that later work: inspect the nominated "
                "message, send the next in-thread reply when needed, and mark the processed "
                "source message read through `POST /v1/mail/state` only after success."
            ),
            "If the latest round is below the round limit, send the next round message in the same thread.",
            "If the latest round equals the round limit, stop without sending a new message.",
        ]
    )


def _refresh_artifacts(
    *,
    paths,
    state: DemoState,
    client: HoumaoServerClient | None,
):
    """Refresh events, inspect, and report artifacts for the current run."""

    evidence = collect_conversation_evidence(state)
    progress = build_progress_summary(state, evidence)
    events = build_conversation_events(state, evidence)
    write_json_lines(
        paths.events_path,
        [event.model_dump(mode="json") for event in events],
    )
    inspect_snapshot = build_inspect_snapshot(
        state=state,
        progress=progress,
        events=events,
        client=client,
    )
    write_json(paths.inspect_path, inspect_snapshot.model_dump(mode="json"))
    report = build_report_snapshot(
        state=state,
        paths=paths,
        progress=progress,
        evidence=evidence,
        inspect_snapshot=inspect_snapshot,
    )
    report_payload = report.model_dump(mode="json")
    write_json(paths.report_path, report_payload)
    write_json(paths.sanitized_report_path, sanitize_report(report_payload))
    return progress, inspect_snapshot, report_payload


def _best_effort_partial_stop(
    *,
    client: HoumaoServerClient,
    launched_roles: list[str],
    initiator,
    responder,
    server_state,
    timeout_seconds: float,
) -> None:
    """Best-effort cleanup for failed startup sequences."""

    for role in reversed(launched_roles):
        participant = initiator if role == "initiator" else responder
        try:
            stop_participant(client=client, participant=participant)
        except Exception:
            pass
    stop_demo_server(server_state, timeout_seconds=timeout_seconds)


def _repo_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[4]

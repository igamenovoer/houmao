"""Lifecycle commands and state helpers for the interactive CAO demo."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.realm_controller.agent_identity import (
    normalize_agent_identity_name,
)
from houmao.cao.rest_client import CaoRestClient

from houmao.demo.cao_interactive_demo.brain_recipes import resolve_demo_brain_recipe
from houmao.demo.cao_interactive_demo.cao_server import (
    _ensure_cao_server,
    _write_launcher_config,
)
from houmao.demo.cao_interactive_demo.models import (
    DEFAULT_LIVE_CAO_TIMEOUT_SECONDS,
    DEFAULT_WORKTREE_DIRNAME,
    EMPTY_RESPONSE_ERROR,
    FIXED_CAO_BASE_URL,
    CommandRunner,
    ControlInputRecord,
    DemoEnvironment,
    DemoPaths,
    DemoState,
    DemoWorkflowError,
    TurnRecord,
    VerificationReport,
    VerificationTurnSummary,
)
from houmao.demo.cao_interactive_demo.rendering import (
    _emit_startup_progress,
    _extract_done_message,
    _load_json_file,
    _parse_control_action_summary,
    _parse_events,
    _require_mapping,
    _require_non_empty_string,
    _require_tool,
    _utc_now,
    _validate_model,
    _write_json_file,
)
from houmao.demo.cao_interactive_demo.runtime import (
    _best_effort_tool_state,
    _best_effort_output_text_tail,
    _build_brain,
    _cao_profile_store,
    _kill_tmux_session,
    _resolved_terminal_log_path_for_state,
    _runtime_cli_command,
    _start_runtime_session,
    _stop_remote_session,
    _terminal_log_path,
    _tool_display_name,
)


def start_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    agent_name_override: str | None,
    brain_recipe_selector: str | None,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Start or replace the interactive CAO demo session."""

    _emit_startup_progress("Preparing the interactive demo workspace.")
    _require_tool("pixi")
    _require_tool("tmux")
    _ensure_workspace(paths)
    if env.provision_worktree:
        _emit_startup_progress("Provisioning the default demo git worktree.")
        _provision_default_worktree(paths=paths, env=env, run_command=run_command)

    resolved_recipe = resolve_demo_brain_recipe(
        agent_def_dir=env.agent_def_dir,
        selector=brain_recipe_selector,
    )
    selected_agent_name = agent_name_override or resolved_recipe.default_agent_name
    normalized_identity = normalize_agent_identity_name(selected_agent_name)
    _emit_startup_progress("Resetting any previous interactive demo session state.")
    replaced_agent_identity = _reset_demo_startup_state(
        paths=paths,
        env=env,
        requested_agent_identity=normalized_identity.canonical_name,
        run_command=run_command,
    )

    _reset_demo_artifacts(paths)
    _emit_startup_progress("Writing the fixed-loopback CAO launcher configuration.")
    _write_launcher_config(paths.launcher_config_path, env=env, runtime_root=paths.runtime_root)
    _emit_startup_progress(f"Ensuring local CAO availability at {FIXED_CAO_BASE_URL}.")
    _ensure_cao_server(paths=paths, env=env, run_command=run_command)

    tool_label = _tool_display_name(resolved_recipe.tool)
    _emit_startup_progress(f"Building the interactive {tool_label} runtime brain.")
    build_payload = _build_brain(
        paths=paths,
        env=env,
        recipe_path=resolved_recipe.recipe_path,
        run_command=run_command,
    )
    _emit_startup_progress(
        f"Launching the interactive {tool_label} session and waiting for readiness."
    )
    runtime_payload = _start_runtime_session(
        paths=paths,
        env=env,
        tool=resolved_recipe.tool,
        agent_identity=normalized_identity.canonical_name,
        brain_manifest_path=Path(str(build_payload["manifest_path"])),
        run_command=run_command,
    )
    started_tool = _require_non_empty_string(
        runtime_payload.get("tool"),
        context="start-session output missing tool",
    )
    if started_tool != resolved_recipe.tool:
        raise DemoWorkflowError(
            "start-session output tool did not match the selected brain recipe "
            f"({started_tool!r} != {resolved_recipe.tool!r})."
        )

    session_manifest_path = Path(str(runtime_payload["session_manifest"])).expanduser().resolve()
    manifest_payload = _load_json_file(session_manifest_path, context="session manifest")
    cao_payload = _require_mapping(
        manifest_payload.get("cao"),
        context=f"session manifest `{session_manifest_path}` missing `cao` payload",
    )
    session_name = _require_non_empty_string(
        cao_payload.get("session_name"),
        context="session manifest missing cao.session_name",
    )
    terminal_id = _require_non_empty_string(
        cao_payload.get("terminal_id"),
        context="session manifest missing cao.terminal_id",
    )

    state = DemoState(
        active=True,
        agent_identity=_require_non_empty_string(
            runtime_payload.get("agent_identity"),
            context="start-session output missing agent_identity",
        ),
        tool=resolved_recipe.tool,
        variant_id=resolved_recipe.variant_id,
        brain_recipe=resolved_recipe.canonical_selector,
        session_manifest=str(session_manifest_path),
        session_name=session_name,
        tmux_target=session_name,
        terminal_id=terminal_id,
        terminal_log_path=_terminal_log_path(
            terminal_id,
            launcher_home_dir=env.launcher_home_dir,
        ),
        runtime_root=str(paths.runtime_root),
        workspace_dir=str(paths.workspace_root),
        brain_home=str(Path(str(build_payload["home_path"])).expanduser().resolve()),
        brain_manifest=str(Path(str(build_payload["manifest_path"])).expanduser().resolve()),
        cao_base_url=FIXED_CAO_BASE_URL,
        cao_profile_store=str(_cao_profile_store(env.launcher_home_dir)),
        launcher_config_path=str(paths.launcher_config_path),
        updated_at=_utc_now(),
        turn_count=0,
        control_count=0,
    )
    save_demo_state(paths.state_path, state)
    _write_current_run_root(env.current_run_root_path, paths.workspace_root)
    payload: dict[str, object] = {
        "state": state.model_dump(mode="json"),
        "replaced_previous_agent_identity": replaced_agent_identity,
        "warnings": list(normalized_identity.warnings),
    }
    return payload


def send_turn(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    prompt: str,
    run_command: CommandRunner,
) -> TurnRecord:
    """Send one prompt turn through the persisted interactive session."""

    state = require_active_state(paths.state_path)
    _ensure_workspace(paths)
    turn_index = _next_turn_index(paths)
    started_at_utc = _utc_now()
    stdout_path = paths.turns_dir / f"turn-{turn_index:03d}.events.jsonl"
    stderr_path = paths.turns_dir / f"turn-{turn_index:03d}.stderr.log"

    result = run_command(
        _runtime_cli_command(
            [
                "send-prompt",
                "--agent-identity",
                state.agent_identity,
                "--prompt",
                prompt,
            ]
        ),
        env.repo_root,
        stdout_path,
        stderr_path,
        env.timeout_seconds,
    )
    completed_at_utc = _utc_now()
    events = _parse_events(stdout=result.stdout)
    response_text = _extract_done_message(events)
    turn = TurnRecord(
        turn_index=turn_index,
        agent_identity=state.agent_identity,
        prompt=prompt,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        exit_status=result.returncode,
        response_text=response_text,
        events=events,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )
    _write_json_file(paths.turns_dir / f"turn-{turn_index:03d}.json", turn.model_dump(mode="json"))

    if result.returncode != 0:
        raise DemoWorkflowError(
            f"send-turn failed via `realm_controller send-prompt` (see `{stderr_path}`)"
        )
    if not response_text.strip():
        raise DemoWorkflowError(EMPTY_RESPONSE_ERROR)

    updated_state = state.model_copy(
        update={
            "updated_at": completed_at_utc,
            "turn_count": turn_index,
        }
    )
    save_demo_state(paths.state_path, updated_state)
    return turn


def send_control_input(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    key_stream: str,
    as_raw_string: bool,
    run_command: CommandRunner,
) -> ControlInputRecord:
    """Send one raw control-input sequence through the persisted interactive session."""

    state = require_active_state(paths.state_path, command_name="send-keys")
    _ensure_workspace(paths)
    control_index = _next_control_index(paths)
    started_at_utc = _utc_now()
    stdout_path = paths.controls_dir / f"control-{control_index:03d}.stdout.json"
    stderr_path = paths.controls_dir / f"control-{control_index:03d}.stderr.log"

    runtime_args = [
        "send-keys",
        "--agent-identity",
        state.agent_identity,
        "--sequence",
        key_stream,
    ]
    if as_raw_string:
        runtime_args.append("--escape-special-keys")

    result = run_command(
        _runtime_cli_command(runtime_args),
        env.repo_root,
        stdout_path,
        stderr_path,
        env.timeout_seconds,
    )
    completed_at_utc = _utc_now()
    control_result = _parse_control_action_summary(
        result.stdout,
        context="send-keys output",
    )
    record = ControlInputRecord(
        control_index=control_index,
        agent_identity=state.agent_identity,
        key_stream=key_stream,
        as_raw_string=as_raw_string,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        exit_status=result.returncode,
        result=control_result,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )
    _write_json_file(
        paths.controls_dir / f"control-{control_index:03d}.json",
        record.model_dump(mode="json"),
    )

    if result.returncode != 0 or control_result.status != "ok":
        raise DemoWorkflowError(
            f"send-keys failed via `realm_controller send-keys` (see `{stderr_path}`)"
        )

    updated_state = state.model_copy(
        update={
            "updated_at": completed_at_utc,
            "control_count": control_index,
        }
    )
    save_demo_state(paths.state_path, updated_state)
    return record


def inspect_demo(
    *,
    paths: DemoPaths,
    as_json: bool,
    output_text_tail_chars: int | None = None,
) -> None:
    """Render stored inspection metadata for the active or latest session."""

    from houmao.demo.cao_interactive_demo.rendering import (
        _print_json,
        _render_human_inspect_output,
    )

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError(
            "No interactive demo state was found. Run `start` before `inspect`."
        )

    terminal_log_path = _resolved_terminal_log_path_for_state(state)
    client = CaoRestClient(
        state.cao_base_url,
        timeout_seconds=DEFAULT_LIVE_CAO_TIMEOUT_SECONDS,
    )
    payload: dict[str, object] = {
        "active": state.active,
        "session_status": "active" if state.active else "inactive",
        "agent_identity": state.agent_identity,
        "session_name": state.session_name,
        "tool": state.tool,
        "variant_id": state.variant_id,
        "brain_recipe": state.brain_recipe,
        "tool_state": _best_effort_tool_state(
            terminal_id=state.terminal_id,
            client=client,
        ),
        "session_manifest": state.session_manifest,
        "tmux_target": state.tmux_target,
        "tmux_attach_command": f"tmux attach -t {state.tmux_target}",
        "terminal_id": state.terminal_id,
        "terminal_log_path": terminal_log_path,
        "terminal_log_tail_command": f"tail -f {terminal_log_path}",
        "workspace_dir": state.workspace_dir,
        "runtime_root": state.runtime_root,
        "updated_at": state.updated_at,
    }
    if output_text_tail_chars is not None:
        output_text_tail = _best_effort_output_text_tail(
            tool=state.tool,
            terminal_id=state.terminal_id,
            output_text_tail_chars=output_text_tail_chars,
            client=client,
        )
        payload["output_text_tail_chars_requested"] = output_text_tail_chars
        payload["output_text_tail"] = output_text_tail.output_text_tail
        if output_text_tail.note is not None:
            payload["output_text_tail_note"] = output_text_tail.note
    if as_json:
        _print_json(payload)
        return

    print(_render_human_inspect_output(payload=payload))


def verify_demo(*, paths: DemoPaths) -> VerificationReport:
    """Generate a verification report from persisted turn artifacts."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError("No interactive demo state was found. Run `start` before `verify`.")

    turn_records = load_turn_records(paths.turns_dir)
    if len(turn_records) < 2:
        raise DemoWorkflowError(
            "Verification requires at least two recorded turns in the current workspace."
        )

    agent_identities = {record.agent_identity for record in turn_records}
    if len(agent_identities) != 1:
        raise DemoWorkflowError(
            "Verification expected exactly one reused agent_identity across recorded turns."
        )

    summaries: list[VerificationTurnSummary] = []
    for record in turn_records:
        if record.exit_status != 0:
            raise DemoWorkflowError(
                f"Turn {record.turn_index} exited non-zero ({record.exit_status})."
            )
        if not record.response_text.strip():
            raise DemoWorkflowError(f"Turn {record.turn_index} has an empty response_text.")
        summaries.append(
            VerificationTurnSummary(
                turn_index=record.turn_index,
                agent_identity=record.agent_identity,
                exit_status=record.exit_status,
                response_text=record.response_text,
            )
        )

    report = VerificationReport(
        status="ok",
        backend="cao_rest",
        tool=state.tool,
        variant_id=state.variant_id,
        brain_recipe=state.brain_recipe,
        cao_base_url=state.cao_base_url,
        agent_identity=state.agent_identity,
        unique_agent_identity_count=len(agent_identities),
        turn_count=len(summaries),
        turns=summaries,
        session_manifest=state.session_manifest,
        workspace_dir=state.workspace_dir,
        tmux_target=state.tmux_target,
        terminal_id=state.terminal_id,
        terminal_log_path=_resolved_terminal_log_path_for_state(state),
        generated_at_utc=_utc_now(),
    )
    _write_json_file(paths.report_path, report.model_dump(mode="json"))
    return report


def stop_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> dict[str, object]:
    """Stop the active interactive demo session and mark local state inactive."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError("No interactive demo state was found. Run `start` before `stop`.")
    if not state.active:
        raise DemoWorkflowError("Interactive demo state is already inactive.")

    result = _stop_remote_session(
        paths=paths,
        env=env,
        agent_identity=state.agent_identity,
        run_command=run_command,
        tolerate_stale=True,
        log_prefix="stop",
    )
    # A dead remote session may still leave the local tmux session behind, so
    # stop always performs the best-effort tmux cleanup step before inactivating
    # the persisted demo state.
    _kill_tmux_session(
        paths=paths,
        env=env,
        session_name=state.session_name,
        run_command=run_command,
    )
    inactive_state = state.model_copy(update={"active": False, "updated_at": _utc_now()})
    save_demo_state(paths.state_path, inactive_state)
    return {
        "state": inactive_state.model_dump(mode="json"),
        "stop_result": {
            "returncode": result.returncode,
            "stdout_path": str(result.stdout_path),
            "stderr_path": str(result.stderr_path),
            "stale_session_tolerated": bool(result.returncode != 0),
        },
    }


def load_demo_state(path: Path) -> DemoState | None:
    """Load demo state from disk when it exists."""

    if not path.is_file():
        return None
    payload = _load_json_file(path, context="demo state")
    return _validate_model(DemoState, payload, source=str(path))


def save_demo_state(path: Path, state: DemoState) -> None:
    """Persist demo state to disk."""

    _write_json_file(path, state.model_dump(mode="json"))


def load_turn_records(turns_dir: Path) -> list[TurnRecord]:
    """Load all persisted turn records sorted by turn index."""

    if not turns_dir.exists():
        return []

    records: list[TurnRecord] = []
    for path in sorted(turns_dir.glob("turn-*.json")):
        payload = _load_json_file(path, context="turn record")
        records.append(_validate_model(TurnRecord, payload, source=str(path)))
    return sorted(records, key=lambda record: record.turn_index)


def load_control_records(controls_dir: Path) -> list[ControlInputRecord]:
    """Load all persisted control-input records sorted by control index."""

    if not controls_dir.exists():
        return []

    records: list[ControlInputRecord] = []
    for path in sorted(controls_dir.glob("control-[0-9][0-9][0-9].json")):
        payload = _load_json_file(path, context="control input record")
        records.append(_validate_model(ControlInputRecord, payload, source=str(path)))
    return sorted(records, key=lambda record: record.control_index)


def require_active_state(path: Path, *, command_name: str = "send-turn") -> DemoState:
    """Return the active demo state or raise an actionable workflow error."""

    state = load_demo_state(path)
    if state is None or not state.active:
        raise DemoWorkflowError(
            f"No active interactive session exists. Run `start` before `{command_name}`."
        )
    return state


def _ensure_workspace(paths: DemoPaths) -> None:
    """Create the stable demo workspace directories."""

    paths.workspace_root.mkdir(parents=True, exist_ok=True)
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.turns_dir.mkdir(parents=True, exist_ok=True)
    paths.controls_dir.mkdir(parents=True, exist_ok=True)


def _reset_demo_artifacts(paths: DemoPaths) -> None:
    """Remove per-run turn, control, and report artifacts before a fresh start."""

    if paths.turns_dir.exists():
        shutil.rmtree(paths.turns_dir)
    paths.turns_dir.mkdir(parents=True, exist_ok=True)
    if paths.controls_dir.exists():
        shutil.rmtree(paths.controls_dir)
    paths.controls_dir.mkdir(parents=True, exist_ok=True)
    if paths.report_path.exists():
        paths.report_path.unlink()


def _provision_default_worktree(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    run_command: CommandRunner,
) -> None:
    """Create the default git worktree used as the demo session workdir."""

    if env.workdir.exists():
        git_dir = env.workdir / ".git"
        if git_dir.exists():
            return
        raise DemoWorkflowError(
            f"Default demo workdir already exists and is not a git worktree: `{env.workdir}`."
        )

    env.workdir.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(
        ["git", "worktree", "add", "--detach", str(env.workdir), "HEAD"],
        env.repo_root,
        paths.logs_dir / "provision-worktree.stdout",
        paths.logs_dir / "provision-worktree.stderr",
        env.timeout_seconds,
    )
    if result.returncode != 0:
        raise DemoWorkflowError(
            f"Failed to provision the default demo git worktree (see `{result.stderr_path}`)."
        )


def _reset_demo_startup_state(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    requested_agent_identity: str,
    run_command: CommandRunner,
) -> str | None:
    """Reset prior tutorial state so startup behaves like a fresh run."""

    previous_paths, previous_state, previous_is_stale = _load_previous_demo_state_for_startup(
        env.current_run_root_path
    )
    current_state, current_is_stale = _load_demo_state_for_startup(paths.state_path)

    cleanup_agent_identities = [requested_agent_identity]
    cleanup_session_names = [requested_agent_identity]
    replaced_agent_identity: str | None = None

    for candidate_state in (previous_state, current_state):
        if candidate_state is None or not candidate_state.active:
            continue
        cleanup_agent_identities.append(candidate_state.agent_identity)
        cleanup_session_names.append(candidate_state.session_name)
        if replaced_agent_identity is None:
            replaced_agent_identity = candidate_state.agent_identity

    for index, agent_identity in enumerate(
        _dedup_preserve_order(cleanup_agent_identities), start=1
    ):
        _stop_remote_session(
            paths=paths,
            env=env,
            agent_identity=agent_identity,
            run_command=run_command,
            tolerate_stale=True,
            log_prefix=f"replacement-stop-{index}",
        )

    for session_name in _dedup_preserve_order(cleanup_session_names):
        _kill_tmux_session(
            paths=paths,
            env=env,
            session_name=session_name,
            run_command=run_command,
        )

    if previous_paths is not None:
        if previous_state is not None:
            _reset_demo_artifacts(previous_paths)
            _mark_state_inactive(previous_paths.state_path, previous_state)
        elif previous_is_stale:
            _reset_demo_artifacts(previous_paths)
            _remove_stale_state_file(previous_paths.state_path)

    if current_state is not None:
        _mark_state_inactive(paths.state_path, current_state)
    elif current_is_stale:
        _remove_stale_state_file(paths.state_path)

    return replaced_agent_identity


def _load_previous_demo_state_for_startup(
    current_run_root_path: Path,
) -> tuple[DemoPaths | None, DemoState | None, bool]:
    """Load the previously recorded demo state for startup cleanup.

    Returns
    -------
    tuple[DemoPaths | None, DemoState | None, bool]
        Resolved prior workspace paths when available, the validated state when
        it can be loaded, and a stale-state flag when the file exists but is no
        longer compatible with the current schema.
    """

    previous_workspace_root = _read_current_run_root(current_run_root_path)
    if previous_workspace_root is None:
        return (None, None, False)

    previous_paths = DemoPaths.from_workspace_root(previous_workspace_root)
    previous_state, previous_is_stale = _load_demo_state_for_startup(previous_paths.state_path)
    return (previous_paths, previous_state, previous_is_stale)


def _load_demo_state_for_startup(path: Path) -> tuple[DemoState | None, bool]:
    """Load state for startup and classify incompatible files as stale local state."""

    if not path.is_file():
        return (None, False)

    try:
        return (load_demo_state(path), False)
    except DemoWorkflowError:
        return (None, True)


def _mark_state_inactive(path: Path, state: DemoState) -> None:
    """Persist an inactive copy of demo state after cleanup or aborted startup."""

    if state.active:
        save_demo_state(path, state.model_copy(update={"active": False, "updated_at": _utc_now()}))


def _remove_stale_state_file(path: Path) -> None:
    """Delete an incompatible persisted state file before writing fresh startup state."""

    if path.exists():
        path.unlink()


def _dedup_preserve_order(values: list[str]) -> list[str]:
    """Return values without duplicates while preserving first-seen order."""

    return list(dict.fromkeys(value for value in values if value.strip()))


def _next_turn_index(paths: DemoPaths) -> int:
    """Return the next sequential turn index for the workspace."""

    existing = load_turn_records(paths.turns_dir)
    if not existing:
        return 1
    return max(record.turn_index for record in existing) + 1


def _next_control_index(paths: DemoPaths) -> int:
    """Return the next sequential control-input index for the workspace."""

    existing = load_control_records(paths.controls_dir)
    if not existing:
        return 1
    return max(record.control_index for record in existing) + 1


def _read_current_run_root(path: Path) -> Path | None:
    """Read the recorded current-run workspace root when available."""

    if not path.is_file():
        return None
    raw_value = path.read_text(encoding="utf-8").strip()
    if not raw_value:
        return None
    resolved = Path(raw_value).expanduser().resolve()
    if not resolved.exists():
        return None
    return resolved


def _write_current_run_root(path: Path, workspace_root: Path) -> None:
    """Persist the latest workspace root used by wrapper-driven follow-up commands."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{workspace_root}\n", encoding="utf-8")


def _latest_demo_run_root(demo_base_root: Path) -> Path | None:
    """Return the newest demo run directory under the default demo root."""

    if not demo_base_root.exists():
        return None
    candidates = sorted(
        (
            path
            for path in demo_base_root.iterdir()
            if path.is_dir() and path.name != DEFAULT_WORKTREE_DIRNAME
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _run_timestamp_slug() -> str:
    """Return a filesystem-safe UTC slug for per-run demo roots."""

    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%fZ")

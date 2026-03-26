"""Lifecycle commands for the interactive full-pipeline demo."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Literal

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.native_launch_resolver import resolve_native_launch_target
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.runtime import resume_runtime_session, start_runtime_session
from houmao.demo.houmao_server_interactive_full_pipeline_demo.models import (
    DEFAULT_AGENT_PROFILE,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_WORKTREE_DIRNAME,
    DemoEnvironment,
    DemoPaths,
    DemoRequestRecord,
    DemoState,
    DemoWorkflowError,
    InspectPayload,
    ManagedAgentHistorySnapshot,
    ManagedAgentSnapshot,
    STALE_STOP_MARKERS,
    StartupPayload,
    StopPayload,
    TerminalSnapshot,
    TurnArtifact,
    VerificationReport,
    VerificationRequestSummary,
    tool_for_provider,
)
from houmao.owned_paths import (
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
    AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.server.models import (
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoTerminalStateResponse,
)
from houmao.srv_ctrl.commands.managed_agents import (
    _local_tui_runtime_for_controller,
    interrupt_managed_agent,
    managed_agent_detail_payload,
    managed_agent_history_payload,
    managed_agent_state_payload,
    prompt_managed_agent,
    resolve_managed_agent_target,
)


def start_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    provider: str,
    requested_session_name: str | None,
) -> StartupPayload:
    """Start or replace the interactive demo run."""

    resolved_tool = tool_for_provider(provider)
    _ensure_workspace(paths)
    replaced_previous_session_name = _cleanup_existing_state_for_startup(paths=paths, env=env)
    if env.provision_worktree:
        _provision_default_worktree(paths=paths, repo_root=env.repo_root)
    _reset_demo_artifacts(paths)
    _reset_runtime_ownership_roots(paths)

    agent_def_dir = _demo_agent_def_dir_path(env.repo_root)
    if not agent_def_dir.is_dir():
        raise DemoWorkflowError(
            f"Tracked demo-local agent-definition root not found: {agent_def_dir}"
        )

    agent_name = _launch_agent_name(
        requested_session_name=requested_session_name,
        resolved_tool=resolved_tool,
    )
    runtime_env = _demo_environment(paths=paths, agent_def_dir=agent_def_dir)
    controller = None
    try:
        with _temporary_environment_bindings(runtime_env):
            target = resolve_native_launch_target(
                selector=DEFAULT_AGENT_PROFILE,
                provider=provider,
                working_directory=paths.workdir,
            )
            build_result = build_brain_home(
                BuildRequest(
                    agent_def_dir=target.agent_def_dir,
                    runtime_root=paths.runtime_root,
                    tool=target.recipe.tool,
                    skills=target.recipe.skills,
                    config_profile=target.recipe.config_profile,
                    credential_profile=target.recipe.credential_profile,
                    recipe_path=target.recipe_path,
                    recipe_launch_overrides=target.recipe.launch_overrides,
                    operator_prompt_mode=target.recipe.operator_prompt_mode,
                    mailbox=target.recipe.mailbox,
                    agent_name=agent_name,
                )
            )
            resolved_backend = backend_for_tool(target.tool, prefer_local_interactive=True)
            controller = start_runtime_session(
                agent_def_dir=target.agent_def_dir,
                brain_manifest_path=build_result.manifest_path.resolve(),
                role_name=target.role_name,
                runtime_root=paths.runtime_root,
                backend=resolved_backend,
                working_directory=paths.workdir,
                agent_name=agent_name,
                tmux_session_name=requested_session_name,
            )
        assert controller is not None
        _wait_for_controller_launch_readiness(controller=controller, env=env)
    except Exception as exc:
        if controller is not None:
            _best_effort_stop_controller(controller=controller, runtime_env=runtime_env)
        if isinstance(exc, DemoWorkflowError):
            raise
        raise DemoWorkflowError(str(exc)) from exc

    if controller.agent_identity is None:
        raise DemoWorkflowError("Local interactive launch did not publish a managed-agent name.")
    if controller.agent_id is None:
        raise DemoWorkflowError("Local interactive launch did not publish an authoritative agent_id.")
    if controller.tmux_session_name is None:
        raise DemoWorkflowError("Local interactive launch did not publish a tmux session name.")

    state = DemoState(
        active=True,
        provider=provider,
        tool=resolved_tool,
        agent_profile=DEFAULT_AGENT_PROFILE,
        variant_id=_variant_id(resolved_tool),
        agent_name=controller.agent_identity,
        agent_id=controller.agent_id,
        requested_session_name=requested_session_name,
        tmux_session_name=controller.tmux_session_name,
        tracked_agent_id=None,
        session_manifest_path=str(controller.manifest_path),
        session_root=str(controller.manifest_path.parent.resolve()),
        runtime_root=str(paths.runtime_root),
        registry_root=str(paths.registry_root),
        jobs_root=str(paths.jobs_root),
        workspace_dir=str(paths.workspace_root),
        workdir=str(paths.workdir),
        agent_def_dir=str(agent_def_dir),
        updated_at=_utc_now(),
        prompt_turn_count=0,
        interrupt_count=0,
    )
    save_demo_state(paths.state_path, state)
    _write_current_run_root(env.current_run_root_path, paths.workspace_root)
    return StartupPayload(
        state=state,
        replaced_previous_session_name=replaced_previous_session_name,
    )


def inspect_demo(
    *,
    paths: DemoPaths,
    dialog_tail_chars: int | None = None,
) -> InspectPayload:
    """Inspect persisted demo state plus live local state when available."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError(
            "No interactive demo state was found. Run `start` before `inspect`."
        )

    live_error: str | None = None
    managed_agent: ManagedAgentSnapshot | None = None
    history: ManagedAgentHistorySnapshot | None = None
    terminal: TerminalSnapshot | None = None
    dialog_tail: str | None = None
    tracked_agent_id = state.tracked_agent_id
    if state.active:
        try:
            live_bundle = _fetch_live_bundle(state=state)
            managed_agent = _managed_agent_snapshot(
                state_response=live_bundle["state"],
                detail_response=live_bundle["detail"],
            )
            tracked_agent_id = managed_agent.tracked_agent_id
            history = _history_snapshot(live_bundle["history"])
            terminal_response = live_bundle["terminal"]
            terminal = (
                _terminal_snapshot(terminal_response) if terminal_response is not None else None
            )
            if dialog_tail_chars is not None and terminal_response is not None:
                dialog_tail = _dialog_tail_from_terminal_state(
                    terminal_state=terminal_response,
                    dialog_tail_chars=dialog_tail_chars,
                )
        except Exception as exc:
            live_error = str(exc)
    else:
        live_error = "Demo state is inactive; local managed-agent inspection skipped."

    return InspectPayload(
        active=state.active,
        provider=state.provider,
        tool=state.tool,
        agent_profile=state.agent_profile,
        variant_id=state.variant_id,
        agent_name=state.agent_name,
        agent_id=state.agent_id,
        requested_session_name=state.requested_session_name,
        tmux_session_name=state.tmux_session_name,
        tracked_agent_id=tracked_agent_id,
        workspace_dir=state.workspace_dir,
        workdir=state.workdir,
        session_manifest_path=state.session_manifest_path,
        updated_at=state.updated_at,
        managed_agent=managed_agent,
        history=history,
        terminal=terminal,
        dialog_tail=dialog_tail,
        dialog_tail_chars_requested=dialog_tail_chars,
        live_error=live_error,
    )


def send_turn(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    prompt: str,
) -> TurnArtifact:
    """Submit one prompt through the local managed-agent control surface."""

    if not prompt.strip():
        raise DemoWorkflowError("Prompt text must not be empty.")
    return _submit_request_artifact(
        paths=paths,
        env=env,
        artifact_kind="send-turn",
        request_kind="submit_prompt",
        prompt=prompt,
    )


def interrupt_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
) -> TurnArtifact:
    """Submit one interrupt through the local managed-agent control surface."""

    return _submit_request_artifact(
        paths=paths,
        env=env,
        artifact_kind="interrupt",
        request_kind="interrupt",
        prompt=None,
    )


def verify_demo(*, paths: DemoPaths) -> VerificationReport:
    """Build one sanitized verification report from artifacts and live local state."""

    state = load_demo_state(paths.state_path)
    if state is None:
        raise DemoWorkflowError("No interactive demo state was found. Run `start` before `verify`.")

    prompt_artifacts = load_turn_artifacts(paths.turns_dir)
    interrupt_artifacts = load_interrupt_artifacts(paths.interrupts_dir)
    if not prompt_artifacts:
        raise DemoWorkflowError("Verification requires at least one accepted prompt artifact.")

    combined_artifacts = sorted(
        [*prompt_artifacts, *interrupt_artifacts],
        key=lambda artifact: artifact.requested_at_utc,
    )
    request_summaries = [_verification_request_summary(artifact) for artifact in combined_artifacts]

    evidence_source: Literal["live_local", "captured_artifacts"] = "captured_artifacts"
    current_managed_agent = combined_artifacts[-1].state_after
    current_history = combined_artifacts[-1].history_after
    current_terminal = combined_artifacts[-1].terminal_after
    tracked_agent_id = combined_artifacts[-1].tracked_agent_id
    if state.active:
        try:
            live_bundle = _fetch_live_bundle(state=state)
            current_managed_agent = _managed_agent_snapshot(
                state_response=live_bundle["state"],
                detail_response=live_bundle["detail"],
            )
            tracked_agent_id = current_managed_agent.tracked_agent_id
            current_history = _history_snapshot(live_bundle["history"])
            terminal_response = live_bundle["terminal"]
            current_terminal = (
                _terminal_snapshot(terminal_response) if terminal_response is not None else None
            )
            evidence_source = "live_local"
        except Exception:
            evidence_source = "captured_artifacts"

    if (
        current_history.entry_count == 0
        and not any(artifact.state_change_observed for artifact in prompt_artifacts)
        and current_managed_agent.last_turn_result == "none"
    ):
        raise DemoWorkflowError(
            "Verification requires tracked local evidence beyond accepted request records."
        )

    report = VerificationReport(
        status="ok",
        evidence_source=evidence_source,
        provider=state.provider,
        tool=state.tool,
        agent_profile=state.agent_profile,
        variant_id=state.variant_id,
        agent_name=state.agent_name,
        agent_id=state.agent_id,
        requested_session_name=state.requested_session_name,
        tmux_session_name=state.tmux_session_name,
        tracked_agent_id=tracked_agent_id,
        session_manifest_path=state.session_manifest_path,
        workspace_dir=state.workspace_dir,
        workdir=state.workdir,
        accepted_prompt_count=len(prompt_artifacts),
        accepted_interrupt_count=len(interrupt_artifacts),
        request_summaries=request_summaries,
        current_managed_agent=current_managed_agent,
        current_history=current_history,
        current_terminal=current_terminal,
        generated_at_utc=_utc_now(),
    )
    _write_json_file(paths.report_path, report.model_dump(mode="json"))
    return report


def stop_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
) -> StopPayload:
    """Stop the active interactive demo session and deactivate local state."""

    state = require_active_state(paths.state_path, command_name="stop")
    stop_status, stale_tolerated = _stop_live_state(
        state=state,
        tolerate_stale=True,
    )
    inactive_state = state.model_copy(update={"active": False, "updated_at": _utc_now()})
    save_demo_state(paths.state_path, inactive_state)
    _write_current_run_root(env.current_run_root_path, paths.workspace_root)
    return StopPayload(
        state=inactive_state,
        stop_status=stop_status,
        stale_session_tolerated=stale_tolerated,
    )


def load_demo_state(path: Path) -> DemoState | None:
    """Load persisted demo state when it exists."""

    if not path.is_file():
        return None
    payload = _load_json_file(path, context="demo state")
    try:
        return DemoState.model_validate(payload)
    except Exception as exc:
        raise DemoWorkflowError(f"Invalid demo state at `{path}`: {exc}") from exc


def save_demo_state(path: Path, state: DemoState) -> None:
    """Persist demo state to disk."""

    _write_json_file(path, state.model_dump(mode="json"))


def load_turn_artifacts(turns_dir: Path) -> list[TurnArtifact]:
    """Load all persisted prompt artifacts sorted by sequence number."""

    return _load_artifacts(pattern="turn-*.json", root=turns_dir)


def load_interrupt_artifacts(interrupts_dir: Path) -> list[TurnArtifact]:
    """Load all persisted interrupt artifacts sorted by sequence number."""

    return _load_artifacts(pattern="interrupt-*.json", root=interrupts_dir)


def require_active_state(path: Path, *, command_name: str) -> DemoState:
    """Return the active demo state or raise an actionable workflow error."""

    state = load_demo_state(path)
    if state is None or not state.active:
        raise DemoWorkflowError(
            f"No active interactive session exists. Run `start` before `{command_name}`."
        )
    return state


def _ensure_workspace(paths: DemoPaths) -> None:
    """Create the stable demo workspace directories."""

    for path in (
        paths.workspace_root,
        paths.logs_dir,
        paths.turns_dir,
        paths.interrupts_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def _reset_demo_artifacts(paths: DemoPaths) -> None:
    """Remove per-run artifacts before a fresh startup."""

    for directory in (paths.turns_dir, paths.interrupts_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    if paths.report_path.exists():
        paths.report_path.unlink()


def _reset_runtime_ownership_roots(paths: DemoPaths) -> None:
    """Recreate run-owned runtime, registry, and jobs roots from scratch."""

    for directory in (paths.runtime_root, paths.registry_root, paths.jobs_root):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)


def _provision_default_worktree(*, paths: DemoPaths, repo_root: Path) -> None:
    """Create the default git worktree used as the demo session workdir."""

    if paths.workdir.exists():
        if (paths.workdir / ".git").exists():
            return
        raise DemoWorkflowError(
            f"Default demo workdir already exists and is not a git worktree: `{paths.workdir}`."
        )

    paths.workdir.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", "--detach", str(paths.workdir), "HEAD"],
        cwd=str(repo_root),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise DemoWorkflowError(
            f"Failed to provision the default demo git worktree via `git worktree add`: {detail}"
        )


def _cleanup_existing_state_for_startup(*, paths: DemoPaths, env: DemoEnvironment) -> str | None:
    """Stop the pointer-selected or explicit active run before startup continues."""

    replaced_previous_session_name: str | None = None
    candidate_roots: list[Path] = []
    previous_root = _read_current_run_root(env.current_run_root_path)
    if previous_root is not None:
        candidate_roots.append(previous_root)
    candidate_roots.append(paths.workspace_root)

    seen_roots: set[Path] = set()
    for candidate_root in candidate_roots:
        resolved_root = candidate_root.resolve()
        if resolved_root in seen_roots:
            continue
        seen_roots.add(resolved_root)
        candidate_paths = DemoPaths.from_workspace_root(resolved_root)
        state, stale = _load_demo_state_for_startup(candidate_paths.state_path)
        if stale:
            _remove_stale_state_file(candidate_paths.state_path)
            continue
        if state is None or not state.active:
            continue
        if replaced_previous_session_name is None:
            replaced_previous_session_name = state.tmux_session_name
        _stop_live_state(
            state=state,
            tolerate_stale=True,
        )
        _mark_state_inactive(candidate_paths.state_path, state)
    return replaced_previous_session_name


def _load_demo_state_for_startup(path: Path) -> tuple[DemoState | None, bool]:
    """Load demo state for startup and classify incompatible files as stale."""

    if not path.is_file():
        return (None, False)
    try:
        return (load_demo_state(path), False)
    except DemoWorkflowError:
        return (None, True)


def _mark_state_inactive(path: Path, state: DemoState) -> None:
    """Persist an inactive copy of demo state after cleanup."""

    if state.active:
        save_demo_state(path, state.model_copy(update={"active": False, "updated_at": _utc_now()}))


def _remove_stale_state_file(path: Path) -> None:
    """Delete an incompatible persisted state file before fresh startup."""

    if path.exists():
        path.unlink()


def _launch_agent_name(*, requested_session_name: str | None, resolved_tool: str) -> str:
    """Resolve the friendly managed-agent name used for the local launch."""

    if requested_session_name is not None and requested_session_name.strip():
        return requested_session_name.strip()
    return _variant_id(resolved_tool)


def _variant_id(resolved_tool: str) -> str:
    """Return the stable demo variant identifier."""

    return f"{resolved_tool}-{DEFAULT_AGENT_PROFILE}"


def _demo_environment(*, paths: DemoPaths, agent_def_dir: Path) -> dict[str, str]:
    """Return the run-local environment used for registry and runtime ownership."""

    return {
        AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR: str(paths.runtime_root.resolve()),
        AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR: str(paths.registry_root.resolve()),
        AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR: str(paths.jobs_root.resolve()),
        AGENT_DEF_DIR_ENV_VAR: str(agent_def_dir.resolve()),
    }


def _state_environment(state: DemoState) -> dict[str, str]:
    """Return the run-local environment reconstructed from persisted state."""

    return {
        AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR: str(Path(state.runtime_root).expanduser().resolve()),
        AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR: str(Path(state.registry_root).expanduser().resolve()),
        AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR: str(Path(state.jobs_root).expanduser().resolve()),
        AGENT_DEF_DIR_ENV_VAR: str(Path(state.agent_def_dir).expanduser().resolve()),
    }


@contextmanager
def _temporary_environment_bindings(overrides: dict[str, str]) -> Iterator[None]:
    """Temporarily apply environment overrides for one bounded block."""

    previous: dict[str, str | None] = {name: os.environ.get(name) for name in overrides}
    for name, value in overrides.items():
        os.environ[name] = value
    try:
        yield
    finally:
        for name, previous_value in previous.items():
            if previous_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous_value


def _wait_for_controller_launch_readiness(*, controller: Any, env: DemoEnvironment) -> None:
    """Wait for the local TUI session to become available and ready."""

    runtime = _local_tui_runtime_for_controller(controller)
    poll_interval = env.request_poll_interval_seconds

    shell_deadline = time.monotonic() + env.compat_shell_ready_timeout_seconds
    last_error = "local tracked session did not become available"
    while time.monotonic() < shell_deadline:
        try:
            tracked_state = runtime.refresh_once()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(poll_interval)
            continue
        if tracked_state.diagnostics.availability == "available":
            break
        last_error = (
            "availability="
            f"{tracked_state.diagnostics.availability} "
            f"transport_state={tracked_state.diagnostics.transport_state} "
            f"process_state={tracked_state.diagnostics.process_state}"
        )
        time.sleep(poll_interval)
    else:
        raise DemoWorkflowError(
            "Timed out waiting for the local interactive session shell to become available: "
            f"{last_error}"
        )

    provider_deadline = time.monotonic() + env.compat_provider_ready_timeout_seconds
    last_error = "tracked terminal did not reach ready posture"
    while time.monotonic() < provider_deadline:
        try:
            tracked_state = runtime.refresh_once()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(poll_interval)
            continue
        if tracked_state.surface.ready_posture == "yes":
            if controller.launch_plan.tool == "codex" and env.compat_codex_warmup_seconds > 0:
                time.sleep(env.compat_codex_warmup_seconds)
            return
        last_error = (
            f"ready_posture={tracked_state.surface.ready_posture} "
            f"turn_phase={tracked_state.turn.phase}"
        )
        time.sleep(poll_interval)
    raise DemoWorkflowError(
        "Timed out waiting for the local interactive provider to become ready: "
        f"{last_error}"
    )


def _resolve_local_target(state: DemoState) -> Any:
    """Resolve the persisted managed agent through the run-local registry."""

    with _temporary_environment_bindings(_state_environment(state)):
        target = resolve_managed_agent_target(
            agent_id=state.agent_id,
            agent_name=None,
            port=None,
        )
    if target.mode != "local":
        raise DemoWorkflowError(
            "Demo state unexpectedly resolved to a non-local managed-agent target."
        )
    if target.identity.transport != "tui":
        raise DemoWorkflowError("Demo state unexpectedly resolved to a non-TUI managed-agent target.")
    return target


def _resume_local_controller(state: DemoState) -> Any:
    """Resume the local runtime controller directly from persisted manifest metadata."""

    agent_def_dir = Path(state.agent_def_dir).expanduser().resolve()
    manifest_path = Path(state.session_manifest_path).expanduser().resolve()
    return resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=manifest_path,
    )


def _fetch_live_bundle(*, state: DemoState) -> dict[str, Any]:
    """Fetch the live managed-agent and tracked-terminal bundle for one local session."""

    target = _resolve_local_target(state)
    return _fetch_live_bundle_from_target(target=target)


def _fetch_live_bundle_from_target(*, target: Any) -> dict[str, Any]:
    """Fetch the live bundle for one already-resolved local managed-agent target."""

    state_response = managed_agent_state_payload(target)
    detail_response = managed_agent_detail_payload(target)
    history_response = managed_agent_history_payload(target, limit=DEFAULT_HISTORY_LIMIT)
    terminal_response = _local_terminal_state(target)
    return {
        "state": state_response,
        "detail": detail_response,
        "history": history_response,
        "terminal": terminal_response,
    }


def _local_terminal_state(target: Any) -> HoumaoTerminalStateResponse | None:
    """Return one live tracked-terminal state for a local TUI target."""

    controller = getattr(target, "controller", None)
    if controller is None:
        return None
    return _local_tui_runtime_for_controller(controller).refresh_once()


def _managed_agent_snapshot(
    *,
    state_response: HoumaoManagedAgentStateResponse,
    detail_response: HoumaoManagedAgentDetailResponse,
) -> ManagedAgentSnapshot:
    """Build one sanitized managed-agent snapshot from live route payloads."""

    detail_payload = detail_response.detail
    terminal_id = state_response.identity.terminal_id
    terminal_state_route: str | None = None
    terminal_history_route: str | None = None
    parsed_surface_present: bool | None = None
    ready_posture: str | None = None
    stable: bool | None = None
    stable_for_seconds: float | None = None
    can_accept_prompt_now: bool | None = None
    interruptible: bool | None = None
    if detail_payload.transport == "tui":
        terminal_id = detail_payload.terminal_id
        terminal_state_route = detail_payload.canonical_terminal_state_route
        terminal_history_route = detail_payload.canonical_terminal_history_route
        parsed_surface_present = detail_payload.parsed_surface is not None
        ready_posture = detail_payload.surface.ready_posture
        stable = detail_payload.stability.stable
        stable_for_seconds = detail_payload.stability.stable_for_seconds
    else:
        can_accept_prompt_now = detail_payload.can_accept_prompt_now
        interruptible = detail_payload.interruptible

    gateway_queue_depth: int | None = None
    if state_response.gateway is not None:
        gateway_queue_depth = state_response.gateway.queue_depth

    return ManagedAgentSnapshot(
        tracked_agent_id=state_response.tracked_agent_id,
        transport=state_response.identity.transport,
        tool=state_response.identity.tool,
        session_name=state_response.identity.session_name,
        terminal_id=terminal_id,
        manifest_path=state_response.identity.manifest_path,
        availability=state_response.availability,
        turn_phase=state_response.turn.phase,
        active_turn_id=state_response.turn.active_turn_id,
        last_turn_result=state_response.last_turn.result,
        last_turn_id=state_response.last_turn.turn_id,
        last_turn_index=state_response.last_turn.turn_index,
        last_turn_updated_at_utc=state_response.last_turn.updated_at_utc,
        detail_transport=detail_payload.transport,
        terminal_state_route=terminal_state_route,
        terminal_history_route=terminal_history_route,
        parsed_surface_present=parsed_surface_present,
        ready_posture=ready_posture,
        stable=stable,
        stable_for_seconds=stable_for_seconds,
        can_accept_prompt_now=can_accept_prompt_now,
        interruptible=interruptible,
        diagnostic_count=len(state_response.diagnostics),
        gateway_queue_depth=gateway_queue_depth,
    )


def _history_snapshot(response: HoumaoManagedAgentHistoryResponse) -> ManagedAgentHistorySnapshot:
    """Build one sanitized managed-agent history summary."""

    latest_entry = None
    if response.entries:
        latest_entry = max(response.entries, key=lambda entry: entry.recorded_at_utc)
    return ManagedAgentHistorySnapshot(
        entry_count=len(response.entries),
        latest_recorded_at_utc=latest_entry.recorded_at_utc if latest_entry is not None else None,
        latest_summary=latest_entry.summary if latest_entry is not None else None,
        latest_turn_phase=latest_entry.turn_phase if latest_entry is not None else None,
        latest_last_turn_result=(
            latest_entry.last_turn_result if latest_entry is not None else None
        ),
    )


def _terminal_snapshot(response: HoumaoTerminalStateResponse) -> TerminalSnapshot:
    """Build one sanitized tracked-terminal summary."""

    parsed_surface = response.parsed_surface
    return TerminalSnapshot(
        terminal_id=response.terminal_id,
        parser_family=parsed_surface.parser_family if parsed_surface is not None else None,
        availability=parsed_surface.availability if parsed_surface is not None else None,
        business_state=parsed_surface.business_state if parsed_surface is not None else None,
        input_mode=parsed_surface.input_mode if parsed_surface is not None else None,
        ui_context=parsed_surface.ui_context if parsed_surface is not None else None,
        parsed_surface_present=parsed_surface is not None,
        ready_posture=response.surface.ready_posture,
        turn_phase=response.turn.phase,
        last_turn_result=response.last_turn.result,
        stable=response.stability.stable,
        stable_for_seconds=response.stability.stable_for_seconds,
        recent_transition_count=len(response.recent_transitions),
        probe_captured_text_length=(
            response.probe_snapshot.captured_text_length
            if response.probe_snapshot is not None
            else None
        ),
    )


def _dialog_tail_from_terminal_state(
    *,
    terminal_state: HoumaoTerminalStateResponse,
    dialog_tail_chars: int,
) -> str | None:
    """Return one optional parser-derived dialog-tail excerpt."""

    if dialog_tail_chars <= 0:
        raise DemoWorkflowError("Dialog-tail length must be positive.")
    if terminal_state.parsed_surface is None:
        return None
    dialog_tail = terminal_state.parsed_surface.dialog_tail
    if not dialog_tail:
        return None
    return dialog_tail[-dialog_tail_chars:]


def _submit_request_artifact(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    artifact_kind: str,
    request_kind: str,
    prompt: str | None,
) -> TurnArtifact:
    """Submit one managed-agent request and persist the recorded artifact."""

    state = require_active_state(paths.state_path, command_name=artifact_kind)
    target = _resolve_local_target(state)
    live_bundle = _fetch_live_bundle_from_target(target=target)
    state_before = _managed_agent_snapshot(
        state_response=live_bundle["state"],
        detail_response=live_bundle["detail"],
    )
    history_before = _history_snapshot(live_bundle["history"])
    terminal_before = (
        _terminal_snapshot(live_bundle["terminal"])
        if live_bundle["terminal"] is not None
        else None
    )
    baseline_signature = _bundle_signature(
        managed_agent=state_before,
        history=history_before,
        terminal=terminal_before,
    )
    requested_at_utc = _utc_now()
    request_record = _submit_request_record(
        target=target,
        request_kind=request_kind,
        prompt=prompt,
    )

    poll_iterations = 0
    state_change_observed = False
    latest_state_snapshot = state_before
    latest_history_snapshot = history_before
    latest_terminal_snapshot = terminal_before
    deadline = time.monotonic() + env.request_settle_timeout_seconds
    while True:
        poll_iterations += 1
        polled_bundle = _fetch_live_bundle_from_target(target=target)
        latest_state_snapshot = _managed_agent_snapshot(
            state_response=polled_bundle["state"],
            detail_response=polled_bundle["detail"],
        )
        latest_history_snapshot = _history_snapshot(polled_bundle["history"])
        latest_terminal_snapshot = (
            _terminal_snapshot(polled_bundle["terminal"])
            if polled_bundle["terminal"] is not None
            else None
        )
        if (
            _bundle_signature(
                managed_agent=latest_state_snapshot,
                history=latest_history_snapshot,
                terminal=latest_terminal_snapshot,
            )
            != baseline_signature
        ):
            state_change_observed = True
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(env.request_poll_interval_seconds)

    settled_at_utc = _utc_now()
    sequence_number = (
        state.prompt_turn_count + 1 if artifact_kind == "send-turn" else state.interrupt_count + 1
    )
    artifact = TurnArtifact(
        artifact_kind=artifact_kind,  # type: ignore[arg-type]
        sequence_number=sequence_number,
        request_kind=request_kind,  # type: ignore[arg-type]
        prompt=prompt,
        agent_name=state.agent_name,
        agent_id=state.agent_id,
        tmux_session_name=state.tmux_session_name,
        tracked_agent_id=latest_state_snapshot.tracked_agent_id,
        requested_at_utc=requested_at_utc,
        settled_at_utc=settled_at_utc,
        poll_iterations=poll_iterations,
        state_change_observed=state_change_observed,
        request=request_record,
        state_before=state_before,
        state_after=latest_state_snapshot,
        history_after=latest_history_snapshot,
        terminal_after=latest_terminal_snapshot,
    )
    artifact_path = (
        paths.turns_dir / f"turn-{sequence_number:03d}.json"
        if artifact_kind == "send-turn"
        else paths.interrupts_dir / f"interrupt-{sequence_number:03d}.json"
    )
    _write_json_file(artifact_path, artifact.model_dump(mode="json"))

    updated_state = state.model_copy(
        update={
            "tracked_agent_id": latest_state_snapshot.tracked_agent_id,
            "updated_at": settled_at_utc,
            "prompt_turn_count": sequence_number
            if artifact_kind == "send-turn"
            else state.prompt_turn_count,
            "interrupt_count": sequence_number
            if artifact_kind == "interrupt"
            else state.interrupt_count,
        }
    )
    save_demo_state(paths.state_path, updated_state)
    return artifact


def _submit_request_record(*, target: Any, request_kind: str, prompt: str | None) -> DemoRequestRecord:
    """Submit one request through the local managed-agent helper surface."""

    if request_kind == "submit_prompt":
        response = prompt_managed_agent(target, prompt=prompt or "")
        record = _request_record_from_prompt_response(response)
        if not record.success or record.disposition != "accepted":
            raise DemoWorkflowError(f"Prompt request was not accepted: {record.detail}")
        return record
    if request_kind == "interrupt":
        response = interrupt_managed_agent(target)
        record = _request_record_from_interrupt_response(
            response=response,
            tracked_agent_id=target.identity.tracked_agent_id,
        )
        if not record.success:
            raise DemoWorkflowError(f"Interrupt request failed: {record.detail}")
        return record
    raise DemoWorkflowError(f"Unsupported request kind `{request_kind}`.")


def _request_record_from_prompt_response(response: object) -> DemoRequestRecord:
    """Normalize one prompt-submission response into the demo artifact schema."""

    request_id = getattr(response, "request_id", None)
    tracked_agent_id = getattr(response, "tracked_agent_id", None)
    detail = getattr(response, "detail", None)
    if not isinstance(request_id, str) or not request_id.strip():
        raise DemoWorkflowError("Prompt response did not include a usable request id.")
    if not isinstance(tracked_agent_id, str) or not tracked_agent_id.strip():
        raise DemoWorkflowError("Prompt response did not include a usable tracked_agent_id.")
    if not isinstance(detail, str) or not detail.strip():
        raise DemoWorkflowError("Prompt response did not include a usable detail message.")
    success = getattr(response, "success", True)
    disposition = getattr(response, "disposition", "accepted")
    return DemoRequestRecord(
        request_id=request_id,
        request_kind="submit_prompt",
        tracked_agent_id=tracked_agent_id,
        detail=detail,
        success=bool(success),
        disposition="accepted" if str(disposition) == "accepted" else "accepted",
    )


def _request_record_from_interrupt_response(
    *,
    response: object,
    tracked_agent_id: str,
) -> DemoRequestRecord:
    """Normalize one interrupt-action response into the demo artifact schema."""

    response_tracked_agent_id = getattr(response, "tracked_agent_id", None)
    detail = getattr(response, "detail", None)
    if not isinstance(detail, str) or not detail.strip():
        raise DemoWorkflowError("Interrupt response did not include a usable detail message.")
    normalized_tracked_agent_id = tracked_agent_id
    if isinstance(response_tracked_agent_id, str) and response_tracked_agent_id.strip():
        normalized_tracked_agent_id = response_tracked_agent_id
    return DemoRequestRecord(
        request_id=f"interrupt-{uuid.uuid4().hex}",
        request_kind="interrupt",
        tracked_agent_id=normalized_tracked_agent_id,
        detail=detail,
        success=bool(getattr(response, "success", False)),
        disposition="action",
    )


def _bundle_signature(
    *,
    managed_agent: ManagedAgentSnapshot,
    history: ManagedAgentHistorySnapshot,
    terminal: TerminalSnapshot | None,
) -> tuple[object, ...]:
    """Return the stable coarse signature used for bounded state-change polling."""

    terminal_signature = None
    if terminal is not None:
        terminal_signature = (
            terminal.turn_phase,
            terminal.last_turn_result,
            terminal.stable,
            terminal.recent_transition_count,
        )
    return (
        managed_agent.turn_phase,
        managed_agent.active_turn_id,
        managed_agent.last_turn_result,
        managed_agent.last_turn_id,
        managed_agent.last_turn_index,
        history.entry_count,
        history.latest_recorded_at_utc,
        terminal_signature,
    )


def _verification_request_summary(artifact: TurnArtifact) -> VerificationRequestSummary:
    """Build one stable verification summary row from a persisted artifact."""

    return VerificationRequestSummary(
        artifact_kind=artifact.artifact_kind,
        sequence_number=artifact.sequence_number,
        request_kind=artifact.request_kind,
        request_id=artifact.request.request_id,
        tracked_agent_id=artifact.tracked_agent_id,
        prompt_present=bool((artifact.prompt or "").strip()),
        state_change_observed=artifact.state_change_observed,
        after_turn_phase=artifact.state_after.turn_phase,
        after_last_turn_result=artifact.state_after.last_turn_result,
        after_last_turn_id=artifact.state_after.last_turn_id,
        after_last_turn_index=artifact.state_after.last_turn_index,
        history_entry_count=artifact.history_after.entry_count,
    )


def _load_artifacts(*, pattern: str, root: Path) -> list[TurnArtifact]:
    """Load all persisted request artifacts that match one file-glob pattern."""

    if not root.exists():
        return []
    artifacts: list[TurnArtifact] = []
    for path in sorted(root.glob(pattern)):
        payload = _load_json_file(path, context="request artifact")
        try:
            artifacts.append(TurnArtifact.model_validate(payload))
        except Exception as exc:
            raise DemoWorkflowError(f"Invalid request artifact at `{path}`: {exc}") from exc
    return sorted(artifacts, key=lambda artifact: artifact.sequence_number)


def _stop_live_state(
    *,
    state: DemoState,
    tolerate_stale: bool,
) -> tuple[str, bool]:
    """Stop one active demo session through the local runtime controller."""

    stop_status = "not_attempted"
    stale_tolerated = False
    try:
        controller = _resume_local_controller(state)
        with _temporary_environment_bindings(_state_environment(state)):
            result = controller.stop(force_cleanup=True)
        if result.status != "ok":
            raise DemoWorkflowError(result.detail)
        stop_status = "stopped"
    except Exception as exc:
        if tolerate_stale and _is_stale_stop_error(exc):
            stop_status = "stale_missing"
            stale_tolerated = True
        else:
            raise DemoWorkflowError(
                f"Failed to stop the managed demo agent `{state.agent_name}`: {exc}"
            ) from exc
    finally:
        _best_effort_kill_tmux_session(state.tmux_session_name)
        _best_effort_cleanup_session_root(Path(state.session_root).expanduser().resolve())

    return (stop_status, stale_tolerated)


def _best_effort_stop_controller(*, controller: Any, runtime_env: dict[str, str]) -> None:
    """Stop one partially started controller during startup error cleanup."""

    try:
        with _temporary_environment_bindings(runtime_env):
            controller.stop(force_cleanup=True)
    except Exception:
        pass
    tmux_session_name = getattr(controller, "tmux_session_name", None)
    if isinstance(tmux_session_name, str) and tmux_session_name.strip():
        _best_effort_kill_tmux_session(tmux_session_name)
    manifest_path = getattr(controller, "manifest_path", None)
    if isinstance(manifest_path, Path):
        _best_effort_cleanup_session_root(manifest_path.parent.resolve())


def _best_effort_kill_tmux_session(session_name: str) -> None:
    """Best-effort local tmux cleanup for one recorded session name."""

    try:
        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return


def _best_effort_cleanup_session_root(session_root: Path) -> None:
    """Best-effort deletion of one stale runtime session root."""

    if not session_root.exists() or session_root == session_root.parent:
        return
    shutil.rmtree(session_root, ignore_errors=True)


def _is_stale_stop_error(exc: Exception) -> bool:
    """Return whether one stop failure matches a stale-session outcome."""

    if isinstance(exc, FileNotFoundError):
        return True
    rendered = str(exc).lower()
    return any(marker in rendered for marker in STALE_STOP_MARKERS)


def _demo_agent_def_dir_path(repo_root: Path) -> Path:
    """Return the tracked demo-local agent-definition path for the demo."""

    return (
        repo_root.resolve()
        / "scripts"
        / "demo"
        / "houmao-server-interactive-full-pipeline-demo"
        / "agents"
    )


def _load_json_file(path: Path, *, context: str) -> Any:
    """Load one JSON file with explicit error reporting."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DemoWorkflowError(f"{context} file was not found: `{path}`") from exc
    except json.JSONDecodeError as exc:
        raise DemoWorkflowError(f"{context} file is not valid JSON: `{path}`") from exc


def _write_json_file(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    """Persist the latest workspace root used by the shell wrappers."""

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


def _utc_now() -> str:
    """Return the current UTC timestamp with second precision."""

    return datetime.now(UTC).isoformat(timespec="seconds")

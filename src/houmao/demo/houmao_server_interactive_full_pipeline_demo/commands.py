"""Lifecycle commands for the Houmao-server interactive full-pipeline demo."""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from houmao.agents.realm_controller.agent_identity import normalize_agent_identity_name
from houmao.agents.realm_controller.boundary_models import HoumaoServerSectionV1
from houmao.agents.realm_controller.manifest import default_manifest_path, load_session_manifest
from houmao.cao.models import CaoSessionDetail
from houmao.cao.rest_client import CaoApiError
from houmao.demo.houmao_server_interactive_full_pipeline_demo.models import (
    DEFAULT_AGENT_PROFILE,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_WORKTREE_DIRNAME,
    DemoEnvironment,
    DemoPaths,
    DemoState,
    DemoWorkflowError,
    InspectPayload,
    ManagedAgentHistorySnapshot,
    ManagedAgentSnapshot,
    StartupPayload,
    STALE_STOP_MARKERS,
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
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentInterruptRequest,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoTerminalStateResponse,
)


def start_demo(
    *,
    paths: DemoPaths,
    env: DemoEnvironment,
    provider: str,
    requested_session_name: str | None,
    requested_port: int | None,
) -> StartupPayload:
    """Start or replace the interactive demo run."""

    resolved_tool = tool_for_provider(provider)
    if requested_port is not None and not _port_is_available(requested_port):
        raise DemoWorkflowError(f"Requested loopback port is unavailable: {requested_port}")

    _ensure_workspace(paths)
    replaced_previous_session_name = _cleanup_existing_state_for_startup(paths=paths, env=env)
    if env.provision_worktree:
        _provision_default_worktree(paths=paths, repo_root=env.repo_root)
    _reset_demo_artifacts(paths)

    selected_port = _select_port(requested_port)
    api_base_url = f"http://127.0.0.1:{selected_port}"
    profile_source = _profile_source_path(env.repo_root)
    if not profile_source.is_file():
        raise DemoWorkflowError(f"Tracked compatibility profile not found: {profile_source}")

    runtime_env = _build_demo_environment(paths=paths)
    server_process: subprocess.Popen[bytes] | None = None
    client: HoumaoServerClient | None = None
    actual_session_name: str | None = _expected_session_name(requested_session_name)
    try:
        server_process = _start_server_process(
            api_base_url=api_base_url,
            paths=paths,
            timeout_seconds=env.server_start_timeout_seconds,
            env=runtime_env,
            compat_shell_ready_timeout_seconds=env.compat_shell_ready_timeout_seconds,
            compat_provider_ready_timeout_seconds=env.compat_provider_ready_timeout_seconds,
            compat_codex_warmup_seconds=env.compat_codex_warmup_seconds,
        )
        _install_pair_profile(
            api_base_url=api_base_url,
            profile_source=profile_source,
            provider=provider,
            env=runtime_env,
            stdout_path=paths.logs_dir / "install.stdout.log",
            stderr_path=paths.logs_dir / "install.stderr.log",
        )

        client = HoumaoServerClient(api_base_url, timeout_seconds=5.0)
        existing_session_names = _list_session_names(client)
        _launch_pair_session(
            api_base_url=api_base_url,
            provider=provider,
            requested_session_name=requested_session_name,
            workdir=paths.workdir,
            env=runtime_env,
            compat_create_timeout_seconds=env.compat_create_timeout_seconds,
        )
        actual_session_name = _wait_for_launched_session_name(
            client=client,
            existing_session_names=existing_session_names,
            expected_session_name=actual_session_name,
            timeout_seconds=env.request_settle_timeout_seconds,
        )
        session_detail = _wait_for_session_detail(
            client=client,
            session_name=actual_session_name,
            timeout_seconds=env.request_settle_timeout_seconds,
        )
        terminal_id = _terminal_id_from_session_detail(
            session_detail=session_detail,
            session_name=actual_session_name,
        )
        manifest_path = _wait_for_session_manifest(
            runtime_root=paths.runtime_root,
            session_name=actual_session_name,
            timeout_seconds=env.request_settle_timeout_seconds,
        )
        bridge = _load_manifest_bridge(manifest_path)
        managed_identity = _wait_for_managed_agent_identity(
            client=client,
            agent_ref=actual_session_name,
            timeout_seconds=env.request_settle_timeout_seconds,
        )
    except Exception as exc:
        if actual_session_name is not None:
            _best_effort_delete_session(
                api_base_url=api_base_url,
                session_name=actual_session_name,
                timeout_seconds=env.server_stop_timeout_seconds,
            )
            _best_effort_kill_tmux_session(actual_session_name)
        if server_process is not None:
            _stop_server_process(
                pid=server_process.pid,
                api_base_url=api_base_url,
                timeout_seconds=env.server_stop_timeout_seconds,
            )
        if isinstance(exc, DemoWorkflowError):
            raise
        raise DemoWorkflowError(str(exc)) from exc

    if bridge.session_name != actual_session_name:
        raise DemoWorkflowError(
            "Delegated manifest `houmao_server.session_name` did not match the launched session "
            f"({bridge.session_name!r} != {actual_session_name!r})."
        )
    if bridge.terminal_id != terminal_id:
        raise DemoWorkflowError(
            "Delegated manifest `houmao_server.terminal_id` did not match the registered "
            f"terminal ({bridge.terminal_id!r} != {terminal_id!r})."
        )

    identity_source = requested_session_name or actual_session_name
    state = DemoState(
        active=True,
        provider=provider,
        tool=resolved_tool,
        agent_profile=DEFAULT_AGENT_PROFILE,
        variant_id=f"{resolved_tool}-{DEFAULT_AGENT_PROFILE}",
        api_base_url=api_base_url,
        agent_identity=normalize_agent_identity_name(identity_source).canonical_name,
        agent_ref=actual_session_name,
        requested_session_name=requested_session_name,
        session_manifest_path=str(manifest_path),
        session_root=str(manifest_path.parent.resolve()),
        session_name=actual_session_name,
        terminal_id=terminal_id,
        tracked_agent_id=managed_identity.tracked_agent_id,
        runtime_root=str(paths.runtime_root),
        registry_root=str(paths.registry_root),
        jobs_root=str(paths.jobs_root),
        workspace_dir=str(paths.workspace_root),
        workdir=str(paths.workdir),
        server_home_dir=str(paths.server_home_dir),
        server_runtime_root=str(paths.server_runtime_root),
        server_pid=server_process.pid,
        server_stdout_log_path=str(paths.logs_dir / "houmao-server.stdout.log"),
        server_stderr_log_path=str(paths.logs_dir / "houmao-server.stderr.log"),
        install_profile_source=str(profile_source),
        install_stdout_log_path=str(paths.logs_dir / "install.stdout.log"),
        install_stderr_log_path=str(paths.logs_dir / "install.stderr.log"),
        houmao_server=bridge,
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
    """Inspect persisted demo state plus live server state when available."""

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
    if state.active:
        try:
            live_bundle = _fetch_live_bundle(
                api_base_url=state.api_base_url,
                agent_ref=state.agent_ref,
                terminal_id=state.terminal_id,
            )
            managed_agent = _managed_agent_snapshot(
                state_response=live_bundle["state"],
                detail_response=live_bundle["detail"],
            )
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
        live_error = "Demo state is inactive; live server inspection skipped."

    return InspectPayload(
        active=state.active,
        provider=state.provider,
        tool=state.tool,
        agent_profile=state.agent_profile,
        variant_id=state.variant_id,
        api_base_url=state.api_base_url,
        agent_identity=state.agent_identity,
        agent_ref=state.agent_ref,
        session_name=state.session_name,
        terminal_id=state.terminal_id,
        tracked_agent_id=state.tracked_agent_id,
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
    """Submit one prompt through the managed-agent request route."""

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
    """Submit one interrupt through the managed-agent request route."""

    return _submit_request_artifact(
        paths=paths,
        env=env,
        artifact_kind="interrupt",
        request_kind="interrupt",
        prompt=None,
    )


def verify_demo(*, paths: DemoPaths) -> VerificationReport:
    """Build one sanitized verification report from request artifacts and server state."""

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

    evidence_source: Literal["live_server", "captured_artifacts"] = "captured_artifacts"
    current_managed_agent = combined_artifacts[-1].state_after
    current_history = combined_artifacts[-1].history_after
    current_terminal = combined_artifacts[-1].terminal_after
    if state.active:
        try:
            live_bundle = _fetch_live_bundle(
                api_base_url=state.api_base_url,
                agent_ref=state.agent_ref,
                terminal_id=state.terminal_id,
            )
            current_managed_agent = _managed_agent_snapshot(
                state_response=live_bundle["state"],
                detail_response=live_bundle["detail"],
            )
            current_history = _history_snapshot(live_bundle["history"])
            terminal_response = live_bundle["terminal"]
            current_terminal = (
                _terminal_snapshot(terminal_response) if terminal_response is not None else None
            )
            evidence_source = "live_server"
        except Exception:
            evidence_source = "captured_artifacts"

    if (
        current_history.entry_count == 0
        and not any(artifact.state_change_observed for artifact in prompt_artifacts)
        and current_managed_agent.last_turn_result == "none"
    ):
        raise DemoWorkflowError(
            "Verification requires server-tracked evidence beyond accepted request records."
        )

    report = VerificationReport(
        status="ok",
        evidence_source=evidence_source,
        provider=state.provider,
        tool=state.tool,
        agent_profile=state.agent_profile,
        variant_id=state.variant_id,
        api_base_url=state.api_base_url,
        agent_identity=state.agent_identity,
        agent_ref=state.agent_ref,
        session_name=state.session_name,
        terminal_id=state.terminal_id,
        tracked_agent_id=state.tracked_agent_id,
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
    delete_status, stale_tolerated, server_status = _stop_live_state(
        state=state,
        timeout_seconds=env.server_stop_timeout_seconds,
        tolerate_stale=True,
    )
    inactive_state = state.model_copy(update={"active": False, "updated_at": _utc_now()})
    save_demo_state(paths.state_path, inactive_state)
    return StopPayload(
        state=inactive_state,
        session_delete_status=delete_status,
        stale_session_tolerated=stale_tolerated,
        server_stop_status=server_status,
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
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.logs_dir,
        paths.turns_dir,
        paths.interrupts_dir,
        paths.server_home_dir,
        paths.server_runtime_root,
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
            replaced_previous_session_name = state.session_name
        _stop_live_state(
            state=state,
            timeout_seconds=env.server_stop_timeout_seconds,
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


def _build_demo_environment(*, paths: DemoPaths) -> dict[str, str]:
    """Return the shared environment used by the demo-owned server and pair helpers."""

    env = dict(os.environ)
    env["HOME"] = str(paths.server_home_dir)
    env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.runtime_root)
    env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    return env


def _start_server_process(
    *,
    api_base_url: str,
    paths: DemoPaths,
    timeout_seconds: float,
    env: dict[str, str],
    compat_shell_ready_timeout_seconds: float,
    compat_provider_ready_timeout_seconds: float,
    compat_codex_warmup_seconds: float,
) -> subprocess.Popen[bytes]:
    """Start the demo-owned Houmao server and wait for health readiness."""

    stdout_path = paths.logs_dir / "houmao-server.stdout.log"
    stderr_path = paths.logs_dir / "houmao-server.stderr.log"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "houmao.server",
            "serve",
            "--api-base-url",
            api_base_url,
            "--runtime-root",
            str(paths.server_runtime_root),
            "--compat-shell-ready-timeout-seconds",
            str(compat_shell_ready_timeout_seconds),
            "--compat-provider-ready-timeout-seconds",
            str(compat_provider_ready_timeout_seconds),
            "--compat-codex-warmup-seconds",
            str(compat_codex_warmup_seconds),
        ],
        cwd=str(paths.workspace_root),
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        start_new_session=True,
    )
    stdout_handle.close()
    stderr_handle.close()
    _wait_for_server_health(api_base_url=api_base_url, timeout_seconds=timeout_seconds)
    return process


def _wait_for_server_health(*, api_base_url: str, timeout_seconds: float) -> None:
    """Wait until the selected Houmao server reports healthy status."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=1.0)
    deadline = time.monotonic() + timeout_seconds
    last_error = "server did not become healthy"
    while time.monotonic() < deadline:
        try:
            health = client.health_extended()
            cao_health = client.health()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if (
            health.status == "ok"
            and health.houmao_service == "houmao-server"
            and cao_health.status == "ok"
        ):
            return
        last_error = json.dumps(
            {
                "houmao": health.model_dump(mode="json"),
                "cao": cao_health.model_dump(mode="json"),
            },
            sort_keys=True,
        )
        time.sleep(0.25)
    raise DemoWorkflowError(
        f"Timed out waiting for demo-owned houmao-server health at {api_base_url}: {last_error}"
    )


def _install_pair_profile(
    *,
    api_base_url: str,
    profile_source: Path,
    provider: str,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    """Install the tracked compatibility profile through `houmao-mgr install`."""

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "houmao.srv_ctrl",
            "install",
            str(profile_source),
            "--provider",
            provider,
            "--port",
            api_base_url.rsplit(":", 1)[-1],
        ],
        cwd=str(profile_source.parent),
        check=False,
        capture_output=True,
        env=env,
    )
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    if result.returncode != 0:
        detail = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode("utf-8", errors="replace").strip()
            or "unknown install error"
        )
        raise DemoWorkflowError(
            f"Pair-owned profile install failed for provider `{provider}`: {detail}"
        )


def _launch_pair_session(
    *,
    api_base_url: str,
    provider: str,
    requested_session_name: str | None,
    workdir: Path,
    env: dict[str, str],
    compat_create_timeout_seconds: float,
) -> None:
    """Launch one detached TUI session through the public compatibility CLI."""

    command = [
        sys.executable,
        "-m",
        "houmao.srv_ctrl",
        "cao",
        "launch",
        "--headless",
        "--yolo",
        "--agents",
        DEFAULT_AGENT_PROFILE,
        "--provider",
        provider,
        "--port",
        api_base_url.rsplit(":", 1)[-1],
        "--compat-create-timeout-seconds",
        str(compat_create_timeout_seconds),
    ]
    if requested_session_name is not None and requested_session_name.strip():
        command.extend(["--session-name", requested_session_name.strip()])

    result = subprocess.run(
        command,
        cwd=str(workdir.resolve()),
        check=False,
        capture_output=True,
        env=env,
    )
    if result.returncode != 0:
        detail = (
            result.stderr.decode("utf-8", errors="replace").strip()
            or result.stdout.decode("utf-8", errors="replace").strip()
            or "unknown launch error"
        )
        raise DemoWorkflowError(
            "Pair-managed detached TUI launch failed via "
            "`houmao-mgr cao launch --headless`: "
            f"{detail}"
        )


def _wait_for_launched_session_name(
    *,
    client: HoumaoServerClient,
    existing_session_names: set[str],
    expected_session_name: str | None,
    timeout_seconds: float,
) -> str:
    """Wait until detached compatibility launch produces one new CAO-compatible session name."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "no new session appeared"
    while time.monotonic() < deadline:
        try:
            session_names = _list_session_names(client)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if expected_session_name is not None and expected_session_name in session_names:
            return expected_session_name
        new_names = session_names - existing_session_names
        if len(new_names) == 1:
            return next(iter(new_names))
        if len(new_names) > 1:
            raise DemoWorkflowError(
                "Unable to identify the delegated pair launch uniquely; multiple new sessions "
                f"appeared: {sorted(new_names)!r}"
            )
        time.sleep(0.25)
    raise DemoWorkflowError(
        "Timed out waiting for a new detached compatibility session to appear: "
        f"{last_error}"
    )


def _wait_for_session_detail(
    *,
    client: HoumaoServerClient,
    session_name: str,
    timeout_seconds: float,
) -> CaoSessionDetail:
    """Wait until a launched session is visible through Houmao server queries."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "session did not appear"
    while time.monotonic() < deadline:
        try:
            payload = client.get_session(session_name)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if payload.terminals:
            return payload
        last_error = f"session `{session_name}` had no terminals yet"
        time.sleep(0.25)
    raise DemoWorkflowError(
        f"Timed out waiting for session registration for `{session_name}`: {last_error}"
    )


def _terminal_id_from_session_detail(*, session_detail: CaoSessionDetail, session_name: str) -> str:
    """Extract the registered terminal id from one session detail payload."""

    if not session_detail.terminals:
        raise DemoWorkflowError(f"Session `{session_name}` returned no terminals.")
    terminal_id = session_detail.terminals[0].id.strip()
    if not terminal_id:
        raise DemoWorkflowError(f"Session `{session_name}` returned an empty terminal id.")
    return terminal_id


def _wait_for_session_manifest(
    *,
    runtime_root: Path,
    session_name: str,
    timeout_seconds: float,
) -> Path:
    """Wait until the delegated runtime manifest exists on disk."""

    manifest_path = default_manifest_path(
        runtime_root, "houmao_server_rest", session_name
    ).resolve()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if manifest_path.is_file():
            return manifest_path
        time.sleep(0.25)
    raise DemoWorkflowError(
        f"Timed out waiting for the delegated runtime manifest to appear at `{manifest_path}`."
    )


def _load_manifest_bridge(manifest_path: Path) -> HoumaoServerSectionV1:
    """Load and validate the persisted `houmao_server` manifest bridge section."""

    payload = load_session_manifest(manifest_path).payload
    if not isinstance(payload, dict):
        raise DemoWorkflowError(f"Session manifest `{manifest_path}` did not contain a mapping.")
    raw_bridge = payload.get("houmao_server")
    if not isinstance(raw_bridge, dict):
        raise DemoWorkflowError(
            f"Session manifest `{manifest_path}` is missing the `houmao_server` section."
        )
    try:
        return HoumaoServerSectionV1.model_validate(raw_bridge)
    except Exception as exc:
        raise DemoWorkflowError(
            f"Session manifest `{manifest_path}` contained an invalid `houmao_server` section: {exc}"
        ) from exc


def _wait_for_managed_agent_identity(
    *,
    client: HoumaoServerClient,
    agent_ref: str,
    timeout_seconds: float,
) -> Any:
    """Wait until the launched session is server-addressable as a managed agent."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "managed-agent route did not become available"
    while time.monotonic() < deadline:
        try:
            identity = client.get_managed_agent(agent_ref)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if identity.transport == "tui" and identity.session_name == agent_ref:
            return identity
        last_error = (
            "managed-agent route returned an unexpected identity "
            f"(transport={identity.transport!r}, session_name={identity.session_name!r})"
        )
        time.sleep(0.25)
    raise DemoWorkflowError(
        "Timed out waiting for the detached compatibility launch to become "
        f"server-addressable without a second registration POST: {last_error}"
    )


def _fetch_live_bundle(
    *,
    api_base_url: str,
    agent_ref: str,
    terminal_id: str,
) -> dict[str, Any]:
    """Fetch the live managed-agent and tracked-terminal bundle for one session."""

    client = HoumaoServerClient(api_base_url, timeout_seconds=5.0)
    state_response = client.get_managed_agent_state(agent_ref)
    detail_response = client.get_managed_agent_state_detail(agent_ref)
    history_response = client.get_managed_agent_history(agent_ref, limit=DEFAULT_HISTORY_LIMIT)
    terminal_response = client.terminal_state(terminal_id)
    return {
        "state": state_response,
        "detail": detail_response,
        "history": history_response,
        "terminal": terminal_response,
    }


def _managed_agent_snapshot(
    *,
    state_response: HoumaoManagedAgentStateResponse,
    detail_response: HoumaoManagedAgentDetailResponse,
) -> ManagedAgentSnapshot:
    """Build one sanitized managed-agent snapshot from live route payloads."""

    detail_payload = detail_response.detail
    terminal_state_route: str | None = None
    terminal_history_route: str | None = None
    parsed_surface_present: bool | None = None
    ready_posture: str | None = None
    stable: bool | None = None
    stable_for_seconds: float | None = None
    can_accept_prompt_now: bool | None = None
    interruptible: bool | None = None
    if detail_payload.transport == "tui":
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
        terminal_id=state_response.identity.terminal_id,
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
    live_bundle = _fetch_live_bundle(
        api_base_url=state.api_base_url,
        agent_ref=state.agent_ref,
        terminal_id=state.terminal_id,
    )
    state_before = _managed_agent_snapshot(
        state_response=live_bundle["state"],
        detail_response=live_bundle["detail"],
    )
    baseline_signature = _bundle_signature(
        managed_agent=state_before,
        history=_history_snapshot(live_bundle["history"]),
        terminal=_terminal_snapshot(live_bundle["terminal"]),
    )
    client = HoumaoServerClient(state.api_base_url, timeout_seconds=5.0)
    requested_at_utc = _utc_now()
    request_model: HoumaoManagedAgentSubmitPromptRequest | HoumaoManagedAgentInterruptRequest
    if request_kind == "submit_prompt":
        request_model = HoumaoManagedAgentSubmitPromptRequest(prompt=prompt or "")
    elif request_kind == "interrupt":
        request_model = HoumaoManagedAgentInterruptRequest()
    else:
        raise DemoWorkflowError(f"Unsupported request kind `{request_kind}`.")
    response = client.submit_managed_agent_request(state.agent_ref, request_model)

    poll_iterations = 0
    state_change_observed = False
    latest_state_snapshot = state_before
    latest_history_snapshot = _history_snapshot(live_bundle["history"])
    latest_terminal_snapshot = _terminal_snapshot(live_bundle["terminal"])
    deadline = time.monotonic() + env.request_settle_timeout_seconds
    while True:
        poll_iterations += 1
        polled_bundle = _fetch_live_bundle(
            api_base_url=state.api_base_url,
            agent_ref=state.agent_ref,
            terminal_id=state.terminal_id,
        )
        latest_state_snapshot = _managed_agent_snapshot(
            state_response=polled_bundle["state"],
            detail_response=polled_bundle["detail"],
        )
        latest_history_snapshot = _history_snapshot(polled_bundle["history"])
        latest_terminal_snapshot = _terminal_snapshot(polled_bundle["terminal"])
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
        agent_ref=state.agent_ref,
        tracked_agent_id=response.tracked_agent_id,
        requested_at_utc=requested_at_utc,
        settled_at_utc=settled_at_utc,
        poll_iterations=poll_iterations,
        state_change_observed=state_change_observed,
        request=response,
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

    next_turn_index = state.houmao_server.turn_index
    if latest_state_snapshot.last_turn_index is not None:
        next_turn_index = max(next_turn_index, latest_state_snapshot.last_turn_index)
    updated_state = state.model_copy(
        update={
            "tracked_agent_id": response.tracked_agent_id,
            "updated_at": settled_at_utc,
            "prompt_turn_count": sequence_number
            if artifact_kind == "send-turn"
            else state.prompt_turn_count,
            "interrupt_count": sequence_number
            if artifact_kind == "interrupt"
            else state.interrupt_count,
            "houmao_server": state.houmao_server.model_copy(update={"turn_index": next_turn_index}),
        }
    )
    save_demo_state(paths.state_path, updated_state)
    return artifact


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
    timeout_seconds: float,
    tolerate_stale: bool,
) -> tuple[str, bool, str]:
    """Stop one active demo session and its demo-owned server."""

    delete_status = "not_attempted"
    stale_tolerated = False
    try:
        client = HoumaoServerClient(state.api_base_url, timeout_seconds=3.0)
        client.stop_managed_agent(state.agent_ref)
        _wait_for_session_absent(
            client=client,
            session_name=state.session_name,
            timeout_seconds=timeout_seconds,
        )
        delete_status = "stopped"
    except Exception as exc:
        if tolerate_stale and _is_stale_stop_error(exc):
            delete_status = "stale_missing"
            stale_tolerated = True
        else:
            raise DemoWorkflowError(
                f"Failed to stop the managed demo agent `{state.agent_ref}`: {exc}"
            ) from exc
    finally:
        _best_effort_kill_tmux_session(state.session_name)

    server_stop_status = _stop_server_process(
        pid=state.server_pid,
        api_base_url=state.api_base_url,
        timeout_seconds=timeout_seconds,
    )["status"]
    return (delete_status, stale_tolerated, server_stop_status)


def _wait_for_session_absent(
    *,
    client: HoumaoServerClient,
    session_name: str,
    timeout_seconds: float,
) -> None:
    """Wait until one session disappears from server queries."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            client.get_session(session_name)
        except CaoApiError as exc:
            if exc.status_code == 404:
                return
        except Exception:
            return
        time.sleep(0.25)
    raise DemoWorkflowError(
        f"Timed out waiting for `{session_name}` to disappear from houmao-server."
    )


def _best_effort_delete_session(
    *,
    api_base_url: str,
    session_name: str,
    timeout_seconds: float,
) -> None:
    """Best-effort session delete used during partial-start cleanup."""

    try:
        client = HoumaoServerClient(api_base_url, timeout_seconds=3.0)
        client.delete_session(session_name)
        _wait_for_session_absent(
            client=client, session_name=session_name, timeout_seconds=timeout_seconds
        )
    except Exception:
        return


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


def _is_stale_stop_error(exc: Exception) -> bool:
    """Return whether one stop failure matches a stale-session outcome."""

    if isinstance(exc, CaoApiError) and exc.status_code == 404:
        return True
    rendered = str(exc).lower()
    return any(marker in rendered for marker in STALE_STOP_MARKERS)


def _stop_server_process(*, pid: int, api_base_url: str, timeout_seconds: float) -> dict[str, Any]:
    """Stop the demo-owned Houmao server process and wait for exit."""

    if pid <= 0:
        return {"status": "already_stopped", "pid": pid}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {"status": "already_stopped", "pid": pid}

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_exists(pid) and not _server_health_ok(api_base_url):
            return {"status": "stopped", "pid": pid}
        time.sleep(0.25)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return {"status": "stopped", "pid": pid}
    time.sleep(0.2)
    return {"status": "forced", "pid": pid}


def _pid_exists(pid: int) -> bool:
    """Return whether one process id currently exists."""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _server_health_ok(api_base_url: str) -> bool:
    """Return whether one Houmao server still responds healthy."""

    try:
        client = HoumaoServerClient(api_base_url, timeout_seconds=1.0)
        health = client.health_extended()
    except Exception:
        return False
    return health.status == "ok" and health.houmao_service == "houmao-server"


def _profile_source_path(repo_root: Path) -> Path:
    """Return the tracked compatibility-profile asset path for the demo."""

    return (
        repo_root.resolve()
        / "scripts"
        / "demo"
        / "houmao-server-interactive-full-pipeline-demo"
        / "profiles"
        / f"{DEFAULT_AGENT_PROFILE}.md"
    ).resolve()


def _list_session_names(client: HoumaoServerClient) -> set[str]:
    """Return the current CAO-compatible session names visible through the pair."""

    return {session.id for session in client.list_sessions()}


def _select_port(requested_port: int | None) -> int:
    """Select one loopback port for the demo-owned server."""

    if requested_port is not None:
        return requested_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_is_available(port: int) -> bool:
    """Return whether one requested loopback port is free to bind."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _expected_session_name(requested_session_name: str | None) -> str | None:
    """Return the expected resolved CAO-compatible session name when explicit."""

    if requested_session_name is None or not requested_session_name.strip():
        return None
    stripped = requested_session_name.strip()
    return stripped if stripped.startswith("cao-") else f"cao-{stripped}"


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

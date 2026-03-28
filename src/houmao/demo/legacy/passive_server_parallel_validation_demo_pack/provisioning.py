"""Provisioning primitives for the passive-server parallel validation demo pack."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
from typing import Any

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.native_launch_resolver import resolve_native_launch_target
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.backends.tmux_runtime import tmux_session_exists
from houmao.agents.realm_controller.gateway_models import GatewayRequestPayloadSubmitPromptV1
from houmao.agents.realm_controller.loaders import parse_env_file
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record_by_agent_id
from houmao.agents.realm_controller.runtime import RuntimeSessionController, start_runtime_session
from houmao.demo.legacy.launch_support import resolve_demo_preset_launch
from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.models import (
    DEFAULT_AGENT_PROFILE,
    DEFAULT_COMPAT_CODEX_WARMUP_SECONDS,
    DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS,
    DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS,
    DEFAULT_DEMO_PACK_DIRNAME,
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    DEFAULT_HEALTH_TIMEOUT_SECONDS,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_OLD_SERVER_PORT,
    DEFAULT_PASSIVE_SERVER_PORT,
    DEFAULT_REQUEST_POLL_INTERVAL_SECONDS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_ROLE_NAME,
    executable_for_provider,
    tool_for_provider,
)
from houmao.owned_paths import (
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
    AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.passive_server.client import PassiveServerClient
from houmao.passive_server.models import PassiveHeadlessLaunchRequest
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentHistoryResponse,
    HoumaoManagedAgentStateResponse,
)
from houmao.server.pair_client import PairAuthorityClientProtocol, resolve_pair_authority_client
from houmao.srv_ctrl.commands.managed_agents import (
    _local_tui_runtime_for_controller,
    attach_gateway,
    resolve_managed_agent_target,
)
from houmao.srv_ctrl.commands.runtime_artifacts import materialize_headless_launch_request


class SuiteError(RuntimeError):
    """Raised when the parallel-validation workflow cannot complete successfully."""


@dataclass(frozen=True)
class ProviderFixture:
    """Tracked asset metadata for one supported provider."""

    provider: str
    tool: str
    config_profile: str
    credential_profile: str
    blueprint_name: str


@dataclass(frozen=True)
class FixturePaths:
    """Tracked demo-pack asset paths consumed by the validation workflow."""

    repo_root: Path
    pack_dir: Path
    agent_def_dir: Path
    project_template_dir: Path
    shared_prompt_path: Path
    gateway_prompt_path: Path
    headless_prompt_path: Path


@dataclass(frozen=True)
class SuitePaths:
    """Resolved output-root layout for one dual-authority validation run."""

    run_root: Path
    control_dir: Path
    logs_dir: Path
    state_path: Path
    report_path: Path
    sanitized_report_path: Path
    shared_runtime_root: Path
    registry_root: Path
    jobs_root: Path
    workdirs_root: Path
    interactive_workdir: Path
    headless_workdir: Path
    old_server_dir: Path
    old_server_logs_dir: Path
    old_server_runtime_root: Path
    old_server_home_dir: Path
    passive_server_dir: Path
    passive_server_logs_dir: Path
    phases_dir: Path


@dataclass
class ArtifactRecorder:
    """Monotonic JSON artifact writer for one artifact subtree."""

    root: Path
    next_index: int = 1

    def write_json(self, *, label: str, payload: Any) -> Path:
        """Write one JSON payload under the recorder root."""

        self.root.mkdir(parents=True, exist_ok=True)
        safe_label = _sanitize_label(label)
        path = self.root / f"{self.next_index:03d}-{safe_label}.json"
        self.next_index += 1
        _write_json(path, payload)
        return path


@dataclass(frozen=True)
class ParallelConfig:
    """Operator-provided configuration for one parallel validation run."""

    provider: str
    pack_dir: Path | None = None
    output_root: Path | None = None
    old_server_port: int = DEFAULT_OLD_SERVER_PORT
    passive_server_port: int = DEFAULT_PASSIVE_SERVER_PORT
    health_timeout_seconds: float = DEFAULT_HEALTH_TIMEOUT_SECONDS
    discovery_timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    request_poll_interval_seconds: float = DEFAULT_REQUEST_POLL_INTERVAL_SECONDS
    history_limit: int = DEFAULT_HISTORY_LIMIT
    compat_shell_ready_timeout_seconds: float = DEFAULT_COMPAT_SHELL_READY_TIMEOUT_SECONDS
    compat_provider_ready_timeout_seconds: float = DEFAULT_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS
    compat_codex_warmup_seconds: float = DEFAULT_COMPAT_CODEX_WARMUP_SECONDS


_PROVIDER_FIXTURES: dict[str, ProviderFixture] = {
    "claude_code": ProviderFixture(
        provider="claude_code",
        tool="claude",
        config_profile="default",
        credential_profile="personal-a-default",
        blueprint_name="server-api-smoke-claude.yaml",
    ),
    "codex": ProviderFixture(
        provider="codex",
        tool="codex",
        config_profile="yunwu-openai",
        credential_profile="yunwu-openai",
        blueprint_name="server-api-smoke-codex.yaml",
    ),
}


def resolve_fixture_paths(pack_dir: Path | None = None) -> FixturePaths:
    """Resolve the tracked demo-pack asset paths used by the validation workflow."""

    repo_root = Path(__file__).resolve().parents[4]
    resolved_pack_dir = (
        pack_dir.resolve()
        if pack_dir is not None
        else (repo_root / "scripts" / "demo" / DEFAULT_DEMO_PACK_DIRNAME).resolve()
    )
    return FixturePaths(
        repo_root=repo_root,
        pack_dir=resolved_pack_dir,
        agent_def_dir=(resolved_pack_dir / "agents").resolve(),
        project_template_dir=(resolved_pack_dir / "inputs" / "project-template").resolve(),
        shared_prompt_path=(resolved_pack_dir / "inputs" / "shared_prompt.txt").resolve(),
        gateway_prompt_path=(resolved_pack_dir / "inputs" / "gateway_prompt.txt").resolve(),
        headless_prompt_path=(resolved_pack_dir / "inputs" / "headless_prompt.txt").resolve(),
    )


def build_suite_paths(*, pack_dir: Path, output_root: Path | None, run_slug: str) -> SuitePaths:
    """Build and create the demo-owned run-root layout."""

    run_root = (
        output_root.resolve()
        if output_root is not None
        else (pack_dir / "outputs" / "runs" / run_slug).resolve()
    )
    if run_root.exists() and any(run_root.iterdir()):
        raise SuiteError(f"Demo output root already exists and is not empty: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)
    paths = SuitePaths(
        run_root=run_root,
        control_dir=(run_root / "control").resolve(),
        logs_dir=(run_root / "logs").resolve(),
        state_path=(run_root / "control" / "demo_state.json").resolve(),
        report_path=(run_root / "report.json").resolve(),
        sanitized_report_path=(run_root / "report.sanitized.json").resolve(),
        shared_runtime_root=(run_root / "runtime").resolve(),
        registry_root=(run_root / "registry").resolve(),
        jobs_root=(run_root / "jobs").resolve(),
        workdirs_root=(run_root / "workdirs").resolve(),
        interactive_workdir=(run_root / "workdirs" / "interactive").resolve(),
        headless_workdir=(run_root / "workdirs" / "headless").resolve(),
        old_server_dir=(run_root / "control" / "old_server").resolve(),
        old_server_logs_dir=(run_root / "logs" / "old_server").resolve(),
        old_server_runtime_root=(run_root / "old_server_runtime").resolve(),
        old_server_home_dir=(run_root / "old_server_home").resolve(),
        passive_server_dir=(run_root / "control" / "passive_server").resolve(),
        passive_server_logs_dir=(run_root / "logs" / "passive_server").resolve(),
        phases_dir=(run_root / "control" / "phases").resolve(),
    )
    for path in (
        paths.control_dir,
        paths.logs_dir,
        paths.shared_runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.workdirs_root,
        paths.old_server_dir,
        paths.old_server_logs_dir,
        paths.old_server_runtime_root,
        paths.old_server_home_dir,
        paths.passive_server_dir,
        paths.passive_server_logs_dir,
        paths.phases_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def load_suite_paths(run_root: Path) -> SuitePaths:
    """Project one existing run root into the suite path layout."""

    resolved_run_root = run_root.resolve()
    return SuitePaths(
        run_root=resolved_run_root,
        control_dir=(resolved_run_root / "control").resolve(),
        logs_dir=(resolved_run_root / "logs").resolve(),
        state_path=(resolved_run_root / "control" / "demo_state.json").resolve(),
        report_path=(resolved_run_root / "report.json").resolve(),
        sanitized_report_path=(resolved_run_root / "report.sanitized.json").resolve(),
        shared_runtime_root=(resolved_run_root / "runtime").resolve(),
        registry_root=(resolved_run_root / "registry").resolve(),
        jobs_root=(resolved_run_root / "jobs").resolve(),
        workdirs_root=(resolved_run_root / "workdirs").resolve(),
        interactive_workdir=(resolved_run_root / "workdirs" / "interactive").resolve(),
        headless_workdir=(resolved_run_root / "workdirs" / "headless").resolve(),
        old_server_dir=(resolved_run_root / "control" / "old_server").resolve(),
        old_server_logs_dir=(resolved_run_root / "logs" / "old_server").resolve(),
        old_server_runtime_root=(resolved_run_root / "old_server_runtime").resolve(),
        old_server_home_dir=(resolved_run_root / "old_server_home").resolve(),
        passive_server_dir=(resolved_run_root / "control" / "passive_server").resolve(),
        passive_server_logs_dir=(resolved_run_root / "logs" / "passive_server").resolve(),
        phases_dir=(resolved_run_root / "control" / "phases").resolve(),
    )


def validate_config(config: ParallelConfig) -> None:
    """Require all configured timeout values and ports to be valid."""

    if config.provider not in _PROVIDER_FIXTURES:
        raise SuiteError(f"Unsupported provider `{config.provider}`.")
    if config.old_server_port == config.passive_server_port:
        raise SuiteError("Old-server and passive-server ports must be different.")
    timeout_fields = {
        "health_timeout_seconds": config.health_timeout_seconds,
        "discovery_timeout_seconds": config.discovery_timeout_seconds,
        "request_timeout_seconds": config.request_timeout_seconds,
        "request_poll_interval_seconds": config.request_poll_interval_seconds,
        "compat_shell_ready_timeout_seconds": config.compat_shell_ready_timeout_seconds,
        "compat_provider_ready_timeout_seconds": config.compat_provider_ready_timeout_seconds,
        "compat_codex_warmup_seconds": config.compat_codex_warmup_seconds,
    }
    for name, value in timeout_fields.items():
        if value <= 0.0:
            raise SuiteError(f"`{name}` must be > 0, got {value!r}.")
    if config.history_limit <= 0:
        raise SuiteError(f"`history_limit` must be > 0, got {config.history_limit!r}.")


def run_preflight(
    *,
    config: ParallelConfig,
    fixtures: FixturePaths,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Run prerequisite checks and return the redacted report plus merged env."""

    fixture = _provider_fixture(config.provider)
    missing: list[str] = []
    executables: dict[str, str | None] = {
        "pixi": shutil.which("pixi"),
        "git": shutil.which("git"),
        "tmux": shutil.which("tmux"),
        executable_for_provider(config.provider): shutil.which(
            executable_for_provider(config.provider)
        ),
    }
    for executable_name, resolved_path in executables.items():
        if resolved_path is None:
            missing.append(f"missing executable `{executable_name}` on PATH")

    for label, path in {
        "pack_dir": fixtures.pack_dir,
        "agent_def_dir": fixtures.agent_def_dir,
        "project_template_dir": fixtures.project_template_dir,
        "shared_prompt_path": fixtures.shared_prompt_path,
        "gateway_prompt_path": fixtures.gateway_prompt_path,
        "headless_prompt_path": fixtures.headless_prompt_path,
    }.items():
        if not path.exists():
            missing.append(f"missing fixture path `{label}`: {path}")

    if not _is_port_available(config.old_server_port):
        missing.append(f"old server port is unavailable: {config.old_server_port}")
    if not _is_port_available(config.passive_server_port):
        missing.append(f"passive server port is unavailable: {config.passive_server_port}")

    fixture_report, credential_env, fixture_missing = _provider_fixture_report(
        fixtures=fixtures,
        fixture=fixture,
    )
    missing.extend(fixture_missing)

    report = {
        "checked_at_utc": _utc_now(),
        "provider": config.provider,
        "tool": fixture.tool,
        "executables": executables,
        "ports": {
            "old_server": config.old_server_port,
            "passive_server": config.passive_server_port,
        },
        "fixtures": fixture_report,
        "credential_env_var_names": sorted(credential_env),
        "missing": missing,
    }
    return report, credential_env, missing


def start_old_server(
    *,
    config: ParallelConfig,
    fixtures: FixturePaths,
    paths: SuitePaths,
    credential_env: Mapping[str, str],
) -> dict[str, Any]:
    """Start the demo-owned old `houmao-server` subprocess and wait for health."""

    api_base_url = f"http://127.0.0.1:{config.old_server_port}"
    server_env = dict(os.environ)
    server_env["HOME"] = str(paths.old_server_home_dir)
    server_env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.shared_runtime_root)
    server_env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    server_env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    server_env[AGENT_DEF_DIR_ENV_VAR] = str(fixtures.agent_def_dir)
    for name, value in credential_env.items():
        server_env[name] = value

    stdout_path = paths.old_server_logs_dir / "houmao-server.stdout.log"
    stderr_path = paths.old_server_logs_dir / "houmao-server.stderr.log"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            "pixi",
            "run",
            "python",
            "-m",
            "houmao.server",
            "serve",
            "--api-base-url",
            api_base_url,
            "--runtime-root",
            str(paths.old_server_runtime_root),
            "--compat-provider-ready-timeout-seconds",
            str(config.compat_provider_ready_timeout_seconds),
        ],
        cwd=str(fixtures.repo_root),
        env=server_env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        start_new_session=True,
    )
    stdout_handle.close()
    stderr_handle.close()

    resolution = _wait_for_pair_health(
        base_url=api_base_url,
        expected_service="houmao-server",
        timeout_seconds=config.health_timeout_seconds,
        request_timeout_seconds=config.request_timeout_seconds,
    )
    current_instance = resolution.client.current_instance()
    server_info = {
        "api_base_url": api_base_url,
        "pid": process.pid,
        "houmao_service": resolution.health.houmao_service,
        "shared_runtime_root": str(paths.shared_runtime_root),
        "registry_root": str(paths.registry_root),
        "jobs_root": str(paths.jobs_root),
        "old_server_runtime_root": str(paths.old_server_runtime_root),
        "old_server_home_dir": str(paths.old_server_home_dir),
        "stdout_log_path": str(stdout_path),
        "stderr_log_path": str(stderr_path),
        "credential_env_var_names": sorted(credential_env),
        "health": _json_ready(resolution.health),
        "current_instance": _json_ready(current_instance),
    }
    _write_json(paths.old_server_dir / "start.json", server_info)
    return server_info


def start_passive_server(
    *,
    config: ParallelConfig,
    fixtures: FixturePaths,
    paths: SuitePaths,
    credential_env: Mapping[str, str],
) -> dict[str, Any]:
    """Start the demo-owned `houmao-passive-server` subprocess and wait for health."""

    api_base_url = f"http://127.0.0.1:{config.passive_server_port}"
    server_env = dict(os.environ)
    server_env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.shared_runtime_root)
    server_env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    server_env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    server_env[AGENT_DEF_DIR_ENV_VAR] = str(fixtures.agent_def_dir)
    for name, value in credential_env.items():
        server_env[name] = value

    stdout_path = paths.passive_server_logs_dir / "houmao-passive-server.stdout.log"
    stderr_path = paths.passive_server_logs_dir / "houmao-passive-server.stderr.log"
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            "pixi",
            "run",
            "python",
            "-m",
            "houmao.passive_server",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(config.passive_server_port),
            "--runtime-root",
            str(paths.shared_runtime_root),
        ],
        cwd=str(fixtures.repo_root),
        env=server_env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        start_new_session=True,
    )
    stdout_handle.close()
    stderr_handle.close()

    resolution = _wait_for_pair_health(
        base_url=api_base_url,
        expected_service="houmao-passive-server",
        timeout_seconds=config.health_timeout_seconds,
        request_timeout_seconds=config.request_timeout_seconds,
    )
    current_instance = resolution.client.current_instance()
    server_info = {
        "api_base_url": api_base_url,
        "pid": process.pid,
        "houmao_service": resolution.health.houmao_service,
        "shared_runtime_root": str(paths.shared_runtime_root),
        "registry_root": str(paths.registry_root),
        "jobs_root": str(paths.jobs_root),
        "stdout_log_path": str(stdout_path),
        "stderr_log_path": str(stderr_path),
        "credential_env_var_names": sorted(credential_env),
        "health": _json_ready(resolution.health),
        "current_instance": _json_ready(current_instance),
    }
    _write_json(paths.passive_server_dir / "start.json", server_info)
    return server_info


def stop_pair_server(
    *,
    server_info: Mapping[str, Any] | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop one pair authority and return shutdown evidence."""

    if server_info is None:
        return {"status": "not_started"}
    pid = int(server_info["pid"])
    api_base_url = str(server_info["api_base_url"])
    shutdown_status: dict[str, Any] = {"pid": pid, "api_base_url": api_base_url}

    try:
        client = resolve_pair_authority_client(
            base_url=api_base_url,
            timeout_seconds=1.0,
        ).client
        response = client.shutdown_server()
        shutdown_status["shutdown_response"] = _json_ready(response)
    except Exception as exc:
        shutdown_status["shutdown_error"] = str(exc)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            shutdown_status["status"] = "stopped"
            return shutdown_status
        time.sleep(0.25)
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        shutdown_status["status"] = "stopped"
        return shutdown_status

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_exists(pid):
            shutdown_status["status"] = "stopped"
            return shutdown_status
        time.sleep(0.25)

    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        shutdown_status["status"] = "stopped"
        return shutdown_status
    shutdown_status["status"] = "forced"
    return shutdown_status


def provision_shared_interactive(
    *,
    config: ParallelConfig,
    fixtures: FixturePaths,
    paths: SuitePaths,
    credential_env: Mapping[str, str],
    run_slug: str,
) -> tuple[RuntimeSessionController, dict[str, Any]]:
    """Build and launch the shared local interactive validation agent."""

    _recreate_directory(paths.interactive_workdir)
    shutil.copytree(fixtures.project_template_dir, paths.interactive_workdir, dirs_exist_ok=True)
    agent_name = normalize_agent_identity_name(
        f"parallel-shared-{tool_for_provider(config.provider)}-{run_slug}"
    ).canonical_name
    runtime_env = _shared_environment(paths=paths, agent_def_dir=fixtures.agent_def_dir)
    runtime_env.update(credential_env)

    with _temporary_environment_bindings(runtime_env):
        target = resolve_native_launch_target(
            selector=DEFAULT_AGENT_PROFILE,
            provider=config.provider,
            working_directory=paths.interactive_workdir,
        )
        build_result = build_brain_home(
            BuildRequest(
                agent_def_dir=target.agent_def_dir,
                runtime_root=paths.shared_runtime_root,
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
            runtime_root=paths.shared_runtime_root,
            backend=resolved_backend,
            working_directory=paths.interactive_workdir,
            agent_name=agent_name,
            tmux_session_name=agent_name,
        )

    _wait_for_controller_launch_readiness(controller=controller, config=config)
    if controller.agent_identity is None:
        raise SuiteError("Shared interactive launch did not publish an agent name.")
    if controller.agent_id is None:
        raise SuiteError("Shared interactive launch did not publish an authoritative agent id.")
    if controller.tmux_session_name is None:
        raise SuiteError("Shared interactive launch did not publish a tmux session name.")

    payload = {
        "provider": config.provider,
        "tool": tool_for_provider(config.provider),
        "backend": controller.launch_plan.backend,
        "agent_profile": DEFAULT_AGENT_PROFILE,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "tmux_session_name": controller.tmux_session_name,
        "manifest_path": str(controller.manifest_path.resolve()),
        "session_root": str(controller.manifest_path.parent.resolve()),
        "workdir": str(paths.interactive_workdir),
        "gateway_attached": False,
    }
    _write_json(paths.phases_dir / "start-shared-agent.json", payload)
    return controller, payload


def capture_inspect_phase(
    *,
    state: Mapping[str, Any],
    paths: SuitePaths,
    history_limit: int,
) -> dict[str, Any]:
    """Capture shared interactive discovery and managed-state parity across both authorities."""

    phase_dir = (paths.phases_dir / "inspect").resolve()
    phase_dir.mkdir(parents=True, exist_ok=True)
    shared_agent = dict(state.get("shared_agent", {}))
    agent_ref = str(shared_agent.get("agent_id"))
    old_client, passive_client = _pair_clients_from_state(state)
    discovery_timeout_seconds = _float_from_state_config(state, "discovery_timeout_seconds")
    request_poll_interval_seconds = _float_from_state_config(state, "request_poll_interval_seconds")

    old_list: Any = None
    passive_list: Any = None
    old_identity: Any = None
    passive_identity: Any = None
    deadline = time.monotonic() + discovery_timeout_seconds
    last_error = "shared agent did not become visible on both authorities"
    while time.monotonic() < deadline:
        try:
            old_list = old_client.list_managed_agents()
            passive_list = passive_client.list_managed_agents()
            old_identity = old_client.get_managed_agent(agent_ref)
            passive_identity = passive_client.get_managed_agent(agent_ref)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(request_poll_interval_seconds)
            continue
        if _list_contains_agent(old_list, agent_ref) and _list_contains_agent(
            passive_list, agent_ref
        ):
            break
        last_error = f"shared agent `{agent_ref}` missing from one authority list response"
        time.sleep(request_poll_interval_seconds)
    else:
        raise SuiteError(
            f"Timed out waiting for shared interactive agent visibility on both authorities: {last_error}"
        )

    old_state = old_client.get_managed_agent_state(agent_ref)
    passive_state = passive_client.get_managed_agent_state(agent_ref)
    old_detail = old_client.get_managed_agent_state_detail(agent_ref)
    passive_detail = passive_client.get_managed_agent_state_detail(agent_ref)
    old_history = old_client.get_managed_agent_history(agent_ref, limit=history_limit)
    passive_history = passive_client.get_managed_agent_history(agent_ref, limit=history_limit)

    _write_json(phase_dir / "old-list.json", old_list)
    _write_json(phase_dir / "passive-list.json", passive_list)
    _write_json(phase_dir / "old-identity.json", old_identity)
    _write_json(phase_dir / "passive-identity.json", passive_identity)
    _write_json(phase_dir / "old-state.json", old_state)
    _write_json(phase_dir / "passive-state.json", passive_state)
    _write_json(phase_dir / "old-detail.json", old_detail)
    _write_json(phase_dir / "passive-detail.json", passive_detail)
    _write_json(phase_dir / "old-history.json", old_history)
    _write_json(phase_dir / "passive-history.json", passive_history)

    old_identity_normalized = _normalized_identity(old_identity)
    passive_identity_normalized = _normalized_identity(passive_identity)
    old_state_normalized = _normalized_state(old_state)
    passive_state_normalized = _normalized_state(passive_state)
    old_detail_normalized = _normalized_detail(old_detail)
    passive_detail_normalized = _normalized_detail(passive_detail)
    old_history_normalized = _normalized_history(old_history)
    passive_history_normalized = _normalized_history(passive_history)

    comparisons = {
        "identity": _comparison_result(old_identity_normalized, passive_identity_normalized),
        "state": _comparison_result(old_state_normalized, passive_state_normalized),
        "detail": _comparison_result(old_detail_normalized, passive_detail_normalized),
        "history": _comparison_result(old_history_normalized, passive_history_normalized),
    }
    comparison_summary = {name: payload["ok"] for name, payload in comparisons.items()}
    result = {
        "ok": all(comparison_summary.values()),
        "agent_ref": agent_ref,
        "list_ok": _list_contains_agent(old_list, agent_ref)
        and _list_contains_agent(passive_list, agent_ref),
        "resolve_ok": True,
        "comparison_summary": comparison_summary,
        "comparisons": comparisons,
        "old_history_normalized": old_history_normalized,
        "passive_history_normalized": passive_history_normalized,
    }
    _write_json(phase_dir / "result.json", result)
    return result


def capture_gateway_phase(
    *,
    state: Mapping[str, Any],
    paths: SuitePaths,
    gateway_prompt_text: str,
    history_limit: int,
) -> dict[str, Any]:
    """Attach one local gateway and validate passive-server gateway prompting."""

    phase_dir = (paths.phases_dir / "gateway").resolve()
    phase_dir.mkdir(parents=True, exist_ok=True)
    shared_agent = dict(state.get("shared_agent", {}))
    agent_ref = str(shared_agent.get("agent_id"))
    old_client, passive_client = _pair_clients_from_state(state)
    request_timeout_seconds = _float_from_state_config(state, "request_timeout_seconds")
    request_poll_interval_seconds = _float_from_state_config(state, "request_poll_interval_seconds")

    with _temporary_environment_bindings(_shared_environment_from_state(state)):
        target = resolve_managed_agent_target(agent_id=agent_ref, agent_name=None, port=None)
        attach_status = attach_gateway(target)

    baseline_old_state = old_client.get_managed_agent_state(agent_ref)
    baseline_old_history = old_client.get_managed_agent_history(agent_ref, limit=history_limit)
    baseline_passive_state = passive_client.get_managed_agent_state(agent_ref)
    baseline_passive_history = passive_client.get_managed_agent_history(
        agent_ref, limit=history_limit
    )

    accepted = passive_client.submit_managed_agent_gateway_request(
        agent_ref,
        HoumaoManagedAgentGatewayRequestCreate(
            kind="submit_prompt",
            payload=GatewayRequestPayloadSubmitPromptV1(prompt=gateway_prompt_text),
        ),
    )

    old_after_state, old_after_history, old_progress_observed = _wait_for_progress(
        client=old_client,
        agent_ref=agent_ref,
        history_limit=history_limit,
        baseline_state=baseline_old_state,
        baseline_history=baseline_old_history,
        timeout_seconds=request_timeout_seconds,
        poll_interval_seconds=request_poll_interval_seconds,
    )
    passive_after_state, passive_after_history, passive_progress_observed = _wait_for_progress(
        client=passive_client,
        agent_ref=agent_ref,
        history_limit=history_limit,
        baseline_state=baseline_passive_state,
        baseline_history=baseline_passive_history,
        timeout_seconds=request_timeout_seconds,
        poll_interval_seconds=request_poll_interval_seconds,
    )

    _write_json(phase_dir / "attach-status.json", attach_status)
    _write_json(phase_dir / "accepted.json", accepted)
    _write_json(phase_dir / "old-state-before.json", baseline_old_state)
    _write_json(phase_dir / "old-history-before.json", baseline_old_history)
    _write_json(phase_dir / "passive-state-before.json", baseline_passive_state)
    _write_json(phase_dir / "passive-history-before.json", baseline_passive_history)
    _write_json(phase_dir / "old-state-after.json", old_after_state)
    _write_json(phase_dir / "old-history-after.json", old_after_history)
    _write_json(phase_dir / "passive-state-after.json", passive_after_state)
    _write_json(phase_dir / "passive-history-after.json", passive_after_history)

    result = {
        "ok": old_progress_observed and passive_progress_observed,
        "agent_ref": agent_ref,
        "gateway_attached": True,
        "attach_status": _json_ready(attach_status),
        "accepted": _json_ready(accepted),
        "old_progress_observed": old_progress_observed,
        "passive_progress_observed": passive_progress_observed,
    }
    _write_json(phase_dir / "result.json", result)
    return result


def capture_headless_phase(
    *,
    state: Mapping[str, Any],
    paths: SuitePaths,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Launch one passive headless agent and verify old-server visibility."""

    phase_dir = (paths.phases_dir / "headless").resolve()
    phase_dir.mkdir(parents=True, exist_ok=True)
    config = _config_from_state(state)
    fixtures = resolve_fixture_paths(Path(str(state["pack_dir"])))
    credential_env = _credential_env_from_preflight(state)
    passive_client = PassiveServerClient(
        str(dict(state.get("authorities", {})).get("passive_server", {}).get("api_base_url")),
        timeout_seconds=config.request_timeout_seconds,
        create_timeout_seconds=config.request_timeout_seconds,
    )
    old_client = HoumaoServerClient(
        str(dict(state.get("authorities", {})).get("old_server", {}).get("api_base_url")),
        timeout_seconds=config.request_timeout_seconds,
        create_timeout_seconds=config.request_timeout_seconds,
    )

    _recreate_directory(paths.headless_workdir)
    shutil.copytree(fixtures.project_template_dir, paths.headless_workdir, dirs_exist_ok=True)
    runtime_env = _shared_environment(paths=paths, agent_def_dir=fixtures.agent_def_dir)
    runtime_env.update(credential_env)
    with _temporary_environment_bindings(runtime_env):
        base_request = materialize_headless_launch_request(
            runtime_root=paths.shared_runtime_root,
            provider=config.provider,
            agent_profile=DEFAULT_AGENT_PROFILE,
            working_directory=paths.headless_workdir,
        )
    headless_agent_name = normalize_agent_identity_name(
        f"parallel-headless-{tool_for_provider(config.provider)}-{_timestamp_slug()}"
    ).canonical_name
    headless_agent_id = derive_agent_id_from_name(headless_agent_name)
    request_model = PassiveHeadlessLaunchRequest(
        tool=base_request.tool,
        working_directory=base_request.working_directory,
        agent_def_dir=base_request.agent_def_dir,
        brain_manifest_path=base_request.brain_manifest_path,
        role_name=base_request.role_name,
        agent_name=headless_agent_name,
        agent_id=headless_agent_id,
        mailbox=base_request.mailbox,
    )
    launch_response = passive_client.launch_passive_headless_agent(request_model)

    deadline = time.monotonic() + config.discovery_timeout_seconds
    last_error = "old server did not expose the passive headless agent"
    old_identity: Any = None
    while time.monotonic() < deadline:
        try:
            old_identity = old_client.get_managed_agent(launch_response.tracked_agent_id)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(config.request_poll_interval_seconds)
            continue
        if old_identity.transport == "headless":
            break
        last_error = f"old server resolved unexpected transport {old_identity.transport!r}"
        time.sleep(config.request_poll_interval_seconds)
    else:
        raise SuiteError(
            "Timed out waiting for passive headless launch visibility on the old server: "
            f"{last_error}"
        )

    passive_state = passive_client.get_managed_agent_state(launch_response.tracked_agent_id)
    passive_detail = passive_client.get_managed_agent_state_detail(launch_response.tracked_agent_id)
    old_state = old_client.get_managed_agent_state(launch_response.tracked_agent_id)
    old_detail = old_client.get_managed_agent_state_detail(launch_response.tracked_agent_id)

    headless_agent = {
        "agent_name": launch_response.agent_name,
        "agent_id": headless_agent_id,
        "tracked_agent_id": launch_response.tracked_agent_id,
        "manifest_path": launch_response.manifest_path,
        "session_root": launch_response.session_root,
        "workdir": str(paths.headless_workdir),
    }
    result = {
        "ok": True,
        "launch_ok": True,
        "old_visibility_ok": True,
        "tracked_agent_id": launch_response.tracked_agent_id,
    }
    _write_json(phase_dir / "request.json", request_model)
    _write_json(phase_dir / "launch-response.json", launch_response)
    _write_json(phase_dir / "old-identity.json", old_identity)
    _write_json(phase_dir / "old-state.json", old_state)
    _write_json(phase_dir / "old-detail.json", old_detail)
    _write_json(phase_dir / "passive-state.json", passive_state)
    _write_json(phase_dir / "passive-detail.json", passive_detail)
    _write_json(phase_dir / "result.json", result)
    return headless_agent, result


def capture_stop_phase(
    *,
    state: Mapping[str, Any],
    paths: SuitePaths,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop the shared interactive agent through the passive server and verify disappearance."""

    phase_dir = (paths.phases_dir / "stop").resolve()
    phase_dir.mkdir(parents=True, exist_ok=True)
    shared_agent = dict(state.get("shared_agent", {}))
    headless_agent_raw = state.get("headless_agent")
    headless_agent = dict(headless_agent_raw) if isinstance(headless_agent_raw, Mapping) else None
    passive_client = PassiveServerClient(
        str(dict(state.get("authorities", {})).get("passive_server", {}).get("api_base_url"))
    )
    old_client = HoumaoServerClient(
        str(dict(state.get("authorities", {})).get("old_server", {}).get("api_base_url"))
    )

    shared_stop = passive_client.stop_managed_agent(str(shared_agent.get("agent_id")))
    discovery_timeout_seconds = _float_from_state_config(state, "discovery_timeout_seconds")
    poll_interval_seconds = _float_from_state_config(state, "request_poll_interval_seconds")
    passive_absent = _wait_for_absence(
        client=passive_client,
        agent_ref=str(shared_agent.get("agent_id")),
        timeout_seconds=discovery_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    old_absent = _wait_for_absence(
        client=old_client,
        agent_ref=str(shared_agent.get("agent_id")),
        timeout_seconds=discovery_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    with _temporary_environment_bindings(_shared_environment_from_state(state)):
        registry_absent = (
            resolve_live_agent_record_by_agent_id(str(shared_agent.get("agent_id"))) is None
        )
    tmux_absent = not tmux_session_exists(session_name=str(shared_agent.get("tmux_session_name")))

    headless_cleanup: dict[str, Any] | None = None
    if headless_agent is not None:
        try:
            headless_cleanup = _json_ready(
                passive_client.stop_managed_agent(str(headless_agent.get("tracked_agent_id")))
            )
        except Exception as exc:
            headless_cleanup = {"error": str(exc)}

    old_shutdown = stop_pair_server(
        server_info=dict(state.get("authorities", {})).get("old_server"),
        timeout_seconds=timeout_seconds,
    )
    passive_shutdown = stop_pair_server(
        server_info=dict(state.get("authorities", {})).get("passive_server"),
        timeout_seconds=timeout_seconds,
    )
    shutdown_ok = old_shutdown.get("status") in {"stopped", "forced"} and passive_shutdown.get(
        "status"
    ) in {"stopped", "forced"}

    result = {
        "ok": passive_absent and old_absent and registry_absent and tmux_absent and shutdown_ok,
        "shared_stop": _json_ready(shared_stop),
        "passive_absent": passive_absent,
        "old_absent": old_absent,
        "registry_absent": registry_absent,
        "tmux_absent": tmux_absent,
        "headless_cleanup": headless_cleanup,
        "old_server_shutdown": old_shutdown,
        "passive_server_shutdown": passive_shutdown,
    }
    _write_json(phase_dir / "result.json", result)
    return result


def _provider_fixture(provider: str) -> ProviderFixture:
    """Return tracked fixture metadata for one supported provider."""

    if provider not in _PROVIDER_FIXTURES:
        raise SuiteError(f"Unsupported provider `{provider}`.")
    return _PROVIDER_FIXTURES[provider]


def _provider_fixture_report(
    *,
    fixtures: FixturePaths,
    fixture: ProviderFixture,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Build one provider-specific fixture report and collect missing prerequisites."""

    resolved_launch = resolve_demo_preset_launch(
        agent_def_dir=fixtures.agent_def_dir,
        preset_path=(
            fixtures.agent_def_dir
            / "roles"
            / DEFAULT_ROLE_NAME
            / "presets"
            / fixture.tool
            / f"{fixture.config_profile}.yaml"
        ),
    )
    blueprint_path = resolved_launch.preset_path
    recipe_path = resolved_launch.preset_path
    role_path = resolved_launch.role_prompt_path
    credential_env_path = resolved_launch.auth_env_path
    config_path = resolved_launch.setup_path / (
        "settings.json" if fixture.tool == "claude" else "config.toml"
    )

    missing: list[str] = []
    for label, path in {
        "blueprint_path": blueprint_path,
        "recipe_path": recipe_path,
        "role_path": role_path,
        "credential_env_path": credential_env_path,
        "config_path": config_path,
    }.items():
        if path is None or not path.exists():
            missing.append(f"missing provider fixture `{fixture.provider}` {label}: {path}")

    recipe = resolved_launch.preset
    recipe_operator_prompt_mode: str | None = recipe.operator_prompt_mode
    if recipe.tool != fixture.tool:
        missing.append(
            f"fixture recipe tool mismatch for `{fixture.provider}`: expected `{fixture.tool}`, got `{recipe.tool}`."
        )
    if recipe.operator_prompt_mode != "unattended":
        missing.append(
            f"fixture recipe `{recipe_path}` must set `launch.operator_prompt_mode: unattended`."
        )

    env_values = (
        parse_env_file(credential_env_path)
        if credential_env_path is not None and credential_env_path.is_file()
        else {}
    )
    required_key_names: list[str]
    if fixture.tool == "codex":
        required_key_names = ["OPENAI_API_KEY"]
        if not env_values.get("OPENAI_API_KEY", "").strip():
            missing.append(
                f"Codex validation requires `OPENAI_API_KEY` in `{credential_env_path}` for `{fixture.provider}`."
            )
    else:
        required_key_names = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"]
        if not any(env_values.get(name, "").strip() for name in required_key_names):
            missing.append(
                f"Claude validation requires `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` in `{credential_env_path}`."
            )

    report = {
        "provider": fixture.provider,
        "tool": fixture.tool,
        "blueprint_path": str(blueprint_path),
        "recipe_path": str(recipe_path),
        "role_path": str(role_path),
        "config_path": str(config_path),
        "credential_env_path": str(credential_env_path),
        "config_profile": fixture.config_profile,
        "credential_profile": fixture.credential_profile,
        "recipe_operator_prompt_mode": recipe_operator_prompt_mode,
        "required_key_names": required_key_names,
        "selected_env_var_names": sorted(name for name, value in env_values.items() if value),
    }
    return report, env_values, missing


def _wait_for_pair_health(
    *,
    base_url: str,
    expected_service: str,
    timeout_seconds: float,
    request_timeout_seconds: float,
) -> Any:
    """Wait until one pair authority answers healthy status."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "authority did not become healthy"
    while time.monotonic() < deadline:
        try:
            resolution = resolve_pair_authority_client(
                base_url=base_url,
                timeout_seconds=request_timeout_seconds,
                create_timeout_seconds=request_timeout_seconds,
            )
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if (
            resolution.health.status == "ok"
            and resolution.health.houmao_service == expected_service
        ):
            return resolution
        last_error = resolution.health.model_dump_json()
        time.sleep(0.25)
    raise SuiteError(f"Timed out waiting for authority health at {base_url}: {last_error}")


def _pair_clients_from_state(
    state: Mapping[str, Any],
) -> tuple[PairAuthorityClientProtocol, PassiveServerClient]:
    """Build typed pair clients from persisted state."""

    authorities = dict(state.get("authorities", {}))
    config = _config_from_state(state)
    old_base_url = str(dict(authorities.get("old_server", {})).get("api_base_url"))
    passive_base_url = str(dict(authorities.get("passive_server", {})).get("api_base_url"))
    old_client = resolve_pair_authority_client(
        base_url=old_base_url,
        timeout_seconds=config.request_timeout_seconds,
        create_timeout_seconds=config.request_timeout_seconds,
    ).client
    passive_client = PassiveServerClient(
        passive_base_url,
        timeout_seconds=config.request_timeout_seconds,
        create_timeout_seconds=config.request_timeout_seconds,
    )
    return old_client, passive_client


def _shared_environment(*, paths: SuitePaths, agent_def_dir: Path) -> dict[str, str]:
    """Return the run-local environment used for registry and runtime ownership."""

    return {
        AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR: str(paths.shared_runtime_root.resolve()),
        AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR: str(paths.registry_root.resolve()),
        AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR: str(paths.jobs_root.resolve()),
        AGENT_DEF_DIR_ENV_VAR: str(agent_def_dir.resolve()),
    }


def _shared_environment_from_state(state: Mapping[str, Any]) -> dict[str, str]:
    """Rebuild the shared runtime environment from persisted state."""

    config = _mapping(dict(state.get("config", {})).get("roots", {}), context="state.config.roots")
    return {
        AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR: str(
            Path(str(config["shared_runtime_root"])).resolve()
        ),
        AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR: str(Path(str(config["registry_root"])).resolve()),
        AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR: str(Path(str(config["jobs_root"])).resolve()),
        AGENT_DEF_DIR_ENV_VAR: str(Path(str(state["agent_def_dir"])).resolve()),
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


def _wait_for_controller_launch_readiness(
    *,
    controller: RuntimeSessionController,
    config: ParallelConfig,
) -> None:
    """Wait for the local interactive session to become available and ready."""

    runtime = _local_tui_runtime_for_controller(controller)
    poll_interval = config.request_poll_interval_seconds

    shell_deadline = time.monotonic() + config.compat_shell_ready_timeout_seconds
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
        raise SuiteError(
            "Timed out waiting for the shared local session shell to become available: "
            f"{last_error}"
        )

    provider_deadline = time.monotonic() + config.compat_provider_ready_timeout_seconds
    last_error = "tracked terminal did not reach ready posture"
    while time.monotonic() < provider_deadline:
        try:
            tracked_state = runtime.refresh_once()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(poll_interval)
            continue
        if tracked_state.surface.ready_posture == "yes":
            if controller.launch_plan.tool == "codex" and config.compat_codex_warmup_seconds > 0:
                time.sleep(config.compat_codex_warmup_seconds)
            return
        last_error = (
            f"ready_posture={tracked_state.surface.ready_posture} "
            f"turn_phase={tracked_state.turn.phase}"
        )
        time.sleep(poll_interval)
    raise SuiteError(
        f"Timed out waiting for the shared local provider to become ready: {last_error}"
    )


def _wait_for_progress(
    *,
    client: PairAuthorityClientProtocol,
    agent_ref: str,
    history_limit: int,
    baseline_state: HoumaoManagedAgentStateResponse,
    baseline_history: HoumaoManagedAgentHistoryResponse,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[HoumaoManagedAgentStateResponse, HoumaoManagedAgentHistoryResponse, bool]:
    """Wait for observable progress in state or history after a managed request."""

    baseline_state_signature = _normalized_state(baseline_state)
    baseline_history_signature = _normalized_history(baseline_history)
    deadline = time.monotonic() + timeout_seconds
    latest_state = baseline_state
    latest_history = baseline_history
    while time.monotonic() < deadline:
        latest_state = client.get_managed_agent_state(agent_ref)
        latest_history = client.get_managed_agent_history(agent_ref, limit=history_limit)
        if _normalized_state(latest_state) != baseline_state_signature:
            return latest_state, latest_history, True
        if _normalized_history(latest_history) != baseline_history_signature:
            return latest_state, latest_history, True
        time.sleep(poll_interval_seconds)
    return latest_state, latest_history, False


def _wait_for_absence(
    *,
    client: PairAuthorityClientProtocol,
    agent_ref: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> bool:
    """Wait until one authority no longer resolves the selected agent."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            client.get_managed_agent(agent_ref)
        except Exception:
            return True
        time.sleep(poll_interval_seconds)
    return False


def _list_contains_agent(response: Any, agent_ref: str) -> bool:
    """Return whether one list response includes the selected agent id."""

    agents = getattr(response, "agents", [])
    for agent in agents:
        tracked_agent_id = getattr(agent, "tracked_agent_id", None)
        discovered_agent_id = getattr(agent, "agent_id", None)
        if tracked_agent_id == agent_ref or discovered_agent_id == agent_ref:
            return True
    return False


def _comparison_result(
    old_payload: dict[str, Any], passive_payload: dict[str, Any]
) -> dict[str, Any]:
    """Build one explicit parity-comparison result payload."""

    return {
        "ok": old_payload == passive_payload,
        "old": old_payload,
        "passive": passive_payload,
    }


def _normalized_identity(identity: Any) -> dict[str, Any]:
    """Normalize one managed-agent identity into a stable comparison payload."""

    return {
        "tracked_agent_id": getattr(identity, "tracked_agent_id", None),
        "transport": getattr(identity, "transport", None),
        "tool": getattr(identity, "tool", None),
        "session_name": getattr(identity, "session_name", None),
        "tmux_session_name": getattr(identity, "tmux_session_name", None),
        "manifest_path": getattr(identity, "manifest_path", None),
        "session_root": getattr(identity, "session_root", None),
        "agent_name": getattr(identity, "agent_name", None),
        "agent_id": getattr(identity, "agent_id", None),
    }


def _normalized_state(state: HoumaoManagedAgentStateResponse) -> dict[str, Any]:
    """Normalize one managed-agent state payload into a stable comparison payload."""

    return {
        "availability": state.availability,
        "turn_phase": state.turn.phase,
        "last_turn_result": state.last_turn.result,
        "has_gateway": state.gateway is not None,
        "has_mailbox": state.mailbox is not None,
        "diagnostic_count": len(state.diagnostics),
    }


def _normalized_detail(detail: HoumaoManagedAgentDetailResponse) -> dict[str, Any]:
    """Normalize one managed-agent detail payload into a stable comparison payload."""

    if detail.detail.transport == "tui":
        diagnostic_count = sum(
            1
            for item in (
                detail.detail.diagnostics.probe_error,
                detail.detail.diagnostics.parse_error,
            )
            if item is not None
        )
        return {
            "transport": "tui",
            "ready_posture": detail.detail.surface.ready_posture,
            "stable": detail.detail.stability.stable,
            "parsed_surface_present": detail.detail.parsed_surface is not None,
            "diagnostic_count": diagnostic_count,
        }
    return {
        "transport": "headless",
        "can_accept_prompt_now": detail.detail.can_accept_prompt_now,
        "interruptible": detail.detail.interruptible,
        "last_turn_status": detail.detail.last_turn_status,
        "diagnostic_count": len(detail.detail.diagnostics),
    }


def _normalized_history(history: HoumaoManagedAgentHistoryResponse) -> dict[str, Any]:
    """Normalize one managed-agent history payload into a stable comparison payload."""

    entries = list(history.entries)
    latest = max(entries, key=lambda entry: entry.recorded_at_utc) if entries else None
    return {
        "entry_count": len(entries),
        "latest_turn_phase": None if latest is None else latest.turn_phase,
        "latest_last_turn_result": None if latest is None else latest.last_turn_result,
        "latest_summary": None if latest is None else latest.summary,
    }


def _credential_env_from_preflight(state: Mapping[str, Any]) -> dict[str, str]:
    """Return the preflight-selected credential env values preserved in control data."""

    preflight = _mapping(state.get("preflight", {}), context="state.preflight")
    env_payload = preflight.get("credential_env")
    if not isinstance(env_payload, Mapping):
        return {}
    return {str(name): str(value) for name, value in env_payload.items()}


def _config_from_state(state: Mapping[str, Any]) -> ParallelConfig:
    """Rebuild the parallel config from persisted state."""

    config_payload = _mapping(state.get("config", {}), context="state.config")
    return ParallelConfig(
        provider=str(config_payload["provider"]),
        pack_dir=Path(str(state["pack_dir"])),
        output_root=Path(str(state["run_root"])),
        old_server_port=int(
            _mapping(config_payload.get("ports", {}), context="state.config.ports")["old_server"]
        ),
        passive_server_port=int(
            _mapping(config_payload.get("ports", {}), context="state.config.ports")[
                "passive_server"
            ]
        ),
        health_timeout_seconds=float(config_payload["health_timeout_seconds"]),
        discovery_timeout_seconds=float(config_payload["discovery_timeout_seconds"]),
        request_timeout_seconds=float(config_payload["request_timeout_seconds"]),
        request_poll_interval_seconds=float(config_payload["request_poll_interval_seconds"]),
        history_limit=int(config_payload["history_limit"]),
        compat_shell_ready_timeout_seconds=float(
            config_payload["compat_shell_ready_timeout_seconds"]
        ),
        compat_provider_ready_timeout_seconds=float(
            config_payload["compat_provider_ready_timeout_seconds"]
        ),
        compat_codex_warmup_seconds=float(config_payload["compat_codex_warmup_seconds"]),
    )


def _float_from_state_config(state: Mapping[str, Any], key: str) -> float:
    """Return one float config value from persisted state."""

    config = _mapping(state.get("config", {}), context="state.config")
    return float(config[key])


def _mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping or raise a stable workflow error."""

    if not isinstance(value, Mapping):
        raise SuiteError(f"{context} must be a mapping")
    return dict(value)


def _recreate_directory(path: Path) -> None:
    """Delete and recreate one directory."""

    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _is_port_available(port: int) -> bool:
    """Return whether one loopback port can be bound right now."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _sanitize_label(value: str) -> str:
    """Return one filesystem-safe artifact label."""

    safe = "".join(character if character.isalnum() else "-" for character in value.strip().lower())
    safe = safe.strip("-")
    return safe or "snapshot"


def _timestamp_slug() -> str:
    """Return one UTC timestamp slug for artifact roots and identities."""

    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def _pid_exists(pid: int) -> bool:
    """Return whether one process id still exists."""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _json_ready(payload: Any) -> Any:
    """Convert one payload into a JSON-ready structure."""

    if payload is None:
        return None
    if isinstance(payload, Path):
        return str(payload)
    if isinstance(payload, (str, int, float, bool)):
        return payload
    if isinstance(payload, Mapping):
        return {str(key): _json_ready(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple, set)):
        return [_json_ready(item) for item in payload]
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    if hasattr(payload, "__dict__"):
        return {key: _json_ready(value) for key, value in payload.__dict__.items()}
    return str(payload)

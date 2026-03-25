"""Manual houmao-server managed-agent API live suite implementation.

This module owns the operator-run live suite that provisions one isolated
`houmao-server`, launches real Claude and Codex managed-agent lanes across TUI
and headless transports, verifies the public HTTP routes, and preserves
artifacts under one suite-owned run root.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
from typing import Any, Literal

from houmao.agents.realm_controller.backends.claude_bootstrap import (
    ensure_claude_home_bootstrap,
)
from houmao.agents.realm_controller.backends.codex_bootstrap import ensure_codex_home_bootstrap
from houmao.agents.brain_builder import load_brain_recipe
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.loaders import parse_env_file
from houmao.owned_paths import (
    AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR,
    AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoHeadlessTurnStatusResponse,
    HoumaoInstallAgentProfileRequest,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentSubmitPromptRequest,
    HoumaoRegisterLaunchRequest,
)
from houmao.srv_ctrl.commands.runtime_artifacts import (
    materialize_delegated_launch,
    materialize_headless_launch_request,
)

LaneTransport = Literal["tui", "headless"]
ToolName = Literal["claude", "codex"]

_FIXTURE_AGENT_PROFILE = "server-api-smoke"
_FIXTURE_ROLE_NAME = "server-api-smoke"
_DEFAULT_PROMPT_TEMPLATE = (
    "Reply with one short sentence confirming the live suite request for lane "
    "{lane_id} using tool {tool} over {transport}."
)
_HEADLESS_TERMINAL_STATUSES = frozenset({"completed", "failed", "interrupted"})


class SuiteError(RuntimeError):
    """Raised when the manual live suite cannot complete successfully."""


@dataclass(frozen=True)
class LaneDefinition:
    """Static metadata for one supported live lane."""

    lane_id: str
    slug: str
    tool: ToolName
    transport: LaneTransport
    compatibility_provider: str
    config_profile: str
    credential_profile: str


@dataclass(frozen=True)
class FixturePaths:
    """Tracked fixture paths consumed by the live suite."""

    repo_root: Path
    agent_def_dir: Path
    compatibility_profile_path: Path
    dummy_project_fixture: Path


@dataclass(frozen=True)
class SuitePaths:
    """Resolved suite-owned output paths for one live run."""

    run_root: Path
    runtime_root: Path
    registry_root: Path
    jobs_root: Path
    home_dir: Path
    logs_dir: Path
    server_logs_dir: Path
    server_runtime_root: Path
    suite_http_dir: Path
    server_dir: Path
    lanes_root: Path


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


@dataclass
class LaneRuntime:
    """Mutable lane runtime state and artifact locations."""

    definition: LaneDefinition
    lane_root: Path
    workdir: Path
    http_recorder: ArtifactRecorder
    requested_session_name: str | None = None
    requested_agent_name: str | None = None
    requested_agent_id: str | None = None
    session_name: str | None = None
    terminal_id: str | None = None
    tmux_window_name: str | None = None
    tracked_agent_id: str | None = None
    manifest_path: str | None = None
    session_root: str | None = None
    launch_metadata: dict[str, Any] | None = None
    route_verification: dict[str, Any] | None = None
    prompt_verification: dict[str, Any] | None = None
    stop_result: dict[str, Any] | None = None

    def summary_payload(self) -> dict[str, Any]:
        """Return one JSON-ready lane summary payload."""

        return {
            "lane_id": self.definition.lane_id,
            "tool": self.definition.tool,
            "transport": self.definition.transport,
            "requested_session_name": self.requested_session_name,
            "requested_agent_name": self.requested_agent_name,
            "requested_agent_id": self.requested_agent_id,
            "session_name": self.session_name,
            "terminal_id": self.terminal_id,
            "tmux_window_name": self.tmux_window_name,
            "tracked_agent_id": self.tracked_agent_id,
            "manifest_path": self.manifest_path,
            "session_root": self.session_root,
            "launch_metadata": self.launch_metadata,
            "route_verification": self.route_verification,
            "prompt_verification": self.prompt_verification,
            "stop_result": self.stop_result,
            "lane_root": str(self.lane_root),
            "workdir": str(self.workdir),
            "http_snapshot_count": self.http_recorder.next_index - 1,
        }


@dataclass(frozen=True)
class SuiteConfig:
    """Operator-provided configuration for one live suite run."""

    selected_lane_ids: tuple[str, ...] = ()
    output_root: Path | None = None
    port: int | None = None
    compat_http_timeout_seconds: float = 20.0
    compat_create_timeout_seconds: float = 90.0
    compat_provider_ready_timeout_seconds: float = 90.0
    health_timeout_seconds: float = 30.0
    prompt_timeout_seconds: float = 120.0
    prompt_poll_interval_seconds: float = 2.0


_LANE_DEFINITIONS: dict[str, LaneDefinition] = {
    "claude-tui": LaneDefinition(
        lane_id="claude-tui",
        slug="cltui",
        tool="claude",
        transport="tui",
        compatibility_provider="claude_code",
        config_profile="default",
        credential_profile="personal-a-default",
    ),
    "codex-tui": LaneDefinition(
        lane_id="codex-tui",
        slug="cdxtui",
        tool="codex",
        transport="tui",
        compatibility_provider="codex",
        config_profile="yunwu-openai",
        credential_profile="yunwu-openai",
    ),
    "claude-headless": LaneDefinition(
        lane_id="claude-headless",
        slug="clhd",
        tool="claude",
        transport="headless",
        compatibility_provider="claude_code",
        config_profile="default",
        credential_profile="personal-a-default",
    ),
    "codex-headless": LaneDefinition(
        lane_id="codex-headless",
        slug="cdxhd",
        tool="codex",
        transport="headless",
        compatibility_provider="codex",
        config_profile="yunwu-openai",
        credential_profile="yunwu-openai",
    ),
}
LANE_IDS = tuple(_LANE_DEFINITIONS.keys())


def run_suite(config: SuiteConfig) -> dict[str, Any]:
    """Run the manual live suite and return the final summary payload."""

    _validate_config(config)
    selected_lanes = _resolve_selected_lanes(config.selected_lane_ids)
    fixtures = _resolve_fixture_paths()
    run_slug = _timestamp_slug()
    paths = _build_suite_paths(
        repo_root=fixtures.repo_root,
        output_root=config.output_root,
        run_slug=run_slug,
    )
    recorders = {
        "suite_http": ArtifactRecorder(paths.suite_http_dir),
    }

    preflight_report, credential_env, preflight_missing = _run_preflight(
        fixtures=fixtures,
        selected_lanes=selected_lanes,
    )
    _write_json(paths.run_root / "config.json", _config_payload(config=config, paths=paths))
    _write_json(paths.run_root / "preflight.json", preflight_report)
    if preflight_missing:
        raise SuiteError(
            "Live-suite preflight failed before server startup:\n- "
            + "\n- ".join(preflight_missing)
        )

    lane_runtimes = _prepare_lane_runtimes(
        fixtures=fixtures,
        paths=paths,
        selected_lanes=selected_lanes,
        run_slug=run_slug,
    )

    started_at_utc = _utc_now()
    server_info: dict[str, Any] | None = None
    client: HoumaoServerClient | None = None
    failure_message: str | None = None
    final_summary: dict[str, Any] | None = None

    try:
        print(f"[preflight] selected lanes: {', '.join(lane.lane_id for lane in selected_lanes)}")
        server_info = _start_suite_server(
            config=config,
            fixtures=fixtures,
            paths=paths,
            suite_http_recorder=recorders["suite_http"],
            credential_env=credential_env,
        )
        client = HoumaoServerClient(
            server_info["api_base_url"],
            timeout_seconds=config.compat_http_timeout_seconds,
            create_timeout_seconds=config.compat_create_timeout_seconds,
        )
        for lane_runtime in lane_runtimes:
            _provision_lane(
                client=client,
                config=config,
                fixtures=fixtures,
                paths=paths,
                server_info=server_info,
                lane_runtime=lane_runtime,
                run_slug=run_slug,
            )
        _verify_shared_routes(
            client=client,
            suite_http_recorder=recorders["suite_http"],
            lane_runtimes=lane_runtimes,
        )
        for lane_runtime in lane_runtimes:
            _verify_lane_routes(client=client, lane_runtime=lane_runtime)
        for lane_runtime in lane_runtimes:
            _submit_prompt_and_verify(
                client=client,
                config=config,
                lane_runtime=lane_runtime,
            )
    except Exception as exc:
        failure_message = str(exc)
        raise SuiteError(str(exc)) from exc
    finally:
        cleanup_results = _cleanup_lanes(client=client, lane_runtimes=lane_runtimes)
        shutdown_result = _stop_suite_server(server_info, timeout_seconds=10.0)
        _write_json(paths.server_dir / "shutdown.json", shutdown_result)
        final_summary = {
            "suite": "houmao-server-agent-api-live-suite",
            "status": "passed" if failure_message is None else "failed",
            "started_at_utc": started_at_utc,
            "completed_at_utc": _utc_now(),
            "run_root": str(paths.run_root),
            "selected_lanes": [lane.lane_id for lane in selected_lanes],
            "api_base_url": server_info["api_base_url"] if server_info is not None else None,
            "preflight": preflight_report,
            "server": server_info,
            "lane_cleanup": cleanup_results,
            "server_shutdown": shutdown_result,
            "failure": failure_message,
            "lanes": {lane.definition.lane_id: lane.summary_payload() for lane in lane_runtimes},
        }
        _write_json(paths.run_root / "summary.json", final_summary)

    assert final_summary is not None
    return final_summary


def _validate_config(config: SuiteConfig) -> None:
    """Require all configured timeout values to be positive."""

    timeout_fields = {
        "compat_http_timeout_seconds": config.compat_http_timeout_seconds,
        "compat_create_timeout_seconds": config.compat_create_timeout_seconds,
        "compat_provider_ready_timeout_seconds": config.compat_provider_ready_timeout_seconds,
        "health_timeout_seconds": config.health_timeout_seconds,
        "prompt_timeout_seconds": config.prompt_timeout_seconds,
        "prompt_poll_interval_seconds": config.prompt_poll_interval_seconds,
    }
    for name, value in timeout_fields.items():
        if value <= 0:
            raise SuiteError(f"`{name}` must be > 0, got {value!r}.")


def _resolve_selected_lanes(selected_lane_ids: Sequence[str]) -> list[LaneDefinition]:
    """Resolve the selected lanes, defaulting to the full four-lane suite."""

    if not selected_lane_ids:
        return list(_LANE_DEFINITIONS.values())
    resolved: list[LaneDefinition] = []
    seen: set[str] = set()
    for lane_id in selected_lane_ids:
        if lane_id not in _LANE_DEFINITIONS:
            raise SuiteError(f"Unknown lane `{lane_id}`.")
        if lane_id in seen:
            continue
        seen.add(lane_id)
        resolved.append(_LANE_DEFINITIONS[lane_id])
    return resolved


def _resolve_fixture_paths() -> FixturePaths:
    """Resolve the tracked fixture paths used by the live suite."""

    repo_root = Path(__file__).resolve().parents[3]
    return FixturePaths(
        repo_root=repo_root,
        agent_def_dir=(repo_root / "tests" / "fixtures" / "agents").resolve(),
        compatibility_profile_path=(
            repo_root
            / "tests"
            / "fixtures"
            / "agents"
            / "compatibility-profiles"
            / "server-api-smoke.md"
        ).resolve(),
        dummy_project_fixture=(
            repo_root / "tests" / "fixtures" / "dummy-projects" / "mailbox-demo-python"
        ).resolve(),
    )


def _build_suite_paths(*, repo_root: Path, output_root: Path | None, run_slug: str) -> SuitePaths:
    """Build and create the suite-owned run-root layout."""

    run_root = (
        output_root.resolve()
        if output_root is not None
        else (
            repo_root / "tmp" / "tests" / "houmao-server-agent-api-live-suite" / run_slug
        ).resolve()
    )
    if run_root.exists() and any(run_root.iterdir()):
        raise SuiteError(f"Suite output root already exists and is not empty: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)
    paths = SuitePaths(
        run_root=run_root,
        runtime_root=(run_root / "runtime").resolve(),
        registry_root=(run_root / "registry").resolve(),
        jobs_root=(run_root / "jobs").resolve(),
        home_dir=(run_root / "home").resolve(),
        logs_dir=(run_root / "logs").resolve(),
        server_logs_dir=(run_root / "logs" / "server").resolve(),
        server_runtime_root=(run_root / "server-runtime").resolve(),
        suite_http_dir=(run_root / "http").resolve(),
        server_dir=(run_root / "server").resolve(),
        lanes_root=(run_root / "lanes").resolve(),
    )
    for path in (
        paths.runtime_root,
        paths.registry_root,
        paths.jobs_root,
        paths.home_dir,
        paths.logs_dir,
        paths.server_logs_dir,
        paths.server_runtime_root,
        paths.suite_http_dir,
        paths.server_dir,
        paths.lanes_root,
    ):
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _run_preflight(
    *,
    fixtures: FixturePaths,
    selected_lanes: Sequence[LaneDefinition],
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Run prerequisite checks and return the redacted report plus merged env."""

    missing: list[str] = []
    executables: dict[str, str | None] = {
        "tmux": shutil.which("tmux"),
    }
    for tool_name in sorted({lane.tool for lane in selected_lanes}):
        executables[tool_name] = shutil.which(tool_name)
    for executable_name, resolved_path in executables.items():
        if resolved_path is None:
            missing.append(f"missing executable `{executable_name}` on PATH")

    fixture_paths = {
        "agent_def_dir": fixtures.agent_def_dir,
        "compatibility_profile_path": fixtures.compatibility_profile_path,
        "dummy_project_fixture": fixtures.dummy_project_fixture,
    }
    for label, path in fixture_paths.items():
        if not path.exists():
            missing.append(f"missing fixture path `{label}`: {path}")

    lane_fixture_reports: dict[str, dict[str, Any]] = {}
    merged_env: dict[str, str] = {}
    for lane in selected_lanes:
        lane_fixture_report, lane_env_names, lane_env_values, lane_missing = _lane_fixture_report(
            fixtures=fixtures,
            lane=lane,
        )
        lane_fixture_reports[lane.lane_id] = lane_fixture_report
        for name in lane_env_names:
            merged_env[name] = lane_env_values[name]
        missing.extend(lane_missing)

    report = {
        "checked_at_utc": _utc_now(),
        "selected_lanes": [lane.lane_id for lane in selected_lanes],
        "executables": executables,
        "fixtures": {key: str(value) for key, value in fixture_paths.items()},
        "lane_fixtures": lane_fixture_reports,
        "credential_env_var_names": sorted(merged_env),
        "missing": missing,
    }
    return report, merged_env, missing


def _lane_fixture_report(
    *,
    fixtures: FixturePaths,
    lane: LaneDefinition,
) -> tuple[dict[str, Any], list[str], dict[str, str], list[str]]:
    """Build one lane-specific fixture report and collect missing prerequisites."""

    recipe_path = (
        fixtures.agent_def_dir
        / "brains"
        / "brain-recipes"
        / lane.tool
        / f"{_FIXTURE_AGENT_PROFILE}-default.yaml"
    ).resolve()
    blueprint_path = (
        fixtures.agent_def_dir / "blueprints" / f"{_FIXTURE_AGENT_PROFILE}-{lane.tool}.yaml"
    ).resolve()
    role_path = (
        fixtures.agent_def_dir / "roles" / _FIXTURE_ROLE_NAME / "system-prompt.md"
    ).resolve()
    credential_env_path = (
        fixtures.agent_def_dir
        / "brains"
        / "api-creds"
        / lane.tool
        / lane.credential_profile
        / "env"
        / "vars.env"
    ).resolve()
    config_path = (
        fixtures.agent_def_dir
        / "brains"
        / "cli-configs"
        / lane.tool
        / lane.config_profile
        / ("settings.json" if lane.tool == "claude" else "config.toml")
    ).resolve()
    missing: list[str] = []
    for label, path in {
        "recipe_path": recipe_path,
        "blueprint_path": blueprint_path,
        "role_path": role_path,
        "credential_env_path": credential_env_path,
        "config_path": config_path,
    }.items():
        if not path.exists():
            missing.append(f"missing lane fixture `{lane.lane_id}` {label}: {path}")

    recipe_operator_prompt_mode: str | None = None
    if recipe_path.is_file():
        recipe = load_brain_recipe(recipe_path)
        recipe_operator_prompt_mode = recipe.operator_prompt_mode
        if recipe.tool != lane.tool:
            missing.append(
                f"lane fixture `{lane.lane_id}` recipe tool mismatch: "
                f"expected `{lane.tool}`, got `{recipe.tool}`."
            )
        if recipe.config_profile != lane.config_profile:
            missing.append(
                f"lane fixture `{lane.lane_id}` recipe config_profile mismatch: "
                f"expected `{lane.config_profile}`, got `{recipe.config_profile}`."
            )
        if recipe.credential_profile != lane.credential_profile:
            missing.append(
                f"lane fixture `{lane.lane_id}` recipe credential_profile mismatch: "
                f"expected `{lane.credential_profile}`, got `{recipe.credential_profile}`."
            )
        if lane.transport == "tui" and recipe.operator_prompt_mode != "unattended":
            missing.append(
                f"lane fixture `{lane.lane_id}` recipe `{recipe_path}` must set "
                "`launch_policy.operator_prompt_mode: unattended` for no-prompt TUI startup."
            )

    extra_fixture_checks: dict[str, str] = {}
    if lane.tool == "claude":
        claude_template_path = (
            fixtures.agent_def_dir
            / "brains"
            / "api-creds"
            / "claude"
            / lane.credential_profile
            / "files"
            / "claude_state.template.json"
        ).resolve()
        extra_fixture_checks["claude_state_template_path"] = str(claude_template_path)
        if lane.transport == "headless" and not claude_template_path.is_file():
            missing.append(
                "missing Claude headless bootstrap template for "
                f"`{lane.lane_id}`: {claude_template_path}"
            )

    env_values = parse_env_file(credential_env_path) if credential_env_path.is_file() else {}
    env_names: list[str]
    required_key_names: list[str]
    if lane.tool == "codex":
        required_key_names = ["OPENAI_API_KEY"]
        env_names = [
            name
            for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID")
            if name in env_values
        ]
        if not env_values.get("OPENAI_API_KEY", "").strip():
            missing.append(
                "Codex API-key-mode is required for the live suite; "
                f"`{credential_env_path}` must set `OPENAI_API_KEY` for `{lane.lane_id}`."
            )
    else:
        required_key_names = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"]
        env_names = [
            name
            for name in (
                "ANTHROPIC_API_KEY",
                "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_BASE_URL",
                "ANTHROPIC_MODEL",
                "ANTHROPIC_SMALL_FAST_MODEL",
                "CLAUDE_CODE_SUBAGENT_MODEL",
                "ANTHROPIC_DEFAULT_OPUS_MODEL",
                "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            )
            if name in env_values
        ]
        if not any(env_values.get(name, "").strip() for name in required_key_names):
            missing.append(
                "Claude live lanes require at least one credential key in "
                f"`{credential_env_path}` for `{lane.lane_id}` "
                "(expected `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`)."
            )

    report = {
        "recipe_path": str(recipe_path),
        "blueprint_path": str(blueprint_path),
        "role_path": str(role_path),
        "config_path": str(config_path),
        "credential_env_path": str(credential_env_path),
        "config_profile": lane.config_profile,
        "credential_profile": lane.credential_profile,
        "recipe_operator_prompt_mode": recipe_operator_prompt_mode,
        "selected_env_var_names": sorted(env_names),
        "required_key_names": required_key_names,
        **extra_fixture_checks,
    }
    return report, env_names, env_values, missing


def _prepare_lane_runtimes(
    *,
    fixtures: FixturePaths,
    paths: SuitePaths,
    selected_lanes: Sequence[LaneDefinition],
    run_slug: str,
) -> list[LaneRuntime]:
    """Create per-lane workdirs and recorders before server startup."""

    runtimes: list[LaneRuntime] = []
    for lane in selected_lanes:
        lane_root = (paths.lanes_root / lane.lane_id).resolve()
        lane_root.mkdir(parents=True, exist_ok=True)
        workdir = (lane_root / "workdir").resolve()
        shutil.copytree(fixtures.dummy_project_fixture, workdir)
        runtimes.append(
            LaneRuntime(
                definition=lane,
                lane_root=lane_root,
                workdir=workdir,
                http_recorder=ArtifactRecorder((lane_root / "http").resolve()),
            )
        )
        _write_json(
            lane_root / "fixture.json",
            {
                "lane_id": lane.lane_id,
                "run_slug": run_slug,
                "copied_fixture": str(fixtures.dummy_project_fixture),
                "workdir": str(workdir),
            },
        )
    return runtimes


def _start_suite_server(
    *,
    config: SuiteConfig,
    fixtures: FixturePaths,
    paths: SuitePaths,
    suite_http_recorder: ArtifactRecorder,
    credential_env: Mapping[str, str],
) -> dict[str, Any]:
    """Start the suite-owned houmao-server subprocess and wait for health."""

    api_base_url = f"http://127.0.0.1:{_choose_port(config.port)}"
    server_env = dict(os.environ)
    server_env["HOME"] = str(paths.home_dir)
    server_env[AGENTSYS_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.runtime_root)
    server_env[AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    server_env[AGENTSYS_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    for name, value in credential_env.items():
        server_env[name] = value

    stdout_path = paths.server_logs_dir / "houmao-server.stdout.log"
    stderr_path = paths.server_logs_dir / "houmao-server.stderr.log"
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
            str(paths.server_runtime_root),
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
    client = HoumaoServerClient(
        api_base_url,
        timeout_seconds=config.compat_http_timeout_seconds,
        create_timeout_seconds=config.compat_create_timeout_seconds,
    )
    health_payload = _wait_for_server_health(
        client=client,
        timeout_seconds=config.health_timeout_seconds,
    )
    current_instance = _record_route_call(
        recorder=suite_http_recorder,
        label="current-instance",
        method="GET",
        path="/houmao/server/current-instance",
        request_payload=None,
        callback=lambda: client.current_instance(),
    )
    server_info = {
        "api_base_url": api_base_url,
        "pid": process.pid,
        "runtime_root": str(paths.runtime_root),
        "registry_root": str(paths.registry_root),
        "jobs_root": str(paths.jobs_root),
        "home_dir": str(paths.home_dir),
        "server_runtime_root": str(paths.server_runtime_root),
        "stdout_log_path": str(stdout_path),
        "stderr_log_path": str(stderr_path),
        "credential_env_var_names": sorted(credential_env),
        "health": _json_ready(health_payload),
        "current_instance": _json_ready(current_instance),
    }
    _write_json(paths.server_dir / "start.json", server_info)
    return server_info


def _wait_for_server_health(
    *,
    client: HoumaoServerClient,
    timeout_seconds: float,
) -> Any:
    """Wait until the suite-owned houmao-server reports healthy status."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "server did not become healthy"
    while time.monotonic() < deadline:
        try:
            health = client.health_extended()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.25)
            continue
        if health.status == "ok" and health.houmao_service == "houmao-server":
            return health
        last_error = health.model_dump_json()
        time.sleep(0.25)
    raise SuiteError(f"Timed out waiting for suite-owned houmao-server health: {last_error}")


def _provision_lane(
    *,
    client: HoumaoServerClient,
    config: SuiteConfig,
    fixtures: FixturePaths,
    paths: SuitePaths,
    server_info: Mapping[str, Any],
    lane_runtime: LaneRuntime,
    run_slug: str,
) -> None:
    """Provision one selected lane using its transport-specific flow."""

    print(f"[lane:{lane_runtime.definition.lane_id}] provision")
    if lane_runtime.definition.transport == "tui":
        _provision_tui_lane(
            client=client,
            config=config,
            fixtures=fixtures,
            paths=paths,
            server_info=server_info,
            lane_runtime=lane_runtime,
            run_slug=run_slug,
        )
        return
    _provision_headless_lane(
        client=client,
        fixtures=fixtures,
        paths=paths,
        lane_runtime=lane_runtime,
        run_slug=run_slug,
    )


def _provision_tui_lane(
    *,
    client: HoumaoServerClient,
    config: SuiteConfig,
    fixtures: FixturePaths,
    paths: SuitePaths,
    server_info: Mapping[str, Any],
    lane_runtime: LaneRuntime,
    run_slug: str,
) -> None:
    """Provision one TUI lane through compatibility create plus registration."""

    lane = lane_runtime.definition
    requested_session_name = f"{_FIXTURE_AGENT_PROFILE}-{lane.slug}-{run_slug}"
    lane_runtime.requested_session_name = requested_session_name
    install_request = HoumaoInstallAgentProfileRequest(
        agent_source=str(fixtures.compatibility_profile_path),
        provider=lane.compatibility_provider,
        working_directory=str(fixtures.repo_root),
    )
    install_response = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="install-profile",
        method="POST",
        path="/houmao/agent-profiles/install",
        request_payload=install_request,
        callback=lambda: client.install_agent_profile(install_request),
    )
    _bootstrap_compat_home_for_tui_lane(
        fixtures=fixtures,
        lane_runtime=lane_runtime,
        server_info=server_info,
    )
    terminal = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="create-session",
        method="POST",
        path="/cao/sessions",
        request_payload={
            "provider": lane.compatibility_provider,
            "agent_profile": _FIXTURE_AGENT_PROFILE,
            "session_name": requested_session_name,
            "working_directory": str(lane_runtime.workdir),
            "create_timeout_seconds": config.compat_create_timeout_seconds,
        },
        callback=lambda: client.create_session(
            provider=lane.compatibility_provider,
            agent_profile=_FIXTURE_AGENT_PROFILE,
            session_name=requested_session_name,
            working_directory=str(lane_runtime.workdir),
        ),
    )
    manifest_path, session_root, canonical_agent_name, agent_id = materialize_delegated_launch(
        runtime_root=paths.runtime_root,
        api_base_url=client.base_url,
        session_name=terminal.session_name,
        terminal_id=terminal.id,
        tmux_window_name=terminal.name,
        provider=lane.compatibility_provider,
        agent_profile=_FIXTURE_AGENT_PROFILE,
        working_directory=lane_runtime.workdir,
    )
    register_request = HoumaoRegisterLaunchRequest(
        session_name=terminal.session_name,
        terminal_id=terminal.id,
        tool=lane.tool,
        manifest_path=str(manifest_path),
        session_root=str(session_root),
        agent_name=canonical_agent_name,
        agent_id=agent_id,
        tmux_session_name=terminal.session_name,
        tmux_window_name=terminal.name,
    )
    register_response = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="register-launch",
        method="POST",
        path="/houmao/launches/register",
        request_payload=register_request,
        callback=lambda: client.register_launch(register_request),
    )
    lane_runtime.session_name = terminal.session_name
    lane_runtime.terminal_id = terminal.id
    lane_runtime.tmux_window_name = terminal.name
    lane_runtime.requested_agent_name = canonical_agent_name
    lane_runtime.requested_agent_id = agent_id
    lane_runtime.manifest_path = str(manifest_path)
    lane_runtime.session_root = str(session_root)
    identity = _wait_for_managed_identity(
        client=client,
        lane_runtime=lane_runtime,
        expected_transport="tui",
        timeout_seconds=config.health_timeout_seconds,
    )
    lane_runtime.tracked_agent_id = identity.tracked_agent_id
    lane_runtime.launch_metadata = {
        "install_response": _json_ready(install_response),
        "create_session": _json_ready(terminal),
        "register_launch": _json_ready(register_response),
        "managed_identity": _json_ready(identity),
        "manifest_path": str(manifest_path),
        "session_root": str(session_root),
        "requested_session_name": requested_session_name,
        "canonical_agent_name": canonical_agent_name,
        "agent_id": agent_id,
    }
    _write_json(lane_runtime.lane_root / "launch.json", lane_runtime.launch_metadata)


def _bootstrap_compat_home_for_tui_lane(
    *,
    fixtures: FixturePaths,
    lane_runtime: LaneRuntime,
    server_info: Mapping[str, Any],
) -> None:
    """Seed compatibility-home state for unattended TUI launches."""

    compat_home_dir = (
        Path(str(server_info["current_instance"]["server_root"])).resolve() / "compat_home"
    )
    compat_home_dir.mkdir(parents=True, exist_ok=True)
    lane = lane_runtime.definition
    credential_env_path = (
        fixtures.agent_def_dir
        / "brains"
        / "api-creds"
        / lane.tool
        / lane.credential_profile
        / "env"
        / "vars.env"
    ).resolve()
    env_values = parse_env_file(credential_env_path)

    if lane.tool == "claude":
        settings_path = (
            fixtures.agent_def_dir
            / "brains"
            / "cli-configs"
            / "claude"
            / lane.config_profile
            / "settings.json"
        ).resolve()
        template_path = (
            fixtures.agent_def_dir
            / "brains"
            / "api-creds"
            / "claude"
            / lane.credential_profile
            / "files"
            / "claude_state.template.json"
        ).resolve()
        shutil.copy2(settings_path, compat_home_dir / "settings.json")
        shutil.copy2(template_path, compat_home_dir / "claude_state.template.json")
        ensure_claude_home_bootstrap(home_path=compat_home_dir, env=env_values)
        bootstrap_payload = {
            "tool": lane.tool,
            "compat_home_dir": str(compat_home_dir),
            "settings_path": str(settings_path),
            "template_path": str(template_path),
            "selected_env_var_names": sorted(name for name, value in env_values.items() if value),
        }
    else:
        config_path = (
            fixtures.agent_def_dir
            / "brains"
            / "cli-configs"
            / "codex"
            / lane.config_profile
            / "config.toml"
        ).resolve()
        auth_path = (
            fixtures.agent_def_dir
            / "brains"
            / "api-creds"
            / "codex"
            / lane.credential_profile
            / "files"
            / "auth.json"
        ).resolve()
        shutil.copy2(config_path, compat_home_dir / "config.toml")
        if auth_path.is_file():
            shutil.copy2(auth_path, compat_home_dir / "auth.json")
        ensure_codex_home_bootstrap(
            home_path=compat_home_dir,
            env=env_values,
            working_directory=lane_runtime.workdir,
        )
        bootstrap_payload = {
            "tool": lane.tool,
            "compat_home_dir": str(compat_home_dir),
            "config_path": str(config_path),
            "auth_path": str(auth_path) if auth_path.is_file() else None,
            "selected_env_var_names": sorted(name for name, value in env_values.items() if value),
        }
    _write_json(lane_runtime.lane_root / "compat-home-bootstrap.json", bootstrap_payload)


def _provision_headless_lane(
    *,
    client: HoumaoServerClient,
    fixtures: FixturePaths,
    paths: SuitePaths,
    lane_runtime: LaneRuntime,
    run_slug: str,
) -> None:
    """Provision one native headless lane through the managed launch route."""

    lane = lane_runtime.definition
    requested_agent_name = normalize_agent_identity_name(
        f"{_FIXTURE_AGENT_PROFILE}-{lane.slug}-{run_slug}"
    ).canonical_name
    requested_agent_id = derive_agent_id_from_name(requested_agent_name)
    lane_runtime.requested_agent_name = requested_agent_name
    lane_runtime.requested_agent_id = requested_agent_id
    with _temporary_env_var(AGENT_DEF_DIR_ENV_VAR, str(fixtures.agent_def_dir)):
        request_model = materialize_headless_launch_request(
            runtime_root=paths.runtime_root,
            provider=lane.compatibility_provider,
            agent_profile=_FIXTURE_AGENT_PROFILE,
            working_directory=lane_runtime.workdir,
        )
    request_model = request_model.model_copy(
        update={
            "agent_name": requested_agent_name,
            "agent_id": requested_agent_id,
        }
    )
    response = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="launch-headless",
        method="POST",
        path="/houmao/agents/headless/launches",
        request_payload=request_model,
        callback=lambda: client.launch_headless_agent(request_model),
    )
    lane_runtime.tracked_agent_id = response.tracked_agent_id
    lane_runtime.session_name = response.identity.tmux_session_name
    lane_runtime.tmux_window_name = response.identity.tmux_window_name
    lane_runtime.manifest_path = response.manifest_path
    lane_runtime.session_root = response.session_root
    lane_runtime.launch_metadata = {
        "launch_response": _json_ready(response),
        "managed_identity": _json_ready(response.identity),
        "requested_agent_name": requested_agent_name,
        "requested_agent_id": requested_agent_id,
        "manifest_path": response.manifest_path,
        "session_root": response.session_root,
    }
    _write_json(lane_runtime.lane_root / "launch.json", lane_runtime.launch_metadata)


def _wait_for_managed_identity(
    *,
    client: HoumaoServerClient,
    lane_runtime: LaneRuntime,
    expected_transport: LaneTransport,
    timeout_seconds: float,
) -> Any:
    """Wait until one managed lane is visible through `/houmao/agents/{agent_ref}`."""

    deadline = time.monotonic() + timeout_seconds
    last_error = "managed identity not available"
    candidate_refs = [
        ref
        for ref in (
            lane_runtime.requested_session_name,
            lane_runtime.requested_agent_name,
            lane_runtime.requested_agent_id,
            lane_runtime.session_name,
            lane_runtime.tracked_agent_id,
        )
        if ref is not None
    ]
    while time.monotonic() < deadline:
        for agent_ref in candidate_refs:
            try:
                identity = client.get_managed_agent(agent_ref)
            except Exception as exc:
                last_error = str(exc)
                continue
            if identity.transport == expected_transport:
                return identity
            last_error = (
                f"managed identity for `{agent_ref}` returned unexpected transport "
                f"{identity.transport!r}"
            )
        time.sleep(0.25)
    raise SuiteError(
        f"Timed out waiting for managed identity for `{lane_runtime.definition.lane_id}`: "
        f"{last_error}"
    )


def _verify_shared_routes(
    *,
    client: HoumaoServerClient,
    suite_http_recorder: ArtifactRecorder,
    lane_runtimes: Sequence[LaneRuntime],
) -> None:
    """Verify shared managed-agent discovery through `GET /houmao/agents`."""

    list_response = _record_route_call(
        recorder=suite_http_recorder,
        label="list-managed-agents",
        method="GET",
        path="/houmao/agents",
        request_payload=None,
        callback=client.list_managed_agents,
    )
    tracked_agent_ids = {
        lane_runtime.tracked_agent_id
        for lane_runtime in lane_runtimes
        if lane_runtime.tracked_agent_id
    }
    returned_ids = {agent.tracked_agent_id for agent in list_response.agents}
    missing = sorted(tracked_agent_ids - returned_ids)
    if missing:
        raise SuiteError(
            "Managed-agent discovery did not return every launched lane: " + ", ".join(missing)
        )


def _verify_lane_routes(*, client: HoumaoServerClient, lane_runtime: LaneRuntime) -> None:
    """Verify per-lane discovery and state routes."""

    tracked_agent_id = _require_tracked_agent_id(lane_runtime)
    identity = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="get-managed-agent",
        method="GET",
        path=f"/houmao/agents/{tracked_agent_id}",
        request_payload=None,
        callback=lambda: client.get_managed_agent(tracked_agent_id),
    )
    state = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="get-managed-agent-state",
        method="GET",
        path=f"/houmao/agents/{tracked_agent_id}/state",
        request_payload=None,
        callback=lambda: client.get_managed_agent_state(tracked_agent_id),
    )
    detail = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="get-managed-agent-state-detail",
        method="GET",
        path=f"/houmao/agents/{tracked_agent_id}/state/detail",
        request_payload=None,
        callback=lambda: client.get_managed_agent_state_detail(tracked_agent_id),
    )
    expected_transport = lane_runtime.definition.transport
    if detail.detail.transport != expected_transport:
        raise SuiteError(
            "Managed-agent detail transport mismatch for "
            f"`{lane_runtime.definition.lane_id}`: expected {expected_transport!r}, "
            f"got {detail.detail.transport!r}."
        )
    lane_runtime.route_verification = {
        "identity": _json_ready(identity),
        "state": _json_ready(state),
        "detail": _json_ready(detail),
        "expected_transport": expected_transport,
    }
    _write_json(lane_runtime.lane_root / "route-verification.json", lane_runtime.route_verification)


def _submit_prompt_and_verify(
    *,
    client: HoumaoServerClient,
    config: SuiteConfig,
    lane_runtime: LaneRuntime,
) -> None:
    """Submit one prompt through `/requests` and verify state progression."""

    tracked_agent_id = _require_tracked_agent_id(lane_runtime)
    prompt = _DEFAULT_PROMPT_TEMPLATE.format(
        lane_id=lane_runtime.definition.lane_id,
        tool=lane_runtime.definition.tool,
        transport=lane_runtime.definition.transport,
    )
    state_before = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="state-before-request",
        method="GET",
        path=f"/houmao/agents/{tracked_agent_id}/state",
        request_payload=None,
        callback=lambda: client.get_managed_agent_state(tracked_agent_id),
    )
    request_model = HoumaoManagedAgentSubmitPromptRequest(prompt=prompt)
    accepted = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="submit-request",
        method="POST",
        path=f"/houmao/agents/{tracked_agent_id}/requests",
        request_payload=request_model,
        callback=lambda: client.submit_managed_agent_request(tracked_agent_id, request_model),
    )
    state_after = _wait_for_post_request_state(
        client=client,
        lane_runtime=lane_runtime,
        state_before=state_before,
        timeout_seconds=config.prompt_timeout_seconds,
        poll_interval_seconds=config.prompt_poll_interval_seconds,
    )
    headless_turn: dict[str, Any] | None = None
    if accepted.headless_turn_id is not None:
        headless_turn = _poll_headless_turn(
            client=client,
            lane_runtime=lane_runtime,
            turn_id=accepted.headless_turn_id,
            timeout_seconds=config.prompt_timeout_seconds,
            poll_interval_seconds=config.prompt_poll_interval_seconds,
        )
    lane_runtime.prompt_verification = {
        "prompt": prompt,
        "accepted": _json_ready(accepted),
        "state_before": _json_ready(state_before),
        "state_after": _json_ready(state_after),
        "headless_turn": headless_turn,
    }
    _write_json(
        lane_runtime.lane_root / "prompt-verification.json", lane_runtime.prompt_verification
    )


def _wait_for_post_request_state(
    *,
    client: HoumaoServerClient,
    lane_runtime: LaneRuntime,
    state_before: HoumaoManagedAgentStateResponse,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> HoumaoManagedAgentStateResponse:
    """Poll `/state` until one observable post-request change appears."""

    tracked_agent_id = _require_tracked_agent_id(lane_runtime)
    baseline = _state_signature(state_before)
    deadline = time.monotonic() + timeout_seconds
    latest_state = state_before
    while time.monotonic() < deadline:
        latest_state = _record_route_call(
            recorder=lane_runtime.http_recorder,
            label="state-poll",
            method="GET",
            path=f"/houmao/agents/{tracked_agent_id}/state",
            request_payload=None,
            callback=lambda: client.get_managed_agent_state(tracked_agent_id),
        )
        if _is_observable_post_request_progress(
            state_before=state_before,
            latest_state=latest_state,
            baseline_signature=baseline,
        ):
            return latest_state
        time.sleep(poll_interval_seconds)
    raise SuiteError(
        "Timed out waiting for observable state progression after `/requests` for "
        f"`{lane_runtime.definition.lane_id}`."
    )


def _poll_headless_turn(
    *,
    client: HoumaoServerClient,
    lane_runtime: LaneRuntime,
    turn_id: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    """Poll one durable headless turn until it reaches a terminal state."""

    tracked_agent_id = _require_tracked_agent_id(lane_runtime)
    deadline = time.monotonic() + timeout_seconds
    latest_status: HoumaoHeadlessTurnStatusResponse | None = None
    while time.monotonic() < deadline:
        latest_status = _record_route_call(
            recorder=lane_runtime.http_recorder,
            label="headless-turn-status",
            method="GET",
            path=f"/houmao/agents/{tracked_agent_id}/turns/{turn_id}",
            request_payload=None,
            callback=lambda: client.get_headless_turn_status(tracked_agent_id, turn_id),
        )
        if latest_status.status in _HEADLESS_TERMINAL_STATUSES:
            break
        time.sleep(poll_interval_seconds)
    if latest_status is None or latest_status.status not in _HEADLESS_TERMINAL_STATUSES:
        raise SuiteError(
            f"Timed out waiting for headless turn `{turn_id}` to finish for "
            f"`{lane_runtime.definition.lane_id}`."
        )

    events = _record_route_call(
        recorder=lane_runtime.http_recorder,
        label="headless-turn-events",
        method="GET",
        path=f"/houmao/agents/{tracked_agent_id}/turns/{turn_id}/events",
        request_payload=None,
        callback=lambda: client.get_headless_turn_events(tracked_agent_id, turn_id),
    )
    stdout_text = client.get_headless_turn_artifact_text(
        tracked_agent_id,
        turn_id,
        artifact_name="stdout",
    )
    stderr_text = client.get_headless_turn_artifact_text(
        tracked_agent_id,
        turn_id,
        artifact_name="stderr",
    )
    turn_root = (lane_runtime.lane_root / "headless-turns" / turn_id).resolve()
    turn_root.mkdir(parents=True, exist_ok=True)
    _write_json(turn_root / "status.json", latest_status)
    _write_json(turn_root / "events.json", events)
    (turn_root / "stdout.txt").write_text(stdout_text, encoding="utf-8")
    (turn_root / "stderr.txt").write_text(stderr_text, encoding="utf-8")
    return {
        "status": _json_ready(latest_status),
        "events": _json_ready(events),
        "stdout_path": str((turn_root / "stdout.txt").resolve()),
        "stderr_path": str((turn_root / "stderr.txt").resolve()),
    }


def _cleanup_lanes(
    *,
    client: HoumaoServerClient | None,
    lane_runtimes: Sequence[LaneRuntime],
) -> dict[str, Any]:
    """Stop all launched lanes before suite-owned server shutdown."""

    results: dict[str, Any] = {}
    for lane_runtime in reversed(lane_runtimes):
        lane_result = _cleanup_lane(client=client, lane_runtime=lane_runtime)
        lane_runtime.stop_result = lane_result
        _write_json(lane_runtime.lane_root / "stop.json", lane_result)
        results[lane_runtime.definition.lane_id] = lane_result
    return results


def _cleanup_lane(
    *,
    client: HoumaoServerClient | None,
    lane_runtime: LaneRuntime,
) -> dict[str, Any]:
    """Stop one launched lane and perform best-effort tmux cleanup when needed."""

    result: dict[str, Any] = {
        "lane_id": lane_runtime.definition.lane_id,
        "tracked_agent_id": lane_runtime.tracked_agent_id,
        "session_name": lane_runtime.session_name,
    }
    if client is not None and lane_runtime.tracked_agent_id is not None:
        try:
            stop_response = _record_route_call(
                recorder=lane_runtime.http_recorder,
                label="stop-managed-agent",
                method="POST",
                path=f"/houmao/agents/{lane_runtime.tracked_agent_id}/stop",
                request_payload=None,
                callback=lambda: client.stop_managed_agent(lane_runtime.tracked_agent_id),
            )
            result["managed_stop"] = _json_ready(stop_response)
        except Exception as exc:
            result["managed_stop_error"] = str(exc)
    elif client is not None and lane_runtime.session_name is not None:
        try:
            delete_response = client.delete_session(lane_runtime.session_name)
            result["session_delete"] = _json_ready(delete_response)
        except Exception as exc:
            result["session_delete_error"] = str(exc)

    if lane_runtime.definition.transport == "tui" and lane_runtime.session_name is not None:
        tmux_result = subprocess.run(
            ["tmux", "kill-session", "-t", lane_runtime.session_name],
            check=False,
            capture_output=True,
            text=True,
        )
        result["tmux_cleanup"] = _completed_process_payload(tmux_result)
    return result


def _stop_suite_server(
    server_info: Mapping[str, Any] | None,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop the suite-owned houmao-server and return shutdown evidence."""

    if server_info is None:
        return {"status": "not_started"}
    pid = int(server_info["pid"])
    api_base_url = str(server_info["api_base_url"])
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return {"status": "already_stopped", "pid": pid}
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not _pid_exists(pid) and not _server_health_ok(api_base_url):
            return {"status": "stopped", "pid": pid}
        time.sleep(0.25)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return {"status": "stopped", "pid": pid}
    return {"status": "forced", "pid": pid}


def _record_route_call(
    *,
    recorder: ArtifactRecorder,
    label: str,
    method: str,
    path: str,
    request_payload: Any,
    callback: Any,
) -> Any:
    """Execute one client call and persist a request/response snapshot."""

    try:
        response = callback()
    except Exception as exc:
        recorder.write_json(
            label=label,
            payload={
                "ok": False,
                "method": method,
                "path": path,
                "request": _json_ready(request_payload),
                "error": str(exc),
            },
        )
        raise
    recorder.write_json(
        label=label,
        payload={
            "ok": True,
            "method": method,
            "path": path,
            "request": _json_ready(request_payload),
            "response": _json_ready(response),
        },
    )
    return response


def _config_payload(*, config: SuiteConfig, paths: SuitePaths) -> dict[str, Any]:
    """Build one JSON-ready config payload for the run root."""

    return {
        "selected_lane_ids": list(config.selected_lane_ids),
        "output_root": str(paths.run_root),
        "port": config.port,
        "compat_http_timeout_seconds": config.compat_http_timeout_seconds,
        "compat_create_timeout_seconds": config.compat_create_timeout_seconds,
        "compat_provider_ready_timeout_seconds": config.compat_provider_ready_timeout_seconds,
        "health_timeout_seconds": config.health_timeout_seconds,
        "prompt_timeout_seconds": config.prompt_timeout_seconds,
        "prompt_poll_interval_seconds": config.prompt_poll_interval_seconds,
    }


def _state_signature(state: HoumaoManagedAgentStateResponse) -> tuple[object, ...]:
    """Return one coarse shared-state signature for post-request polling."""

    return (
        state.turn.phase,
        state.turn.active_turn_id,
        state.last_turn.result,
        state.last_turn.turn_id,
        state.last_turn.turn_index,
        state.last_turn.updated_at_utc,
    )


def _is_observable_post_request_progress(
    *,
    state_before: HoumaoManagedAgentStateResponse,
    latest_state: HoumaoManagedAgentStateResponse,
    baseline_signature: tuple[object, ...],
) -> bool:
    """Return whether the latest state shows meaningful post-request progress."""

    if _state_signature(latest_state) == baseline_signature:
        return False
    if latest_state.last_turn.result != state_before.last_turn.result:
        return True
    if latest_state.turn.phase != state_before.turn.phase:
        return True
    if latest_state.turn.active_turn_id != state_before.turn.active_turn_id:
        return True
    return False


def _require_tracked_agent_id(lane_runtime: LaneRuntime) -> str:
    """Require one launched lane to expose its tracked-agent id."""

    if lane_runtime.tracked_agent_id is None:
        raise SuiteError(
            f"Lane `{lane_runtime.definition.lane_id}` did not record a tracked agent id."
        )
    return lane_runtime.tracked_agent_id


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
    if hasattr(payload, "returncode") and hasattr(payload, "stdout") and hasattr(payload, "stderr"):
        return _completed_process_payload(payload)
    if hasattr(payload, "__dict__"):
        return {key: _json_ready(value) for key, value in payload.__dict__.items()}
    return str(payload)


def _completed_process_payload(result: subprocess.CompletedProcess[str] | Any) -> dict[str, Any]:
    """Project one completed-process-like object into JSON."""

    return {
        "args": list(result.args) if isinstance(result.args, (list, tuple)) else str(result.args),
        "returncode": int(result.returncode),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _choose_port(requested_port: int | None) -> int:
    """Choose one loopback port for the suite-owned server."""

    if requested_port is not None:
        return requested_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


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


def _server_health_ok(api_base_url: str) -> bool:
    """Return whether one houmao-server still answers healthy status."""

    try:
        client = HoumaoServerClient(api_base_url, timeout_seconds=1.0)
        health = client.health_extended()
    except Exception:
        return False
    return health.status == "ok" and health.houmao_service == "houmao-server"


@contextmanager
def _temporary_env_var(name: str, value: str):
    """Set one environment variable for a bounded block."""

    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous

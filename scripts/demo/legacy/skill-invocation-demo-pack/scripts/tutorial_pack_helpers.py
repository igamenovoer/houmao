#!/usr/bin/env python3
"""Helper utilities for the skill-invocation demo pack."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from houmao.agents.realm_controller.loaders import parse_allowlisted_env
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.cao.no_proxy import is_supported_loopback_cao_base_url
from houmao.cao.server_launcher import (
    load_cao_server_launcher_config,
    resolve_cao_server_runtime_artifacts,
)
from houmao.demo.legacy.launch_support import (
    normalize_demo_launch_backend,
    resolve_demo_preset_launch,
)

_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_DEFAULT_DEMO_OUTPUT_DIR = Path("tmp/demo/skill-invocation-demo-pack")
_FIXED_DEMO_PROJECT_COMMIT_UTC = "2026-03-18T00:00:00Z"
_FIXED_DEMO_PROJECT_COMMIT_MESSAGE = "Initial dummy project snapshot"
_FIXED_DEMO_PROJECT_AUTHOR_NAME = "Houmao Demo Fixture"
_FIXED_DEMO_PROJECT_AUTHOR_EMAIL = "houmao-demo-fixture@example.invalid"
_MANAGED_PROJECT_METADATA_NAME = ".houmao-demo-project.json"
_ARTIFACT_FILENAMES = {
    "brain_build": "brain_build.json",
    "cao_start": "cao_start.json",
    "inspect": "inspect.json",
    "prompt_events": "prompt.events.jsonl",
    "prompt_result": "prompt.json",
    "report": "report.json",
    "report_sanitized": "report.sanitized.json",
    "session_start": "session_start.json",
    "stop": "stop.json",
}
_PATH_KEYS = {
    "agent_def_dir",
    "artifact_dir",
    "blueprint_path",
    "brain_recipe_path",
    "credential_env_path",
    "credential_profile_dir",
    "demo_output_dir",
    "home_dir",
    "home_path",
    "job_dir",
    "launch_helper_path",
    "launcher_config_path",
    "launcher_result_file",
    "log_file",
    "manifest_path",
    "marker_path",
    "ownership_file",
    "parameters_path",
    "profile_store",
    "project_fixture",
    "project_workdir",
    "prompt_events_path",
    "prompt_path",
    "prompt_result_path",
    "report_path",
    "runtime_root",
    "sanitized_report_path",
    "session_manifest",
    "state_path",
    "stop_path",
    "tool_adapter_path",
}


GitRunner = Callable[[list[str], Path, dict[str, str] | None], subprocess.CompletedProcess[str]]
LauncherRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


class DemoSkipError(RuntimeError):
    """Error used when the demo should exit with a tracked skip message."""


@dataclass(frozen=True)
class ToolLane:
    """Tracked tool-lane configuration."""

    blueprint: str
    agent_identity: str


@dataclass(frozen=True)
class PromptConfig:
    """Tracked prompt and marker contract."""

    trigger_file: str
    trigger_phrase: str
    marker_relative_path: str
    expected_marker_payload: dict[str, Any]


@dataclass(frozen=True)
class AutomaticConfig:
    """Tracked automatic verification timing."""

    marker_timeout_seconds: int


@dataclass(frozen=True)
class DemoParameters:
    """Validated demo-pack parameters."""

    schema_version: int
    demo_id: str
    agent_def_dir: str
    project_fixture: str
    backend: str
    cao_base_url: str
    parsing_mode: str
    tool_lanes: dict[str, ToolLane]
    prompt: PromptConfig
    automatic: AutomaticConfig


@dataclass(frozen=True)
class DemoLayout:
    """Resolved demo-owned filesystem layout."""

    demo_output_dir: Path
    control_dir: Path
    project_workdir: Path
    runtime_root: Path
    cao_dir: Path
    cao_launcher_config_path: Path
    cao_runtime_root: Path
    inputs_dir: Path
    state_path: Path
    brain_build_path: Path
    session_start_path: Path
    cao_start_path: Path
    prompt_events_path: Path
    prompt_result_path: Path
    inspect_path: Path
    report_path: Path
    sanitized_report_path: Path
    stop_path: Path


@dataclass(frozen=True)
class LanePreflight:
    """Resolved prerequisites for one selected tool lane."""

    selected_tool: str
    blueprint_path: Path
    brain_recipe_path: Path
    role_name: str
    tool_adapter_path: Path
    launch_executable: str
    config_profile: str
    credential_profile: str
    credential_profile_dir: Path
    credential_env_path: Path
    selected_allowlisted_env_keys: tuple[str, ...]
    required_credential_paths: tuple[Path, ...]
    optional_credential_paths: tuple[Path, ...]
    usable_auth_json: bool

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-friendly representation."""

        return {
            "selected_tool": self.selected_tool,
            "blueprint_path": str(self.blueprint_path),
            "brain_recipe_path": str(self.brain_recipe_path),
            "role_name": self.role_name,
            "tool_adapter_path": str(self.tool_adapter_path),
            "launch_executable": self.launch_executable,
            "config_profile": self.config_profile,
            "credential_profile": self.credential_profile,
            "credential_profile_dir": str(self.credential_profile_dir),
            "credential_env_path": str(self.credential_env_path),
            "selected_allowlisted_env_keys": list(self.selected_allowlisted_env_keys),
            "required_credential_paths": [str(path) for path in self.required_credential_paths],
            "optional_credential_paths": [str(path) for path in self.optional_credential_paths],
            "usable_auth_json": self.usable_auth_json,
        }


def _read_json(path: Path) -> Any:
    """Load one JSON value from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON value to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require_mapping(value: Any, *, context: str) -> dict[str, Any]:
    """Return one mapping value or raise a validation error."""

    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    return value


def _require_non_empty_string(value: Any, *, context: str) -> str:
    """Return one non-empty string or raise a validation error."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _normalize_cao_base_url(value: str) -> str:
    """Normalize one loopback CAO base URL string."""

    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme != "http":
        raise ValueError("CAO base URL must use http")
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("CAO base URL must include host and explicit port")
    return f"http://{parsed.hostname}:{parsed.port}"


def _tool_lane_from_payload(payload: Any, *, context: str) -> ToolLane:
    """Parse one tool-lane block."""

    mapping = _require_mapping(payload, context=context)
    return ToolLane(
        blueprint=_require_non_empty_string(
            mapping.get("blueprint"), context=f"{context}.blueprint"
        ),
        agent_identity=_require_non_empty_string(
            mapping.get("agent_identity"),
            context=f"{context}.agent_identity",
        ),
    )


def _prompt_from_payload(payload: Any) -> PromptConfig:
    """Parse the prompt block."""

    mapping = _require_mapping(payload, context="prompt")
    expected_marker_payload = _require_mapping(
        mapping.get("expected_marker_payload"),
        context="prompt.expected_marker_payload",
    )
    return PromptConfig(
        trigger_file=_require_non_empty_string(
            mapping.get("trigger_file"),
            context="prompt.trigger_file",
        ),
        trigger_phrase=_require_non_empty_string(
            mapping.get("trigger_phrase"),
            context="prompt.trigger_phrase",
        ),
        marker_relative_path=_require_non_empty_string(
            mapping.get("marker_relative_path"),
            context="prompt.marker_relative_path",
        ),
        expected_marker_payload=expected_marker_payload,
    )


def _automatic_from_payload(payload: Any) -> AutomaticConfig:
    """Parse the automatic timing block."""

    mapping = _require_mapping(payload, context="automatic")
    marker_timeout_seconds = int(mapping.get("marker_timeout_seconds"))
    if marker_timeout_seconds < 1:
        raise ValueError("automatic.marker_timeout_seconds must be >= 1")
    return AutomaticConfig(marker_timeout_seconds=marker_timeout_seconds)


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load and validate the tracked demo parameters."""

    payload = _require_mapping(_read_json(path), context=str(path))
    schema_version = int(payload.get("schema_version"))
    if schema_version != 1:
        raise ValueError("demo parameters must use schema_version=1")

    tool_lanes_raw = _require_mapping(payload.get("tool_lanes"), context="tool_lanes")
    tool_lanes = {
        key: _tool_lane_from_payload(value, context=f"tool_lanes.{key}")
        for key, value in tool_lanes_raw.items()
    }
    if set(tool_lanes) != {"claude", "codex"}:
        raise ValueError("tool_lanes must define exactly `claude` and `codex`")

    parameters = DemoParameters(
        schema_version=schema_version,
        demo_id=_require_non_empty_string(payload.get("demo_id"), context="demo_id"),
        agent_def_dir=_require_non_empty_string(
            payload.get("agent_def_dir"),
            context="agent_def_dir",
        ),
        project_fixture=_require_non_empty_string(
            payload.get("project_fixture"),
            context="project_fixture",
        ),
        backend=_require_non_empty_string(payload.get("backend"), context="backend"),
        cao_base_url=_require_non_empty_string(payload.get("cao_base_url"), context="cao_base_url"),
        parsing_mode=_require_non_empty_string(
            payload.get("parsing_mode"),
            context="parsing_mode",
        ),
        tool_lanes=tool_lanes,
        prompt=_prompt_from_payload(payload.get("prompt")),
        automatic=_automatic_from_payload(payload.get("automatic")),
    )
    if normalize_demo_launch_backend(parameters.backend) != "local_interactive":
        raise ValueError("demo parameters backend must be local_interactive or legacy cao_rest")
    if parameters.parsing_mode != "shadow_only":
        raise ValueError("demo parameters parsing_mode must be shadow_only")
    return parameters


def parameters_to_payload(parameters: DemoParameters) -> dict[str, Any]:
    """Convert parameters to one JSON-serializable payload."""

    return asdict(parameters)


def resolve_repo_relative_path(
    raw_path: str | None,
    *,
    repo_root: Path,
    default_relative: str | Path | None = None,
) -> Path:
    """Resolve one optional path relative to the repository root."""

    if raw_path is None or not raw_path.strip():
        if default_relative is None:
            raise ValueError("path is required when no default_relative is provided")
        candidate = Path(default_relative)
    else:
        candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root.resolve() / candidate).resolve()


def build_demo_layout(*, demo_output_dir: Path) -> DemoLayout:
    """Build the demo-owned output layout for one run."""

    resolved_output_dir = demo_output_dir.resolve()
    control_dir = resolved_output_dir / "control"
    cao_dir = resolved_output_dir / "cao"
    return DemoLayout(
        demo_output_dir=resolved_output_dir,
        control_dir=control_dir,
        project_workdir=resolved_output_dir / "project",
        runtime_root=resolved_output_dir / "runtime",
        cao_dir=cao_dir,
        cao_launcher_config_path=cao_dir / "launcher.toml",
        cao_runtime_root=cao_dir / "runtime",
        inputs_dir=resolved_output_dir / "inputs",
        state_path=control_dir / "demo_state.json",
        brain_build_path=control_dir / _ARTIFACT_FILENAMES["brain_build"],
        session_start_path=control_dir / _ARTIFACT_FILENAMES["session_start"],
        cao_start_path=control_dir / _ARTIFACT_FILENAMES["cao_start"],
        prompt_events_path=control_dir / _ARTIFACT_FILENAMES["prompt_events"],
        prompt_result_path=control_dir / _ARTIFACT_FILENAMES["prompt_result"],
        inspect_path=control_dir / _ARTIFACT_FILENAMES["inspect"],
        report_path=control_dir / _ARTIFACT_FILENAMES["report"],
        sanitized_report_path=control_dir / _ARTIFACT_FILENAMES["report_sanitized"],
        stop_path=control_dir / _ARTIFACT_FILENAMES["stop"],
    )


def render_marker_path(parameters: DemoParameters, *, project_workdir: Path) -> Path:
    """Render the absolute marker path inside the copied workdir."""

    relative_path = Path(parameters.prompt.marker_relative_path)
    if relative_path.is_absolute():
        raise ValueError("prompt.marker_relative_path must stay relative to the copied workdir")
    return (project_workdir.resolve() / relative_path).resolve()


def render_prompt_path(parameters: DemoParameters, *, layout: DemoLayout) -> Path:
    """Render the copied prompt file path inside the demo root."""

    prompt_name = Path(parameters.prompt.trigger_file).name
    return (layout.inputs_dir / prompt_name).resolve()


def _stderr_path_for(path: Path) -> Path:
    """Return the paired stderr path for one artifact."""

    return path.with_suffix(path.suffix + ".err")


def _copy_inputs(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Refresh tracked input files into the demo output directory."""

    if layout.inputs_dir.exists():
        shutil.rmtree(layout.inputs_dir)
    shutil.copytree(pack_dir / "inputs", layout.inputs_dir)


def _default_git_runner(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    """Run one git command for demo project provisioning."""

    return subprocess.run(
        args,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        env=None if env is None else {**os.environ, **env},
    )


def _resolved_git_reported_path(raw_path: str, *, cwd: Path) -> Path:
    """Resolve one git-reported path relative to the command cwd when needed."""

    candidate = Path(raw_path.strip())
    if candidate.is_absolute():
        return candidate.resolve()
    return (cwd.resolve() / candidate).resolve()


def _git_output(*, args: list[str], cwd: Path, run_git: GitRunner) -> str | None:
    """Run one git command and return stripped stdout on success."""

    result = run_git(args, cwd, None)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def is_standalone_git_repo(
    *,
    project_workdir: Path,
    run_git: GitRunner = _default_git_runner,
) -> bool:
    """Return whether the path is a standalone git repository rooted at itself."""

    if not project_workdir.exists():
        return False

    inside = _git_output(
        args=["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_workdir,
        run_git=run_git,
    )
    if inside != "true":
        return False

    project_top = _git_output(
        args=["git", "rev-parse", "--show-toplevel"],
        cwd=project_workdir,
        run_git=run_git,
    )
    project_common = _git_output(
        args=["git", "rev-parse", "--git-common-dir"],
        cwd=project_workdir,
        run_git=run_git,
    )
    if project_top is None or project_common is None:
        return False

    return _resolved_git_reported_path(
        project_top,
        cwd=project_workdir,
    ) == project_workdir.resolve() and _resolved_git_reported_path(
        project_common,
        cwd=project_workdir,
    ) == (project_workdir.resolve() / ".git")


def _managed_project_metadata_path(project_workdir: Path) -> Path:
    """Return the metadata path used to mark demo-managed dummy project repos."""

    return project_workdir / _MANAGED_PROJECT_METADATA_NAME


def _is_managed_dummy_project_repo(
    *,
    project_workdir: Path,
    run_git: GitRunner = _default_git_runner,
) -> bool:
    """Return whether the project directory is a managed dummy-project repo."""

    return _managed_project_metadata_path(project_workdir).is_file() and is_standalone_git_repo(
        project_workdir=project_workdir,
        run_git=run_git,
    )


def _write_managed_project_metadata(*, project_workdir: Path, fixture_dir: Path) -> None:
    """Write one marker payload for a managed copied dummy-project workdir."""

    _write_json(
        _managed_project_metadata_path(project_workdir),
        {
            "schema_version": 1,
            "managed_by": "skill-invocation-demo-pack",
            "fixture_dir": str(fixture_dir.resolve()),
            "prepared_at": _FIXED_DEMO_PROJECT_COMMIT_UTC,
        },
    )


def _run_required_git_command(
    *,
    args: list[str],
    cwd: Path,
    run_git: GitRunner,
    env: dict[str, str] | None = None,
) -> None:
    """Run one required git command or raise with a clear detail string."""

    result = run_git(args, cwd, env)
    if result.returncode == 0:
        return
    detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
    raise RuntimeError(f"`{' '.join(args)}` failed: {detail}")


def _initialize_demo_git_repo(
    *,
    project_workdir: Path,
    run_git: GitRunner = _default_git_runner,
) -> None:
    """Initialize one copied dummy project as a fresh pinned-metadata git repo."""

    fixed_identity_env = {
        "GIT_AUTHOR_NAME": _FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": _FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_COMMITTER_NAME": _FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": _FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_AUTHOR_DATE": _FIXED_DEMO_PROJECT_COMMIT_UTC,
        "GIT_COMMITTER_DATE": _FIXED_DEMO_PROJECT_COMMIT_UTC,
    }

    _run_required_git_command(
        args=["git", "init", "--initial-branch", "main"],
        cwd=project_workdir,
        run_git=run_git,
    )
    _run_required_git_command(
        args=["git", "add", "--all"],
        cwd=project_workdir,
        run_git=run_git,
    )
    _run_required_git_command(
        args=[
            "git",
            "commit",
            "--allow-empty",
            "--no-gpg-sign",
            "-m",
            _FIXED_DEMO_PROJECT_COMMIT_MESSAGE,
        ],
        cwd=project_workdir,
        run_git=run_git,
        env=fixed_identity_env,
    )


def ensure_project_workdir_from_fixture(
    *,
    repo_root: Path,
    project_fixture: Path,
    project_workdir: Path,
    allow_reprovision: bool,
    run_git: GitRunner = _default_git_runner,
) -> Path:
    """Copy one tracked dummy project fixture and initialize a fresh git-backed workdir."""

    del repo_root
    resolved_fixture = project_fixture.resolve()
    resolved_project_workdir = project_workdir.resolve()
    if not resolved_fixture.is_dir():
        raise ValueError(f"dummy project fixture directory not found: {resolved_fixture}")
    if (resolved_fixture / ".git").exists():
        raise ValueError(
            "dummy project fixture must remain source-only and may not include tracked `.git`: "
            f"{resolved_fixture}"
        )

    if resolved_project_workdir.exists():
        if not allow_reprovision:
            raise ValueError(
                "demo project directory already exists before a stopped demo state was found: "
                f"{resolved_project_workdir}"
            )
        if not _is_managed_dummy_project_repo(
            project_workdir=resolved_project_workdir,
            run_git=run_git,
        ):
            raise ValueError(
                "demo project directory exists but is not a demo-managed dummy-project repo: "
                f"{resolved_project_workdir}"
            )
        shutil.rmtree(resolved_project_workdir)

    resolved_project_workdir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(resolved_fixture, resolved_project_workdir)
    _write_managed_project_metadata(
        project_workdir=resolved_project_workdir,
        fixture_dir=resolved_fixture,
    )
    _initialize_demo_git_repo(
        project_workdir=resolved_project_workdir,
        run_git=run_git,
    )
    if not is_standalone_git_repo(
        project_workdir=resolved_project_workdir,
        run_git=run_git,
    ):
        raise RuntimeError(
            "dummy project provisioning finished but the resulting project directory did not "
            f"validate as a standalone git repository: {resolved_project_workdir}"
        )
    return resolved_project_workdir


def supports_loopback_cao_launcher_management(cao_base_url: str) -> bool:
    """Return whether the base URL can use demo-local launcher management."""

    return is_supported_loopback_cao_base_url(_normalize_cao_base_url(cao_base_url))


def _default_launcher_runner(args: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Run one launcher CLI command via the repo Pixi environment."""

    return subprocess.run(
        ["pixi", "run", "python", "-m", "houmao.cao.tools.cao_server_launcher", *args],
        cwd=str(repo_root.resolve()),
        check=False,
        capture_output=True,
        text=True,
    )


def write_demo_cao_launcher_config(*, demo_output_dir: Path, cao_base_url: str) -> Path:
    """Write the demo-local CAO launcher config and return its path."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    layout.cao_dir.mkdir(parents=True, exist_ok=True)
    layout.cao_launcher_config_path.write_text(
        "\n".join(
            [
                f'base_url = "{_normalize_cao_base_url(cao_base_url)}"',
                'runtime_root = "runtime"',
                'home_dir = ""',
                'proxy_policy = "clear"',
                "startup_timeout_seconds = 15",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return layout.cao_launcher_config_path


def _launcher_json(
    *,
    repo_root: Path,
    args: list[str],
    accepted_exit_codes: set[int],
    run_launcher: LauncherRunner,
) -> dict[str, Any]:
    """Run one launcher command and parse one JSON payload from stdout/stderr."""

    result = run_launcher(args, repo_root.resolve())
    if result.returncode not in accepted_exit_codes:
        detail = result.stderr.strip() or result.stdout.strip() or "launcher command failed"
        raise RuntimeError(detail)
    payload_text = result.stdout.strip() or result.stderr.strip()
    if not payload_text:
        raise RuntimeError("launcher command returned no JSON payload")
    payload = json.loads(payload_text)
    return _require_mapping(payload, context="launcher result")


def _ownership_verified(payload: dict[str, Any], *, artifact_dir: Path, base_url: str) -> bool:
    """Return whether one launcher result payload carries matching ownership."""

    ownership = payload.get("ownership")
    if not isinstance(ownership, dict):
        return False
    return (
        ownership.get("managed_by") == "houmao.cao.server_launcher"
        and ownership.get("base_url") == base_url
        and ownership.get("artifact_dir") == str(artifact_dir)
    )


def start_demo_cao(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    cao_base_url: str,
    run_launcher: LauncherRunner = _default_launcher_runner,
) -> dict[str, Any]:
    """Start or reuse demo-local loopback CAO and return one structured payload."""

    normalized_base_url = _normalize_cao_base_url(cao_base_url)
    if not supports_loopback_cao_launcher_management(normalized_base_url):
        raise ValueError(
            "demo-local CAO launcher management only supports loopback base URLs "
            "with explicit ports"
        )

    config_path = write_demo_cao_launcher_config(
        demo_output_dir=demo_output_dir,
        cao_base_url=normalized_base_url,
    )
    config = load_cao_server_launcher_config(config_path)
    artifacts = resolve_cao_server_runtime_artifacts(config)
    start_payload = _launcher_json(
        repo_root=repo_root,
        args=["start", "--config", str(config_path)],
        accepted_exit_codes={0},
        run_launcher=run_launcher,
    )
    ownership_verified = _ownership_verified(
        start_payload,
        artifact_dir=artifacts.artifact_dir,
        base_url=normalized_base_url,
    )
    return {
        "managed": True,
        "base_url": normalized_base_url,
        "launcher_config_path": str(config.config_path),
        "runtime_root": str(config.runtime_root),
        "home_dir": str(artifacts.home_dir),
        "profile_store": str(
            (artifacts.home_dir / ".aws" / "cli-agent-orchestrator" / "agent-store").resolve()
        ),
        "artifact_dir": str(artifacts.artifact_dir),
        "log_file": str(artifacts.log_file),
        "launcher_result_file": str(artifacts.launcher_result_file),
        "ownership_file": str(artifacts.ownership_file),
        "healthy": bool(start_payload.get("healthy")),
        "started_current_run": bool(start_payload.get("started_new_process")),
        "reused_existing_process": bool(start_payload.get("reused_existing_process")),
        "ownership_verified": ownership_verified,
        "message": _require_non_empty_string(start_payload.get("message"), context="message"),
    }


def stop_demo_cao(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    run_launcher: LauncherRunner = _default_launcher_runner,
) -> dict[str, Any]:
    """Stop demo-local CAO using the demo-owned launcher config."""

    config_path = build_demo_layout(demo_output_dir=demo_output_dir).cao_launcher_config_path
    if not config_path.exists():
        return {
            "managed": False,
            "stopped": False,
            "already_stopped": True,
            "message": f"demo-local launcher config not found: {config_path}",
        }
    return _launcher_json(
        repo_root=repo_root,
        args=["stop", "--config", str(config_path)],
        accepted_exit_codes={0, 2},
        run_launcher=run_launcher,
    )


def _resolve_cao_context(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    cao_base_url: str,
) -> dict[str, Any]:
    """Resolve the CAO execution context for the demo."""

    normalized_base_url = _normalize_cao_base_url(cao_base_url)
    if not supports_loopback_cao_launcher_management(normalized_base_url):
        raise DemoSkipError(
            "skill-invocation demo only supports launcher-managed loopback CAO in v1"
        )
    try:
        payload = start_demo_cao(
            repo_root=repo_root,
            demo_output_dir=demo_output_dir,
            cao_base_url=normalized_base_url,
        )
    except Exception as exc:  # pragma: no cover - exercised through CLI in live runs
        raise DemoSkipError(f"loopback CAO unavailable or unreachable: {exc}") from exc
    if not bool(payload.get("ownership_verified")):
        raise DemoSkipError("loopback CAO reuse was not verified as launcher-owned for this pack")
    return payload


def _command_environment(*, jobs_dir: Path | None) -> dict[str, str]:
    """Return subprocess environment overrides for realm-controller commands."""

    env = dict(os.environ)
    if jobs_dir is not None:
        env["AGENTSYS_LOCAL_JOBS_DIR"] = str(jobs_dir.resolve())
    return env


def _run_json_command(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    accepted_exit_codes: set[int] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run one command, persist raw output, and parse one JSON stdout payload."""

    result = subprocess.run(
        command,
        cwd=str(cwd.resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    allowed = accepted_exit_codes if accepted_exit_codes is not None else {0}
    if result.returncode not in allowed:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(f"{detail} (exit={result.returncode})")
    payload_text = result.stdout.strip()
    if not payload_text:
        return {}
    payload = json.loads(payload_text)
    return _require_mapping(payload, context="command output")


def _run_jsonl_command(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    accepted_exit_codes: set[int] | None = None,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Run one command, persist raw output, and parse JSONL stdout."""

    result = subprocess.run(
        command,
        cwd=str(cwd.resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    allowed = accepted_exit_codes if accepted_exit_codes is not None else {0}
    if result.returncode not in allowed:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(f"{detail} (exit={result.returncode})")
    events: list[dict[str, Any]] = []
    for index, line in enumerate(result.stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        events.append(_require_mapping(payload, context=f"stdout line {index}"))
    return events


def _run_realm_controller_json(
    *,
    repo_root: Path,
    args: list[str],
    stdout_path: Path,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run one realm-controller command and parse JSON output."""

    return _run_json_command(
        command=["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args],
        cwd=repo_root,
        stdout_path=stdout_path,
        stderr_path=_stderr_path_for(stdout_path),
        env=env,
    )


def _run_realm_controller_jsonl(
    *,
    repo_root: Path,
    args: list[str],
    stdout_path: Path,
    env: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Run one realm-controller command and parse JSONL output."""

    return _run_jsonl_command(
        command=["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args],
        cwd=repo_root,
        stdout_path=stdout_path,
        stderr_path=_stderr_path_for(stdout_path),
        env=env,
    )


def _load_state(state_path: Path) -> dict[str, Any]:
    """Load one persisted demo state payload."""

    return _require_mapping(_read_json(state_path), context=str(state_path))


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    """Persist the current demo state payload."""

    _write_json(path, payload)


def _freshen_demo_output(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Reset fresh-run artifacts while preserving the project directory."""

    for path in (layout.runtime_root, layout.cao_dir, layout.control_dir, layout.inputs_dir):
        if path.exists():
            shutil.rmtree(path)
    _copy_inputs(pack_dir=pack_dir, layout=layout)


def _project_fixture_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the selected tracked dummy-project fixture directory."""

    return resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)


def _agent_def_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the agent-definition directory for the demo."""

    return resolve_repo_relative_path(
        os.environ.get("AGENT_DEF_DIR"),
        repo_root=repo_root,
        default_relative=parameters.agent_def_dir,
    )


def _selected_lane(parameters: DemoParameters, *, tool: str) -> ToolLane:
    """Return the tracked lane for one selected tool."""

    if tool not in parameters.tool_lanes:
        raise ValueError(f"unsupported tool lane: {tool}")
    return parameters.tool_lanes[tool]


def _usable_codex_auth_json(path: Path) -> bool:
    """Return whether one Codex auth file contains usable non-empty JSON."""

    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and bool(payload)


def preflight_selected_tool(
    *,
    repo_root: Path,
    agent_def_dir: Path,
    parameters: DemoParameters,
    tool: str,
) -> LanePreflight:
    """Resolve and validate tracked prerequisites for one selected tool lane."""

    lane = _selected_lane(parameters, tool=tool)
    blueprint_path = resolve_repo_relative_path(lane.blueprint, repo_root=repo_root)
    if not blueprint_path.is_file():
        raise DemoSkipError(f"selected preset not found: {blueprint_path}")

    resolved_launch = resolve_demo_preset_launch(
        agent_def_dir=agent_def_dir,
        preset_path=blueprint_path,
    )
    recipe = resolved_launch.preset
    adapter_path = resolved_launch.adapter_path
    adapter = resolved_launch.adapter
    if resolved_launch.auth_path is None or resolved_launch.auth_env_path is None:
        raise DemoSkipError(
            f"selected preset does not declare auth-backed launch inputs: {blueprint_path}"
        )
    credential_profile_dir = resolved_launch.auth_path
    credential_env_path = resolved_launch.auth_env_path
    selected_env_keys: tuple[str, ...] = ()
    if credential_env_path.is_file():
        selected_env, selected_names = parse_allowlisted_env(
            credential_env_path,
            adapter.credential_env_allowlist,
        )
        selected_env_keys = tuple(
            name for name in selected_names if selected_env.get(name, "").strip()
        )

    required_paths = resolved_launch.required_auth_paths
    optional_paths = resolved_launch.optional_auth_paths
    for required_path in required_paths:
        if not required_path.exists():
            raise DemoSkipError(
                f"missing required credential material for `{tool}`: {required_path}"
            )

    launch_executable = shutil.which(adapter.launch_executable)
    if launch_executable is None:
        raise DemoSkipError(
            f"selected tool executable not found on PATH: {adapter.launch_executable}"
        )
    if shutil.which("tmux") is None:
        raise DemoSkipError("`tmux` not found on PATH")

    usable_auth_json = any(_usable_codex_auth_json(path) for path in optional_paths)
    if tool == "codex":
        if not selected_env_keys and not usable_auth_json:
            raise DemoSkipError(
                "missing supported Codex credentials: expected allowlisted env vars or usable auth.json"
            )
    else:
        if not credential_env_path.is_file() or not selected_env_keys:
            raise DemoSkipError(
                "missing supported Claude credentials: expected allowlisted env vars in the selected profile"
            )

    return LanePreflight(
        selected_tool=tool,
        blueprint_path=blueprint_path,
        brain_recipe_path=resolved_launch.preset_path,
        role_name=resolved_launch.role_name,
        tool_adapter_path=adapter_path,
        launch_executable=launch_executable,
        config_profile=recipe.config_profile,
        credential_profile=recipe.credential_profile,
        credential_profile_dir=credential_profile_dir,
        credential_env_path=credential_env_path,
        selected_allowlisted_env_keys=selected_env_keys,
        required_credential_paths=required_paths,
        optional_credential_paths=optional_paths,
        usable_auth_json=usable_auth_json,
    )


def probe_marker_status(
    *,
    marker_path: Path,
    expected_payload: dict[str, Any],
) -> dict[str, Any]:
    """Inspect the current marker file and compare it to the tracked payload."""

    if not marker_path.is_file():
        return {
            "exists": False,
            "valid_json": False,
            "matches_expected": False,
            "observed_payload": None,
        }
    try:
        observed_payload = _require_mapping(_read_json(marker_path), context=str(marker_path))
    except Exception:
        return {
            "exists": True,
            "valid_json": False,
            "matches_expected": False,
            "observed_payload": None,
        }
    return {
        "exists": True,
        "valid_json": True,
        "matches_expected": observed_payload == expected_payload,
        "observed_payload": observed_payload,
    }


def wait_for_probe_marker(
    *,
    marker_path: Path,
    expected_payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    """Wait until the expected probe marker exists or timeout expires."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = probe_marker_status(marker_path=marker_path, expected_payload=expected_payload)
        if bool(status["matches_expected"]):
            return status
        time.sleep(1.0)
    return probe_marker_status(marker_path=marker_path, expected_payload=expected_payload)


def summarize_prompt_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce raw runtime prompt events to one stable summary."""

    event_kinds = [str(event.get("kind", "")) for event in events]
    done_event = next((event for event in reversed(events) if event.get("kind") == "done"), None)
    done_message = None
    if isinstance(done_event, dict):
        maybe_message = done_event.get("message")
        if isinstance(maybe_message, str):
            done_message = maybe_message
    return {
        "event_count": len(events),
        "event_kinds": event_kinds,
        "done_message": done_message,
    }


def start_demo(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
    tool: str,
    jobs_dir: Path | None,
) -> dict[str, Any]:
    """Start the live demo session for one selected tool lane."""

    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    project_fixture = _project_fixture_dir(parameters=parameters, repo_root=repo_root)
    allow_project_reprovision = False
    if layout.state_path.exists():
        if not layout.stop_path.exists():
            raise ValueError(
                "demo state already exists for this output directory and has not been stopped; "
                "run `run_demo.sh stop` first"
            )
        allow_project_reprovision = True

    _freshen_demo_output(pack_dir=pack_dir, layout=layout)
    ensure_project_workdir_from_fixture(
        repo_root=repo_root,
        project_fixture=project_fixture,
        project_workdir=layout.project_workdir,
        allow_reprovision=allow_project_reprovision,
    )
    layout.runtime_root.mkdir(parents=True, exist_ok=True)
    layout.control_dir.mkdir(parents=True, exist_ok=True)

    agent_def_dir = _agent_def_dir(parameters=parameters, repo_root=repo_root)
    preflight = preflight_selected_tool(
        repo_root=repo_root,
        agent_def_dir=agent_def_dir,
        parameters=parameters,
        tool=tool,
    )
    lane = _selected_lane(parameters, tool=tool)
    cao_context = _resolve_cao_context(
        repo_root=repo_root,
        demo_output_dir=demo_output_dir,
        cao_base_url=os.environ.get("CAO_BASE_URL", parameters.cao_base_url),
    )
    _write_json(layout.cao_start_path, cao_context)

    env = _command_environment(jobs_dir=jobs_dir)
    build_payload = _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "build-brain",
            "--agent-def-dir",
            str(agent_def_dir),
            "--runtime-root",
            str(layout.runtime_root),
            "--preset",
            str(preflight.brain_recipe_path),
        ],
        stdout_path=layout.brain_build_path,
        env=env,
    )
    session_payload = _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "start-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--runtime-root",
            str(layout.runtime_root),
            "--brain-manifest",
            _require_non_empty_string(build_payload.get("manifest_path"), context="manifest_path"),
            "--role",
            preflight.role_name,
            "--backend",
            normalize_demo_launch_backend(parameters.backend),
            "--cao-base-url",
            _require_non_empty_string(cao_context.get("base_url"), context="cao.base_url"),
            "--cao-profile-store",
            _require_non_empty_string(
                cao_context.get("profile_store"),
                context="cao.profile_store",
            ),
            "--cao-parsing-mode",
            parameters.parsing_mode,
            "--workdir",
            str(layout.project_workdir),
            "--agent-identity",
            lane.agent_identity,
        ],
        stdout_path=layout.session_start_path,
        env=env,
    )

    state = {
        "schema_version": 1,
        "demo_id": parameters.demo_id,
        "parameters_path": str(parameters_path.resolve()),
        "demo_output_dir": str(layout.demo_output_dir),
        "project_workdir": str(layout.project_workdir),
        "project_fixture": str(project_fixture.resolve()),
        "runtime_root": str(layout.runtime_root),
        "agent_def_dir": str(agent_def_dir.resolve()),
        "jobs_dir": None if jobs_dir is None else str(jobs_dir.resolve()),
        "selected_tool": tool,
        "selected_lane": {
            "blueprint": lane.blueprint,
            "agent_identity": lane.agent_identity,
        },
        "preflight": preflight.to_payload(),
        "cao": cao_context,
        "brain_build": build_payload,
        "session": session_payload,
        "prompt_path": str(render_prompt_path(parameters, layout=layout)),
        "marker_path": str(render_marker_path(parameters, project_workdir=layout.project_workdir)),
    }
    _write_state(layout.state_path, state)
    return state


def prompt_demo(
    *,
    repo_root: Path,
    parameters_path: Path,
    state_path: Path,
) -> dict[str, Any]:
    """Send the tracked trigger prompt to the running session."""

    parameters = load_demo_parameters(parameters_path)
    state = _load_state(state_path)
    prompt_text = Path(
        _require_non_empty_string(state.get("prompt_path"), context="state.prompt_path")
    ).read_text(encoding="utf-8")
    layout = build_demo_layout(
        demo_output_dir=Path(
            _require_non_empty_string(state.get("demo_output_dir"), context="state.demo_output_dir")
        )
    )
    env = _command_environment(
        jobs_dir=None if state.get("jobs_dir") is None else Path(str(state["jobs_dir"]))
    )
    session = _require_mapping(state.get("session"), context="state.session")
    events = _run_realm_controller_jsonl(
        repo_root=repo_root,
        args=[
            "send-prompt",
            "--agent-def-dir",
            _require_non_empty_string(state.get("agent_def_dir"), context="state.agent_def_dir"),
            "--agent-identity",
            _require_non_empty_string(
                session.get("agent_identity"),
                context="state.session.agent_identity",
            ),
            "--cao-parsing-mode",
            parameters.parsing_mode,
            "--prompt",
            prompt_text,
        ],
        stdout_path=layout.prompt_events_path,
        env=env,
    )
    summary = summarize_prompt_events(events)
    marker_status = probe_marker_status(
        marker_path=Path(
            _require_non_empty_string(state.get("marker_path"), context="marker_path")
        ),
        expected_payload=parameters.prompt.expected_marker_payload,
    )
    payload = {
        "prompt_path": str(render_prompt_path(parameters, layout=layout)),
        "trigger_phrase": parameters.prompt.trigger_phrase,
        "prompt_text": prompt_text,
        **summary,
        "marker_status_after_prompt": marker_status,
    }
    _write_json(layout.prompt_result_path, payload)
    return payload


def inspect_demo(
    *, parameters_path: Path, state_path: Path, output_path: Path | None = None
) -> dict[str, Any]:
    """Inspect the persisted session/watch coordinates for one running demo."""

    parameters = load_demo_parameters(parameters_path)
    state = _load_state(state_path)
    output_path = (
        output_path
        or build_demo_layout(demo_output_dir=Path(state["demo_output_dir"])).inspect_path
    )

    session_manifest_path = Path(
        _require_non_empty_string(
            _require_mapping(state["session"], context="state.session").get("session_manifest"),
            context="state.session.session_manifest",
        )
    )
    manifest = load_session_manifest(session_manifest_path)
    parsed = parse_session_manifest_payload(manifest.payload, source=str(session_manifest_path))
    cao_payload = parsed.cao
    marker_status = probe_marker_status(
        marker_path=Path(_require_non_empty_string(state["marker_path"], context="marker_path")),
        expected_payload=parameters.prompt.expected_marker_payload,
    )
    inspection = {
        "selected_tool": _require_non_empty_string(
            state.get("selected_tool"),
            context="state.selected_tool",
        ),
        "selected_blueprint": _require_non_empty_string(
            _require_mapping(state["selected_lane"], context="state.selected_lane").get(
                "blueprint"
            ),
            context="state.selected_lane.blueprint",
        ),
        "session_manifest": str(session_manifest_path),
        "agent_identity": _require_non_empty_string(
            _require_mapping(state["session"], context="state.session").get("agent_identity"),
            context="state.session.agent_identity",
        ),
        "job_dir": _require_mapping(state["session"], context="state.session").get("job_dir"),
        "tmux_session_name": _require_mapping(state["session"], context="state.session").get(
            "tmux_session_name"
        ),
        "cao_base_url": _require_non_empty_string(state["cao"]["base_url"], context="cao.base_url"),
        "cao_session_name": None if cao_payload is None else cao_payload.session_name,
        "cao_terminal_id": None if cao_payload is None else cao_payload.terminal_id,
        "tmux_window_name": None if cao_payload is None else cao_payload.tmux_window_name,
        "parsing_mode": None if cao_payload is None else cao_payload.parsing_mode,
        "marker_status": marker_status,
    }
    _write_json(output_path, inspection)
    return inspection


def build_report(
    *,
    output_path: Path,
    parameters_path: Path,
    state_path: Path,
) -> dict[str, Any]:
    """Build one structured raw report for the current demo run."""

    parameters = load_demo_parameters(parameters_path)
    state = _load_state(state_path)
    layout = build_demo_layout(demo_output_dir=Path(state["demo_output_dir"]))
    prompt_summary = (
        _read_json(layout.prompt_result_path) if layout.prompt_result_path.is_file() else None
    )
    session_manifest_path = Path(
        _require_non_empty_string(
            _require_mapping(state["session"], context="state.session").get("session_manifest"),
            context="state.session.session_manifest",
        )
    )
    manifest = load_session_manifest(session_manifest_path)
    parsed = parse_session_manifest_payload(manifest.payload, source=str(session_manifest_path))
    marker_status = probe_marker_status(
        marker_path=Path(_require_non_empty_string(state["marker_path"], context="marker_path")),
        expected_payload=parameters.prompt.expected_marker_payload,
    )
    verification_reasons: list[str] = []
    if not bool(marker_status["exists"]):
        verification_reasons.append("probe marker file not found")
    if not bool(marker_status["valid_json"]):
        verification_reasons.append("probe marker file was not valid JSON")
    if not bool(marker_status["matches_expected"]):
        verification_reasons.append("probe marker payload did not match the tracked contract")

    report = {
        "demo": parameters.demo_id,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_output_dir": state["demo_output_dir"],
        "project_workdir": state["project_workdir"],
        "runtime_root": state["runtime_root"],
        "agent_def_dir": state["agent_def_dir"],
        "selected_tool": state["selected_tool"],
        "selected_blueprint": _require_non_empty_string(
            _require_mapping(state["selected_lane"], context="state.selected_lane").get(
                "blueprint"
            ),
            context="state.selected_lane.blueprint",
        ),
        "parameters": parameters_to_payload(parameters),
        "cao": state["cao"],
        "preflight": state["preflight"],
        "watch": {
            "session_manifest": str(session_manifest_path),
            "agent_identity": _require_non_empty_string(
                _require_mapping(state["session"], context="state.session").get("agent_identity"),
                context="state.session.agent_identity",
            ),
            "job_dir": _require_mapping(state["session"], context="state.session").get("job_dir"),
            "tmux_session_name": _require_mapping(state["session"], context="state.session").get(
                "tmux_session_name"
            ),
            "cao_base_url": _require_non_empty_string(
                state["cao"]["base_url"], context="cao.base_url"
            ),
            "cao_session_name": None if parsed.cao is None else parsed.cao.session_name,
            "cao_terminal_id": None if parsed.cao is None else parsed.cao.terminal_id,
            "tmux_window_name": None if parsed.cao is None else parsed.cao.tmux_window_name,
            "parsing_mode": None if parsed.cao is None else parsed.cao.parsing_mode,
        },
        "prompt": {
            "trigger_phrase": parameters.prompt.trigger_phrase,
            "prompt_path": state["prompt_path"],
            "prompt_text": Path(state["prompt_path"]).read_text(encoding="utf-8"),
            "prompt_events_path": str(layout.prompt_events_path),
            "prompt_result_path": str(layout.prompt_result_path),
            "summary": prompt_summary,
        },
        "marker": {
            "relative_path": parameters.prompt.marker_relative_path,
            "marker_path": state["marker_path"],
            "expected_payload": parameters.prompt.expected_marker_payload,
            **marker_status,
        },
        "artifacts": {
            "brain_build": str(layout.brain_build_path),
            "session_start": str(layout.session_start_path),
            "cao_start": str(layout.cao_start_path),
            "prompt_events": str(layout.prompt_events_path),
            "prompt_result": str(layout.prompt_result_path),
            "inspect": str(layout.inspect_path),
            "report": str(layout.report_path),
            "report_sanitized": str(layout.sanitized_report_path),
            "stop": str(layout.stop_path),
        },
        "verification": {
            "passed": not verification_reasons,
            "reasons": verification_reasons,
        },
    }
    _write_json(output_path, report)
    return report


def _sanitize_string(value: str, *, key: str | None, parent_key: str | None) -> str:
    """Sanitize one string value using field-aware placeholders."""

    if key in {"generated_at_utc"} or _TIMESTAMP_PATTERN.match(value):
        return "<TIMESTAMP>"
    if key in {"base_url", "cao_base_url"}:
        return "<CAO_BASE_URL>"
    if key in {"selected_tool", "tool"}:
        return "<SELECTED_TOOL>"
    if key in {"selected_blueprint", "blueprint"} and parent_key in {
        None,
        "report",
        "selected_lane",
    }:
        return "<SELECTED_BLUEPRINT>"
    if key in {"agent_identity", "agent_name"}:
        return "<AGENT_IDENTITY>"
    if key == "launch_executable":
        return "<TOOL_EXECUTABLE>"
    if key == "tmux_session_name":
        return "<TMUX_SESSION_NAME>"
    if key == "cao_session_name":
        return "<CAO_SESSION_NAME>"
    if key == "cao_terminal_id":
        return "<CAO_TERMINAL_ID>"
    if key == "tmux_window_name":
        return "<TMUX_WINDOW_NAME>"
    if key in _PATH_KEYS or _ABSOLUTE_PATH_PATTERN.match(value):
        return "<ABSOLUTE_PATH>"
    if key == "done_message":
        return "<DONE_MESSAGE>"
    return value


def sanitize_report(payload: Any, *, key: str | None = None, parent_key: str | None = None) -> Any:
    """Recursively sanitize one raw demo report payload."""

    if isinstance(payload, dict):
        sanitized_payload = dict(payload)
        if parent_key == "prompt" and key == "summary":
            sanitized_payload["event_count"] = "<EVENT_COUNT>"
            sanitized_payload["event_kinds"] = "<EVENT_KINDS>"
            sanitized_payload["done_message"] = "<DONE_MESSAGE>"
        if key == "cao":
            if "started_current_run" in sanitized_payload:
                sanitized_payload["started_current_run"] = "<CAO_START_STATE>"
            if "reused_existing_process" in sanitized_payload:
                sanitized_payload["reused_existing_process"] = "<CAO_REUSE_STATE>"
            if "message" in sanitized_payload:
                sanitized_payload["message"] = "<CAO_MESSAGE>"
        if key == "preflight":
            if "selected_allowlisted_env_keys" in sanitized_payload:
                sanitized_payload["selected_allowlisted_env_keys"] = "<ALLOWLISTED_ENV_KEYS>"
            if "required_credential_paths" in sanitized_payload:
                sanitized_payload["required_credential_paths"] = "<REQUIRED_CREDENTIAL_PATHS>"
            if "optional_credential_paths" in sanitized_payload:
                sanitized_payload["optional_credential_paths"] = "<OPTIONAL_CREDENTIAL_PATHS>"
            if "usable_auth_json" in sanitized_payload:
                sanitized_payload["usable_auth_json"] = "<USABLE_AUTH_JSON>"
        if key == "artifacts":
            sanitized_payload = {
                child_key: f"<ARTIFACT_PATH:{child_key}>" for child_key in sanitized_payload
            }
        return {
            child_key: sanitize_report(child_value, key=child_key, parent_key=key)
            for child_key, child_value in sanitized_payload.items()
        }
    if isinstance(payload, list):
        return [sanitize_report(item, key=None, parent_key=key) for item in payload]
    if isinstance(payload, str):
        return _sanitize_string(payload, key=key, parent_key=parent_key)
    return payload


def verify_sanitized_report(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Validate that sanitized actual output matches the expected contract."""

    if actual != expected:
        raise ValueError(
            "sanitized report mismatch\n"
            f"expected:\n{json.dumps(expected, indent=2, sort_keys=True)}\n"
            f"actual:\n{json.dumps(actual, indent=2, sort_keys=True)}"
        )


def auto_run(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
    tool: str,
    expected_report_path: Path,
    jobs_dir: Path | None,
    snapshot: bool,
) -> dict[str, Any]:
    """Run the one-shot automatic workflow end to end."""

    parameters = load_demo_parameters(parameters_path)
    state = start_demo(
        repo_root=repo_root,
        pack_dir=pack_dir,
        demo_output_dir=demo_output_dir,
        parameters_path=parameters_path,
        tool=tool,
        jobs_dir=jobs_dir,
    )
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    try:
        prompt_demo(
            repo_root=repo_root,
            parameters_path=parameters_path,
            state_path=layout.state_path,
        )
        wait_for_probe_marker(
            marker_path=Path(
                _require_non_empty_string(state["marker_path"], context="marker_path")
            ),
            expected_payload=parameters.prompt.expected_marker_payload,
            timeout_seconds=parameters.automatic.marker_timeout_seconds,
        )
        report = build_report(
            output_path=layout.report_path,
            parameters_path=parameters_path,
            state_path=layout.state_path,
        )
        sanitized = sanitize_report(report)
        _write_json(layout.sanitized_report_path, sanitized)
        if snapshot:
            expected_report_path.parent.mkdir(parents=True, exist_ok=True)
            expected_report_path.write_text(
                json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            verify_sanitized_report(
                sanitized,
                _require_mapping(
                    _read_json(expected_report_path), context=str(expected_report_path)
                ),
            )
        return report
    finally:
        stop_demo(repo_root=repo_root, demo_output_dir=demo_output_dir)


def stop_demo(*, repo_root: Path, demo_output_dir: Path) -> dict[str, Any]:
    """Stop the live session and demo-owned CAO when present."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    if not layout.state_path.exists():
        payload = {
            "stopped": False,
            "already_stopped": True,
            "message": f"demo state not found: {layout.state_path}",
        }
        _write_json(layout.stop_path, payload)
        return payload

    state = _load_state(layout.state_path)
    payload: dict[str, Any] = {"stopped": True}
    try:
        payload["session_stop"] = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "stop-session",
                "--agent-def-dir",
                _require_non_empty_string(state["agent_def_dir"], context="state.agent_def_dir"),
                "--agent-identity",
                _require_non_empty_string(
                    _require_mapping(state["session"], context="state.session").get(
                        "agent_identity"
                    ),
                    context="state.session.agent_identity",
                ),
            ],
            stdout_path=layout.stop_path.with_name("session_stop.json"),
            env=_command_environment(
                jobs_dir=None if state.get("jobs_dir") is None else Path(str(state["jobs_dir"]))
            ),
        )
    except Exception as exc:
        payload["session_stop_error"] = str(exc)
    if bool(_require_mapping(state["cao"], context="cao").get("managed")):
        try:
            payload["cao_stop"] = stop_demo_cao(
                repo_root=repo_root,
                demo_output_dir=demo_output_dir,
            )
        except Exception as exc:
            payload["cao_stop_error"] = str(exc)
    _write_json(layout.stop_path, payload)
    return payload


def _cmd_resolve_path(args: argparse.Namespace) -> int:
    """Resolve one optional path from the repository root."""

    default_relative = args.default_relative if args.default_relative is not None else None
    print(
        resolve_repo_relative_path(
            args.raw_path,
            repo_root=args.repo_root,
            default_relative=default_relative,
        )
    )
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    """Start the live demo session."""

    try:
        payload = start_demo(
            repo_root=args.repo_root,
            pack_dir=args.pack_dir,
            demo_output_dir=args.demo_output_dir,
            parameters_path=args.parameters,
            tool=args.tool,
            jobs_dir=args.jobs_dir,
        )
    except DemoSkipError as exc:
        print(f"SKIP: {exc}")
        return 0
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_prompt(args: argparse.Namespace) -> int:
    """Send the tracked probe prompt."""

    payload = prompt_demo(
        repo_root=args.repo_root,
        parameters_path=args.parameters,
        state_path=build_demo_layout(demo_output_dir=args.demo_output_dir).state_path,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect the persisted watch coordinates."""

    payload = inspect_demo(
        parameters_path=args.parameters,
        state_path=build_demo_layout(demo_output_dir=args.demo_output_dir).state_path,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Build, sanitize, and verify the demo report contract."""

    layout = build_demo_layout(demo_output_dir=args.demo_output_dir)
    parameters = load_demo_parameters(args.parameters)
    state = _load_state(layout.state_path)
    wait_for_probe_marker(
        marker_path=Path(_require_non_empty_string(state["marker_path"], context="marker_path")),
        expected_payload=parameters.prompt.expected_marker_payload,
        timeout_seconds=parameters.automatic.marker_timeout_seconds,
    )
    report = build_report(
        output_path=layout.report_path,
        parameters_path=args.parameters,
        state_path=layout.state_path,
    )
    sanitized = sanitize_report(report)
    _write_json(layout.sanitized_report_path, sanitized)
    if args.snapshot:
        args.expected_report.parent.mkdir(parents=True, exist_ok=True)
        args.expected_report.write_text(
            json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"snapshot updated: {args.expected_report}")
        return 0
    verify_sanitized_report(
        sanitized,
        _require_mapping(_read_json(args.expected_report), context=str(args.expected_report)),
    )
    print("verification passed")
    return 0


def _cmd_auto(args: argparse.Namespace) -> int:
    """Run the one-shot automatic workflow."""

    try:
        auto_run(
            repo_root=args.repo_root,
            pack_dir=args.pack_dir,
            demo_output_dir=args.demo_output_dir,
            parameters_path=args.parameters,
            tool=args.tool,
            expected_report_path=args.expected_report,
            jobs_dir=args.jobs_dir,
            snapshot=args.snapshot,
        )
    except DemoSkipError as exc:
        print(f"SKIP: {exc}")
        return 0
    print("verification passed")
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    """Stop the live demo session and demo-owned CAO."""

    payload = stop_demo(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the helper CLI parser."""

    parser = argparse.ArgumentParser(description="Skill invocation demo-pack helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve-path", help="Resolve one optional repo-relative path")
    resolve.add_argument("raw_path", nargs="?")
    resolve.add_argument("--repo-root", type=Path, required=True)
    resolve.add_argument("--default-relative")
    resolve.set_defaults(func=_cmd_resolve_path)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", type=Path, required=True)
    common.add_argument("--pack-dir", type=Path, required=True)
    common.add_argument("--parameters", type=Path, required=True)
    common.add_argument("--demo-output-dir", type=Path, required=True)
    common.add_argument("--tool", choices=("claude", "codex"), required=True)

    start = subparsers.add_parser("start", parents=[common], help="Start the live demo session")
    start.add_argument("--jobs-dir", type=Path)
    start.set_defaults(func=_cmd_start)

    prompt = subparsers.add_parser("prompt", parents=[common], help="Send the tracked probe prompt")
    prompt.set_defaults(func=_cmd_prompt)

    inspect = subparsers.add_parser(
        "inspect", parents=[common], help="Inspect the current live session"
    )
    inspect.set_defaults(func=_cmd_inspect)

    verify = subparsers.add_parser("verify", parents=[common], help="Verify the structured report")
    verify.add_argument("--expected-report", type=Path, required=True)
    verify.add_argument("--snapshot", action="store_true")
    verify.set_defaults(func=_cmd_verify)

    auto = subparsers.add_parser("auto", parents=[common], help="Run the automatic workflow")
    auto.add_argument("--expected-report", type=Path, required=True)
    auto.add_argument("--jobs-dir", type=Path)
    auto.add_argument("--snapshot", action="store_true")
    auto.set_defaults(func=_cmd_auto)

    stop = subparsers.add_parser("stop", parents=[common], help="Stop the live demo session")
    stop.set_defaults(func=_cmd_stop)
    return parser


def main() -> int:
    """Run the helper CLI."""

    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

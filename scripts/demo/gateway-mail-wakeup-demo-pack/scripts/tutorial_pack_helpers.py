#!/usr/bin/env python3
"""Helper utilities for the gateway mail wake-up demo pack."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
import tomllib
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import GatewayMailNotifierPutV1
from houmao.agents.realm_controller.gateway_storage import (
    build_gateway_mail_notifier_status,
    read_gateway_mail_notifier_record,
    read_gateway_notifier_audit_records,
    write_gateway_mail_notifier_record,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.cao.no_proxy import is_supported_loopback_cao_base_url
from houmao.cao.rest_client import CaoApiError, CaoRestClient
from houmao.cao.server_launcher import (
    load_cao_server_launcher_config,
    resolve_cao_server_runtime_artifacts,
)
from houmao.mailbox.filesystem import (
    resolve_active_mailbox_dir,
    resolve_active_mailbox_local_sqlite_path,
)
from houmao.mailbox.managed import DeliveryRequest
from houmao.mailbox.protocol import MailboxMessage, serialize_message_document

_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_OUTPUT_PATH_TOKEN = "{{OUTPUT_FILE_PATH}}"
_DEFAULT_DEMO_OUTPUT_DIR = Path("tmp/demo/gateway-mail-wakeup-demo-pack")
_FIXED_DEMO_PROJECT_COMMIT_UTC = "2026-03-18T00:00:00Z"
_FIXED_DEMO_PROJECT_COMMIT_MESSAGE = "Initial dummy project snapshot"
_FIXED_DEMO_PROJECT_AUTHOR_NAME = "Houmao Demo Fixture"
_FIXED_DEMO_PROJECT_AUTHOR_EMAIL = "houmao-demo-fixture@example.invalid"
_MANAGED_PROJECT_METADATA_NAME = ".houmao-demo-project.json"

_ARTIFACT_FILENAMES = {
    "brain_build": "brain_build.json",
    "cao_start": "cao_start.json",
    "gateway_attach": "gateway_attach.json",
    "idle_wait": "idle_wait.json",
    "inspect": "inspect.json",
    "notifier_enable": "notifier_enable.json",
    "report": "report.json",
    "report_sanitized": "report.sanitized.json",
    "session_start": "session_start.json",
}
_PATH_PLACEHOLDERS = {
    "demo_output_dir": "<DEMO_OUTPUT_DIR>",
    "project_workdir": "<PROJECT_WORKDIR>",
    "runtime_root": "<RUNTIME_ROOT>",
    "mailbox_root": "<MAILBOX_ROOT>",
    "agent_def_dir": "<AGENT_DEF_DIR>",
    "session_manifest": "<SESSION_MANIFEST_PATH>",
    "manifest_path": "<BRAIN_MANIFEST_PATH>",
    "home_path": "<BRAIN_HOME_PATH>",
    "launch_helper_path": "<LAUNCH_HELPER_PATH>",
    "job_dir": "<JOB_DIR>",
    "filesystem_root": "<MAILBOX_FILESYSTEM_ROOT>",
    "gateway_root": "<GATEWAY_ROOT>",
    "queue_path": "<GATEWAY_QUEUE_PATH>",
    "events_path": "<GATEWAY_EVENTS_PATH>",
    "log_path": "<GATEWAY_LOG_PATH>",
    "state_path": "<DEMO_STATE_PATH>",
    "output_file_path": "<OUTPUT_FILE_PATH>",
    "payload_file": "<DELIVERY_PAYLOAD_PATH>",
    "staged_message_path": "<STAGED_MESSAGE_PATH>",
    "shared_index_sqlite_path": "<MAILBOX_SHARED_INDEX_SQLITE_PATH>",
    "local_sqlite_path": "<MAILBOX_LOCAL_SQLITE_PATH>",
    "local_mailbox_dir": "<MAILBOX_LOCAL_DIR>",
    "cao_launcher_config_path": "<CAO_LAUNCHER_CONFIG_PATH>",
    "cao_runtime_root": "<CAO_RUNTIME_ROOT>",
    "cao_home_dir": "<CAO_HOME_DIR>",
    "cao_profile_store": "<CAO_PROFILE_STORE>",
    "cao_artifact_dir": "<CAO_ARTIFACT_DIR>",
    "cao_log_file": "<CAO_LOG_FILE>",
    "cao_launcher_result_file": "<CAO_LAUNCHER_RESULT_FILE>",
    "cao_ownership_file": "<CAO_OWNERSHIP_FILE>",
}
_VALUE_PLACEHOLDERS = {
    "generated_at_utc": "<TIMESTAMP>",
    "bindings_version": "<BINDINGS_VERSION>",
    "created_at_utc": "<TIMESTAMP>",
    "home_id": "<BRAIN_HOME_ID>",
    "last_notification_at_utc": "<TIMESTAMP>",
    "last_poll_at_utc": "<TIMESTAMP>",
    "message_id": "<MESSAGE_ID>",
    "thread_id": "<THREAD_ID>",
    "request_id": "<REQUEST_ID>",
    "enqueued_request_id": "<REQUEST_ID>",
    "last_notified_digest": "<DIGEST>",
    "unread_digest": "<DIGEST>",
    "state_source": "<STATE_SOURCE>",
}


RealmControllerRunner = Callable[
    [list[str], Path, Path, Path, dict[str, str] | None],
    dict[str, Any],
]
GitRunner = Callable[[list[str], Path, dict[str, str] | None], subprocess.CompletedProcess[str]]
LauncherRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


class DemoSkipError(RuntimeError):
    """Error used when the demo should exit with a tracked skip message."""


@dataclass(frozen=True)
class LauncherConfigSnapshot:
    """Minimal launcher-config fields needed for CAO profile-store discovery."""

    base_url: str
    runtime_root: Path | None
    home_dir: Path | None


@dataclass(frozen=True)
class DemoAgent:
    """Tracked managed-agent session configuration."""

    blueprint: str
    agent_identity: str
    mailbox_principal_id: str
    mailbox_address: str


@dataclass(frozen=True)
class DemoGateway:
    """Tracked gateway configuration."""

    host: str
    notifier_interval_seconds: int
    idle_poll_interval_seconds: int


@dataclass(frozen=True)
class DemoDelivery:
    """Tracked mail-injection defaults."""

    sender_principal_id: str
    sender_address: str
    subject: str
    body_file: str


@dataclass(frozen=True)
class DemoAutomatic:
    """Tracked automatic workflow configuration."""

    idle_timeout_seconds: int
    output_timeout_seconds: int
    output_file_relative_path: str


@dataclass(frozen=True)
class DemoParameters:
    """Validated tutorial input parameters."""

    schema_version: int
    demo_id: str
    agent_def_dir: str
    project_fixture: str
    backend: str
    cao_base_url: str
    shared_mailbox_root_template: str
    agent: DemoAgent
    gateway: DemoGateway
    delivery: DemoDelivery
    automatic: DemoAutomatic


@dataclass(frozen=True)
class DemoLayout:
    """Resolved demo-owned filesystem layout."""

    demo_output_dir: Path
    project_workdir: Path
    runtime_root: Path
    cao_dir: Path
    cao_launcher_config_path: Path
    cao_runtime_root: Path
    cao_start_path: Path
    inputs_dir: Path
    mailbox_root: Path
    deliveries_dir: Path
    output_dir: Path
    state_path: Path
    brain_build_path: Path
    session_start_path: Path
    gateway_attach_path: Path
    notifier_enable_path: Path
    idle_wait_path: Path
    inspect_path: Path
    report_path: Path
    sanitized_report_path: Path


def _read_json(path: Path) -> Any:
    """Load one JSON value from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _read_toml(path: Path) -> dict[str, Any]:
    """Load one TOML mapping from disk."""

    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return _require_mapping(payload, context=str(path))


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


def _cao_server_root(runtime_root: Path, *, base_url: str) -> Path:
    """Return the launcher-managed server root for one base URL."""

    parsed = urlparse(_normalize_cao_base_url(base_url))
    assert parsed.hostname is not None
    assert parsed.port is not None
    return (runtime_root.resolve() / "cao_servers" / f"{parsed.hostname}-{parsed.port}").resolve()


def _resolve_optional_config_path(raw_path: str | None, *, repo_root: Path) -> Path:
    """Resolve one optional launcher-config path."""

    if raw_path is None or not raw_path.strip():
        return (repo_root.resolve() / "config" / "cao-server-launcher" / "local.toml").resolve()
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root.resolve() / candidate).resolve()


def _resolve_optional_absolute_or_config_relative(
    raw_path: str | None,
    *,
    config_path: Path,
) -> Path | None:
    """Resolve one optional path relative to the launcher config when needed."""

    if raw_path is None or not raw_path.strip():
        return None
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (config_path.parent.resolve() / candidate).resolve()


def _load_launcher_config_snapshot(config_path: Path) -> LauncherConfigSnapshot:
    """Load the launcher config fields needed for CAO profile-store detection."""

    payload = _read_toml(config_path)
    base_url = _normalize_cao_base_url(
        _require_non_empty_string(payload.get("base_url"), context="base_url")
    )
    runtime_root = _resolve_optional_absolute_or_config_relative(
        payload.get("runtime_root"),
        config_path=config_path,
    )
    home_dir = _resolve_optional_absolute_or_config_relative(
        payload.get("home_dir"),
        config_path=config_path,
    )
    return LauncherConfigSnapshot(
        base_url=base_url,
        runtime_root=runtime_root,
        home_dir=home_dir,
    )


def _ownership_home_dir(path: Path, *, expected_base_url: str) -> Path | None:
    """Return the ownership-recorded CAO home dir when it matches the target URL."""

    if not path.exists():
        return None
    payload = _require_mapping(_read_json(path), context=str(path))
    managed_by = _require_non_empty_string(payload.get("managed_by"), context="managed_by")
    if managed_by != "houmao.cao.server_launcher":
        return None
    base_url = _normalize_cao_base_url(
        _require_non_empty_string(payload.get("base_url"), context="base_url")
    )
    if base_url != expected_base_url:
        return None
    home_dir_raw = payload.get("home_dir")
    if home_dir_raw is None:
        return None
    home_dir = Path(_require_non_empty_string(home_dir_raw, context="home_dir")).expanduser()
    return home_dir.resolve()


def default_cao_profile_store(*, cao_home: Path) -> Path:
    """Return the CAO agent-store path derived from one CAO home directory."""

    return (cao_home.resolve() / ".aws" / "cli-agent-orchestrator" / "agent-store").resolve()


def detect_cao_profile_store(
    *,
    repo_root: Path,
    cao_base_url: str,
    launcher_config_path: str | None = None,
) -> Path | None:
    """Best-effort detect the CAO profile store for the selected base URL."""

    normalized_base_url = _normalize_cao_base_url(cao_base_url)
    config_path = _resolve_optional_config_path(launcher_config_path, repo_root=repo_root)
    if not config_path.exists():
        return None

    config = _load_launcher_config_snapshot(config_path)
    if config.runtime_root is None:
        return None

    server_root = _cao_server_root(config.runtime_root, base_url=normalized_base_url)
    ownership_path = server_root / "launcher" / "ownership.json"
    ownership_home = _ownership_home_dir(ownership_path, expected_base_url=normalized_base_url)
    if ownership_home is not None:
        return default_cao_profile_store(cao_home=ownership_home)

    if config.base_url != normalized_base_url:
        return None

    if config.home_dir is not None:
        return default_cao_profile_store(cao_home=config.home_dir)
    return default_cao_profile_store(cao_home=server_root / "home")


def _agent_from_payload(payload: Any) -> DemoAgent:
    """Parse one agent configuration block."""

    mapping = _require_mapping(payload, context="agent")
    return DemoAgent(
        blueprint=_require_non_empty_string(mapping.get("blueprint"), context="agent.blueprint"),
        agent_identity=_require_non_empty_string(
            mapping.get("agent_identity"), context="agent.agent_identity"
        ),
        mailbox_principal_id=_require_non_empty_string(
            mapping.get("mailbox_principal_id"),
            context="agent.mailbox_principal_id",
        ),
        mailbox_address=_require_non_empty_string(
            mapping.get("mailbox_address"),
            context="agent.mailbox_address",
        ),
    )


def _gateway_from_payload(payload: Any) -> DemoGateway:
    """Parse one gateway configuration block."""

    mapping = _require_mapping(payload, context="gateway")
    notifier_interval_seconds = int(mapping.get("notifier_interval_seconds"))
    idle_poll_interval_seconds = int(mapping.get("idle_poll_interval_seconds"))
    if notifier_interval_seconds < 1:
        raise ValueError("gateway.notifier_interval_seconds must be >= 1")
    if idle_poll_interval_seconds < 1:
        raise ValueError("gateway.idle_poll_interval_seconds must be >= 1")
    return DemoGateway(
        host=_require_non_empty_string(mapping.get("host"), context="gateway.host"),
        notifier_interval_seconds=notifier_interval_seconds,
        idle_poll_interval_seconds=idle_poll_interval_seconds,
    )


def _delivery_from_payload(payload: Any) -> DemoDelivery:
    """Parse one delivery configuration block."""

    mapping = _require_mapping(payload, context="delivery")
    return DemoDelivery(
        sender_principal_id=_require_non_empty_string(
            mapping.get("sender_principal_id"),
            context="delivery.sender_principal_id",
        ),
        sender_address=_require_non_empty_string(
            mapping.get("sender_address"),
            context="delivery.sender_address",
        ),
        subject=_require_non_empty_string(mapping.get("subject"), context="delivery.subject"),
        body_file=_require_non_empty_string(mapping.get("body_file"), context="delivery.body_file"),
    )


def _automatic_from_payload(payload: Any) -> DemoAutomatic:
    """Parse one automatic workflow configuration block."""

    mapping = _require_mapping(payload, context="automatic")
    idle_timeout_seconds = int(mapping.get("idle_timeout_seconds"))
    output_timeout_seconds = int(mapping.get("output_timeout_seconds"))
    if idle_timeout_seconds < 1:
        raise ValueError("automatic.idle_timeout_seconds must be >= 1")
    if output_timeout_seconds < 1:
        raise ValueError("automatic.output_timeout_seconds must be >= 1")
    return DemoAutomatic(
        idle_timeout_seconds=idle_timeout_seconds,
        output_timeout_seconds=output_timeout_seconds,
        output_file_relative_path=_require_non_empty_string(
            mapping.get("output_file_relative_path"),
            context="automatic.output_file_relative_path",
        ),
    )


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load and validate the tracked demo parameters."""

    payload = _require_mapping(_read_json(path), context=str(path))
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise ValueError("demo parameters must use schema_version=1")

    parameters = DemoParameters(
        schema_version=int(schema_version),
        demo_id=_require_non_empty_string(payload.get("demo_id"), context="demo_id"),
        agent_def_dir=_require_non_empty_string(
            payload.get("agent_def_dir"), context="agent_def_dir"
        ),
        project_fixture=_require_non_empty_string(
            payload.get("project_fixture"), context="project_fixture"
        ),
        backend=_require_non_empty_string(payload.get("backend"), context="backend"),
        cao_base_url=_require_non_empty_string(payload.get("cao_base_url"), context="cao_base_url"),
        shared_mailbox_root_template=_require_non_empty_string(
            payload.get("shared_mailbox_root_template"),
            context="shared_mailbox_root_template",
        ),
        agent=_agent_from_payload(payload.get("agent")),
        gateway=_gateway_from_payload(payload.get("gateway")),
        delivery=_delivery_from_payload(payload.get("delivery")),
        automatic=_automatic_from_payload(payload.get("automatic")),
    )
    if parameters.backend != "cao_rest":
        raise ValueError("demo parameters backend must be cao_rest")
    if "{demo_output_dir}" not in parameters.shared_mailbox_root_template and (
        "{workspace_dir}" not in parameters.shared_mailbox_root_template
    ):
        raise ValueError(
            "shared_mailbox_root_template must contain {demo_output_dir} or {workspace_dir}"
        )
    return parameters


def parameters_to_payload(parameters: DemoParameters) -> dict[str, Any]:
    """Convert parameters into one JSON-serializable payload."""

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
    cao_dir = resolved_output_dir / "cao"
    return DemoLayout(
        demo_output_dir=resolved_output_dir,
        project_workdir=resolved_output_dir / "project",
        runtime_root=resolved_output_dir / "runtime",
        cao_dir=cao_dir,
        cao_launcher_config_path=cao_dir / "launcher.toml",
        cao_runtime_root=cao_dir / "runtime",
        cao_start_path=resolved_output_dir / _ARTIFACT_FILENAMES["cao_start"],
        inputs_dir=resolved_output_dir / "inputs",
        mailbox_root=resolved_output_dir / "shared-mailbox",
        deliveries_dir=resolved_output_dir / "deliveries",
        output_dir=resolved_output_dir / "outputs",
        state_path=resolved_output_dir / "demo_state.json",
        brain_build_path=resolved_output_dir / _ARTIFACT_FILENAMES["brain_build"],
        session_start_path=resolved_output_dir / _ARTIFACT_FILENAMES["session_start"],
        gateway_attach_path=resolved_output_dir / _ARTIFACT_FILENAMES["gateway_attach"],
        notifier_enable_path=resolved_output_dir / _ARTIFACT_FILENAMES["notifier_enable"],
        idle_wait_path=resolved_output_dir / _ARTIFACT_FILENAMES["idle_wait"],
        inspect_path=resolved_output_dir / _ARTIFACT_FILENAMES["inspect"],
        report_path=resolved_output_dir / _ARTIFACT_FILENAMES["report"],
        sanitized_report_path=resolved_output_dir / _ARTIFACT_FILENAMES["report_sanitized"],
    )


def render_mailbox_root(parameters: DemoParameters, *, demo_output_dir: Path) -> Path:
    """Render the shared mailbox root from the demo-output-dir template."""

    rendered = parameters.shared_mailbox_root_template.replace(
        "{demo_output_dir}", str(demo_output_dir.resolve())
    ).replace("{workspace_dir}", str(demo_output_dir.resolve()))
    return Path(rendered).expanduser().resolve()


def render_output_file_path(parameters: DemoParameters, *, demo_output_dir: Path) -> Path:
    """Render the demo-owned automatic output file path."""

    relative_path = Path(parameters.automatic.output_file_relative_path)
    if relative_path.is_absolute():
        return relative_path.resolve()
    return (demo_output_dir.resolve() / relative_path).resolve()


def _artifact_paths(layout: DemoLayout) -> dict[str, Path]:
    """Return the stable artifact-path mapping for the demo output directory."""

    return {
        "cao_start": layout.cao_start_path,
        "brain_build": layout.brain_build_path,
        "session_start": layout.session_start_path,
        "gateway_attach": layout.gateway_attach_path,
        "notifier_enable": layout.notifier_enable_path,
        "idle_wait": layout.idle_wait_path,
        "inspect": layout.inspect_path,
        "report": layout.report_path,
        "report_sanitized": layout.sanitized_report_path,
    }


def _copy_inputs(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Refresh tracked input files into the demo output directory."""

    if layout.inputs_dir.exists():
        shutil.rmtree(layout.inputs_dir)
    shutil.copytree(pack_dir / "inputs", layout.inputs_dir)


def _stderr_path_for(path: Path) -> Path:
    """Return the paired stderr path for one JSON artifact."""

    return path.with_suffix(".err")


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
    """Return whether the existing project directory is a managed dummy-project repo."""

    return _managed_project_metadata_path(project_workdir).is_file() and is_standalone_git_repo(
        project_workdir=project_workdir,
        run_git=run_git,
    )


def _project_fixture_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the selected tracked dummy-project fixture directory."""

    return resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)


def _write_managed_project_metadata(*, project_workdir: Path, fixture_dir: Path) -> None:
    """Write one marker payload for a managed copied dummy-project workdir."""

    _write_json(
        _managed_project_metadata_path(project_workdir),
        {
            "schema_version": 1,
            "managed_by": "gateway-mail-wakeup-demo-pack",
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
        [
            "pixi",
            "run",
            "python",
            "-m",
            "houmao.cao.tools.cao_server_launcher",
            *args,
        ],
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
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"launcher returned malformed JSON: {exc}") from exc
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
        "profile_store": str(default_cao_profile_store(cao_home=artifacts.home_dir)),
        "artifact_dir": str(artifacts.artifact_dir),
        "log_file": str(artifacts.log_file),
        "launcher_result_file": str(artifacts.launcher_result_file),
        "ownership_file": str(artifacts.ownership_file),
        "healthy": bool(start_payload.get("healthy")),
        "started_current_run": bool(start_payload.get("started_new_process")),
        "reused_existing_process": bool(start_payload.get("reused_existing_process")),
        "ownership_verified": ownership_verified,
        "recovery_attempted": False,
        "message": _require_non_empty_string(start_payload.get("message"), context="message"),
    }


def stop_demo_cao(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    cao_base_url: str,
    run_launcher: LauncherRunner = _default_launcher_runner,
) -> dict[str, Any]:
    """Stop demo-local CAO using the demo-owned launcher config."""

    del cao_base_url
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
    cao_profile_store: str | None,
) -> dict[str, Any]:
    """Resolve the CAO execution context for the demo."""

    normalized_base_url = _normalize_cao_base_url(cao_base_url)
    if supports_loopback_cao_launcher_management(normalized_base_url):
        return start_demo_cao(
            repo_root=repo_root,
            demo_output_dir=demo_output_dir,
            cao_base_url=normalized_base_url,
        )
    if cao_profile_store is None or not cao_profile_store.strip():
        raise DemoSkipError(
            "external CAO requires explicit CAO_PROFILE_STORE for the wake-up demo pack"
        )
    return {
        "managed": False,
        "base_url": normalized_base_url,
        "profile_store": str(Path(cao_profile_store).expanduser().resolve()),
        "message": "using external CAO with explicit profile store",
    }


def _command_environment(*, jobs_dir: Path | None) -> dict[str, str]:
    """Return subprocess environment overrides for realm-controller commands."""

    env = dict(**subprocess.os.environ)
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
    """Run one command, persist raw output, and parse a JSON stdout payload."""

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


def _run_realm_controller_json(
    *,
    repo_root: Path,
    args: list[str],
    stdout_path: Path,
    env: dict[str, str] | None = None,
    accepted_exit_codes: set[int] | None = None,
) -> dict[str, Any]:
    """Run one `houmao.agents.realm_controller` command and parse JSON output."""

    return _run_json_command(
        command=["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args],
        cwd=repo_root,
        stdout_path=stdout_path,
        stderr_path=_stderr_path_for(stdout_path),
        env=env,
        accepted_exit_codes=accepted_exit_codes,
    )


def _load_state(state_path: Path) -> dict[str, Any]:
    """Load one persisted demo state payload."""

    return _require_mapping(_read_json(state_path), context=str(state_path))


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    """Persist the current demo state payload."""

    _write_json(path, payload)


def _freshen_demo_output(
    *,
    pack_dir: Path,
    layout: DemoLayout,
) -> None:
    """Reset fresh-run artifacts while preserving the demo project directory."""

    for path in (
        layout.runtime_root,
        layout.mailbox_root,
        layout.deliveries_dir,
        layout.output_dir,
        layout.cao_dir,
    ):
        if path.exists():
            shutil.rmtree(path)
    stop_demo_path = layout.demo_output_dir / "stop_demo.json"
    if stop_demo_path.exists():
        stop_demo_path.unlink()
    for path in _artifact_paths(layout).values():
        if path.exists():
            path.unlink()
        stderr_path = _stderr_path_for(path)
        if stderr_path.exists():
            stderr_path.unlink()
    if layout.state_path.exists():
        layout.state_path.unlink()
    _copy_inputs(pack_dir=pack_dir, layout=layout)


def _agent_def_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the agent-definition directory for the demo."""

    return resolve_repo_relative_path(
        subprocess.os.environ.get("AGENT_DEF_DIR"),
        repo_root=repo_root,
        default_relative=parameters.agent_def_dir,
    )


def _gateway_endpoint_from_payload(payload: dict[str, Any]) -> GatewayEndpoint | None:
    """Build a gateway endpoint from an attach payload when available."""

    gateway_host = payload.get("gateway_host")
    gateway_port = payload.get("gateway_port")
    if not isinstance(gateway_host, str) or not isinstance(gateway_port, int):
        return None
    return GatewayEndpoint(host=gateway_host, port=gateway_port)


def _queue_path_from_state(state: dict[str, Any]) -> Path:
    """Return the durable queue path from the demo state."""

    gateway_root = Path(
        _require_non_empty_string(state["gateway"]["gateway_root"], context="gateway_root")
    )
    return (gateway_root / "queue.sqlite").resolve()


def _gateway_root_from_state(state: dict[str, Any]) -> Path:
    """Return the gateway root path from the demo state."""

    return Path(_require_non_empty_string(state["gateway"]["gateway_root"], context="gateway_root"))


def _notifier_status_payload(
    *,
    state: dict[str, Any],
    interval_seconds: int | None = None,
    enable: bool | None = None,
    disable: bool = False,
) -> dict[str, Any]:
    """Read or update notifier status with HTTP-first SQLite fallback behavior."""

    endpoint = _gateway_endpoint_from_payload(_require_mapping(state["gateway"], context="gateway"))
    queue_path = _queue_path_from_state(state)
    if endpoint is not None:
        client = GatewayClient(endpoint=endpoint)
        try:
            if enable:
                assert interval_seconds is not None
                status = client.put_mail_notifier(
                    GatewayMailNotifierPutV1(interval_seconds=interval_seconds)
                )
            elif disable:
                status = client.delete_mail_notifier()
            else:
                status = client.get_mail_notifier()
            return {"state_source": "http", **status.model_dump(mode="json")}
        except Exception:
            pass

    if enable:
        assert interval_seconds is not None
        record = write_gateway_mail_notifier_record(
            queue_path,
            enabled=True,
            interval_seconds=interval_seconds,
            last_error=None,
        )
    elif disable:
        record = write_gateway_mail_notifier_record(
            queue_path,
            enabled=False,
            interval_seconds=None,
            last_notified_digest=None,
            last_error=None,
        )
    else:
        record = read_gateway_mail_notifier_record(queue_path)
    status = build_gateway_mail_notifier_status(
        record=record,
        supported=True,
        support_error=None,
    )
    return {"state_source": "sqlite_fallback", **status.model_dump(mode="json")}


def _gateway_status_payload(
    *,
    repo_root: Path,
    agent_def_dir: Path,
    session_manifest_path: Path,
) -> dict[str, Any] | None:
    """Load the compact gateway status payload via CLI when possible."""

    temp_stdout = session_manifest_path.parent / ".gateway-status.tmp.json"
    temp_stderr = temp_stdout.with_suffix(".err")
    try:
        payload = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "gateway-status",
                "--agent-def-dir",
                str(agent_def_dir),
                "--agent-identity",
                str(session_manifest_path),
            ],
            stdout_path=temp_stdout,
            env=None,
        )
        return payload
    except Exception:
        return None
    finally:
        if temp_stdout.exists():
            temp_stdout.unlink()
        if temp_stderr.exists():
            temp_stderr.unlink()


def _wait_for_idle(
    *,
    repo_root: Path,
    agent_def_dir: Path,
    session_manifest_path: Path,
    cao_base_url: str,
    poll_interval_seconds: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Wait until the managed session appears idle."""

    manifest = load_session_manifest(session_manifest_path)
    payload = parse_session_manifest_payload(manifest.payload, source=str(manifest.path))
    terminal_id = None if payload.cao is None else payload.cao.terminal_id
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        checked_at_utc = datetime.now(UTC).isoformat(timespec="seconds")
        if terminal_id is not None:
            try:
                terminal = CaoRestClient(cao_base_url).get_terminal(terminal_id)
                if terminal.status == "idle":
                    return {
                        "ok": True,
                        "state_source": "cao",
                        "checked_at_utc": checked_at_utc,
                        "terminal_status": terminal.status,
                    }
            except CaoApiError:
                pass

        gateway_status = _gateway_status_payload(
            repo_root=repo_root,
            agent_def_dir=agent_def_dir,
            session_manifest_path=session_manifest_path,
        )
        if gateway_status is not None and (
            gateway_status.get("request_admission") == "open"
            and gateway_status.get("active_execution") == "idle"
        ):
            return {
                "ok": True,
                "state_source": "gateway_status",
                "checked_at_utc": checked_at_utc,
                "gateway_status": gateway_status,
            }
        time.sleep(float(poll_interval_seconds))

    raise TimeoutError(
        f"timed out waiting {timeout_seconds}s for an idle managed session before mail injection"
    )


def _generate_message_id() -> str:
    """Return one valid managed mailbox message id."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"msg-{timestamp}-{uuid.uuid4().hex}"


def _load_body_text(
    *,
    repo_root: Path,
    pack_dir: Path,
    body_content: str | None,
    body_file: str | None,
    output_file_path: Path | None,
) -> str:
    """Load one body string from inline text or a file."""

    sources = [body_content is not None, body_file is not None]
    if sources.count(True) != 1:
        raise ValueError("exactly one of body_content or body_file must be provided")
    if body_content is not None:
        body_text = body_content
    else:
        resolved_body_file = resolve_repo_relative_path(body_file, repo_root=repo_root)
        if not resolved_body_file.is_file():
            pack_local = (pack_dir / body_file).resolve()
            if not pack_local.is_file():
                raise ValueError(f"mail body file not found: {body_file}")
            resolved_body_file = pack_local
        body_text = resolved_body_file.read_text(encoding="utf-8")
    if output_file_path is not None:
        body_text = body_text.replace(_OUTPUT_PATH_TOKEN, str(output_file_path.resolve()))
    return body_text


def _delivery_request_payload(
    *,
    state: dict[str, Any],
    sender_principal_id: str,
    sender_address: str,
    subject: str,
    body_markdown: str,
    index: int,
) -> tuple[dict[str, Any], Path, Path]:
    """Materialize one staged message plus delivery payload file."""

    layout = build_demo_layout(demo_output_dir=Path(state["demo_output_dir"]))
    session = _require_mapping(state["session"], context="session")
    mailbox = _require_mapping(session["mailbox"], context="session.mailbox")
    message_id = _generate_message_id()
    created_at_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    staged_message_path = layout.deliveries_dir / "staged" / f"{message_id}.md"
    payload_file = layout.deliveries_dir / "payloads" / f"delivery-{index:03d}.json"
    payload = {
        "staged_message_path": str(staged_message_path),
        "message_id": message_id,
        "thread_id": message_id,
        "in_reply_to": None,
        "references": [],
        "created_at_utc": created_at_utc,
        "sender": {
            "principal_id": sender_principal_id,
            "address": sender_address,
        },
        "to": [
            {
                "principal_id": _require_non_empty_string(
                    mailbox.get("principal_id"),
                    context="session.mailbox.principal_id",
                ),
                "address": _require_non_empty_string(
                    mailbox.get("address"),
                    context="session.mailbox.address",
                ),
            }
        ],
        "cc": [],
        "reply_to": [],
        "subject": subject,
        "attachments": [],
        "headers": {},
    }
    request = DeliveryRequest.from_payload(payload)
    staged_message = MailboxMessage(
        message_id=request.message_id,
        thread_id=request.thread_id,
        in_reply_to=request.in_reply_to,
        references=list(request.references),
        created_at_utc=request.created_at_utc,
        sender=request.sender.to_mailbox_principal(),
        to=[principal.to_mailbox_principal() for principal in request.to],
        cc=[principal.to_mailbox_principal() for principal in request.cc],
        reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
        subject=request.subject,
        body_markdown=body_markdown,
        attachments=[attachment.to_mailbox_attachment() for attachment in request.attachments],
        headers=dict(request.headers),
    )
    staged_message_path.parent.mkdir(parents=True, exist_ok=True)
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    staged_message_path.write_text(
        serialize_message_document(staged_message),
        encoding="utf-8",
    )
    _write_json(payload_file, payload)
    return payload, staged_message_path, payload_file


def _run_delivery_script(
    *,
    repo_root: Path,
    mailbox_root: Path,
    payload_file: Path,
    artifact_path: Path,
) -> dict[str, Any]:
    """Run the mailbox delivery script through the projected rules/scripts boundary."""

    delivery_script = mailbox_root / "rules" / "scripts" / "deliver_message.py"
    return _run_json_command(
        command=[
            "pixi",
            "run",
            "python",
            str(delivery_script),
            "--mailbox-root",
            str(mailbox_root),
            "--payload-file",
            str(payload_file),
        ],
        cwd=repo_root,
        stdout_path=artifact_path,
        stderr_path=_stderr_path_for(artifact_path),
    )


def _delivery_artifact_paths(layout: DemoLayout, *, index: int) -> tuple[Path, Path]:
    """Return the stable delivery artifact paths for one send operation."""

    return (
        layout.deliveries_dir / f"delivery-{index:03d}.json",
        layout.deliveries_dir / f"delivery-{index:03d}.meta.json",
    )


def _record_delivery(
    *,
    repo_root: Path,
    pack_dir: Path,
    state: dict[str, Any],
    subject: str,
    body_content: str | None,
    body_file: str | None,
    output_file_path: Path | None,
) -> dict[str, Any]:
    """Deliver one message through the managed mailbox script boundary."""

    layout = build_demo_layout(demo_output_dir=Path(state["demo_output_dir"]))
    parameters = load_demo_parameters(Path(state["parameters_path"]))
    next_index = int(state.get("message_counter", 0)) + 1
    body_markdown = _load_body_text(
        repo_root=repo_root,
        pack_dir=pack_dir,
        body_content=body_content,
        body_file=body_file,
        output_file_path=output_file_path,
    )
    payload, staged_message_path, payload_file = _delivery_request_payload(
        state=state,
        sender_principal_id=parameters.delivery.sender_principal_id,
        sender_address=parameters.delivery.sender_address,
        subject=subject,
        body_markdown=body_markdown,
        index=next_index,
    )
    artifact_path, meta_path = _delivery_artifact_paths(layout, index=next_index)
    result = _run_delivery_script(
        repo_root=repo_root,
        mailbox_root=Path(state["mailbox_root"]),
        payload_file=payload_file,
        artifact_path=artifact_path,
    )
    metadata = {
        "index": next_index,
        "subject": subject,
        "payload_file": str(payload_file),
        "staged_message_path": str(staged_message_path),
        "message_id": payload["message_id"],
        "created_at_utc": payload["created_at_utc"],
        "body_preview": body_markdown.strip().splitlines()[:3],
        "result": result,
    }
    _write_json(meta_path, metadata)
    state["message_counter"] = next_index
    state["last_delivery_metadata"] = metadata
    _write_state(layout.state_path, state)
    return metadata


def _wait_for_output_file(*, state: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    """Wait until the configured output file appears or timeout expires."""

    output_file_path = Path(
        _require_non_empty_string(state["output_file_path"], context="output_file_path")
    )
    last_delivery = _require_mapping(
        state.get("last_delivery_metadata", {}),
        context="last_delivery_metadata",
    )
    delivery_timestamp = _require_non_empty_string(
        last_delivery.get("created_at_utc"),
        context="last_delivery_metadata.created_at_utc",
    )
    delivery_dt = datetime.fromisoformat(delivery_timestamp.replace("Z", "+00:00"))
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if output_file_path.is_file():
            content = output_file_path.read_text(encoding="utf-8").strip()
            modified_dt = datetime.fromtimestamp(output_file_path.stat().st_mtime, UTC)
            return {
                "exists": True,
                "output_file_path": str(output_file_path),
                "content": content,
                "timestamp_like": bool(_TIMESTAMP_PATTERN.match(content)),
                "modified_after_delivery": modified_dt >= delivery_dt,
            }
        time.sleep(1.0)

    raise TimeoutError(
        f"timed out waiting {timeout_seconds}s for demo output file {output_file_path}"
    )


def _read_unread_mailbox_state(*, mailbox_root: Path, mailbox_address: str) -> dict[str, Any]:
    """Read mailbox-local unread state for the managed session."""

    local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
        mailbox_root, address=mailbox_address
    )
    with sqlite3.connect(local_sqlite_path) as connection:
        rows = connection.execute(
            """
            SELECT message_id, thread_id, created_at_utc, subject
            FROM message_state
            WHERE is_read = 0
            ORDER BY created_at_utc ASC, message_id ASC
            """
        ).fetchall()
    messages = [
        {
            "message_id": str(row[0]),
            "thread_id": str(row[1]),
            "created_at_utc": str(row[2]),
            "subject": str(row[3]),
        }
        for row in rows
    ]
    return {
        "shared_index_sqlite_path": str((mailbox_root / "index.sqlite").resolve()),
        "local_mailbox_dir": str(resolve_active_mailbox_dir(mailbox_root, address=mailbox_address)),
        "local_sqlite_path": str(local_sqlite_path),
        "unread_count": len(messages),
        "unread_messages": messages,
    }


def _read_gateway_queue_state(*, queue_path: Path, events_path: Path) -> dict[str, Any]:
    """Load notifier-related queue and event evidence from the gateway root."""

    request_rows: list[dict[str, Any]] = []
    if queue_path.is_file():
        with sqlite3.connect(queue_path) as connection:
            rows = connection.execute(
                """
                SELECT request_id, request_kind, state, accepted_at_utc, started_at_utc, finished_at_utc
                FROM gateway_requests
                WHERE request_kind = 'mail_notifier_prompt'
                ORDER BY accepted_at_utc ASC
                """
            ).fetchall()
        request_rows = [
            {
                "request_id": str(row[0]),
                "request_kind": str(row[1]),
                "state": str(row[2]),
                "accepted_at_utc": None if row[3] is None else str(row[3]),
                "started_at_utc": None if row[4] is None else str(row[4]),
                "finished_at_utc": None if row[5] is None else str(row[5]),
            }
            for row in rows
        ]

    events: list[dict[str, Any]] = []
    if events_path.is_file():
        events = [
            _require_mapping(json.loads(line), context=str(events_path))
            for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return {
        "request_rows": request_rows,
        "event_kinds": sorted({str(event.get("kind")) for event in events}),
        "notifier_request_ids": [row["request_id"] for row in request_rows],
        "completed_request_ids": [
            row["request_id"] for row in request_rows if row.get("state") == "completed"
        ],
    }


def summarize_notifier_audit_records(rows: list[Any]) -> dict[str, Any]:
    """Reduce raw notifier audit rows to stable outcome-summary evidence."""

    observed_outcomes = sorted({row.outcome for row in rows if row.outcome != "empty"})
    unread_subjects = sorted({item.subject for row in rows for item in row.unread_summary})
    unread_message_ids = sorted({item.message_id for row in rows for item in row.unread_summary})
    return {
        "total_rows": len(rows),
        "observed_outcomes": observed_outcomes,
        "has_enqueued": any(row.outcome == "enqueued" for row in rows),
        "has_busy_skip": any(row.outcome == "busy_skip" for row in rows),
        "has_poll_error": any(row.outcome == "poll_error" for row in rows),
        "max_unread_count": max((row.unread_count or 0 for row in rows), default=0),
        "unread_subjects": unread_subjects,
        "unread_message_ids": unread_message_ids,
        "enqueued_request_id_present": any(
            row.enqueued_request_id is not None for row in rows if row.outcome == "enqueued"
        ),
    }


def inspect_demo(*, state_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    """Inspect the current demo artifacts and persist a raw inspection snapshot."""

    state = _load_state(state_path)
    layout = build_demo_layout(demo_output_dir=Path(state["demo_output_dir"]))
    session = _require_mapping(state["session"], context="session")
    mailbox = _require_mapping(session["mailbox"], context="session.mailbox")
    gateway_root = _gateway_root_from_state(state)
    queue_path = gateway_root / "queue.sqlite"
    events_path = gateway_root / "events.jsonl"
    log_path = gateway_root / "logs" / "gateway.log"

    notifier_status = _notifier_status_payload(state=state)
    audit_rows = read_gateway_notifier_audit_records(queue_path)
    audit_summary = summarize_notifier_audit_records(audit_rows)
    mailbox_state = _read_unread_mailbox_state(
        mailbox_root=Path(state["mailbox_root"]),
        mailbox_address=_require_non_empty_string(
            mailbox.get("address"), context="mailbox.address"
        ),
    )
    queue_state = _read_gateway_queue_state(queue_path=queue_path, events_path=events_path)
    output_file_path = Path(
        _require_non_empty_string(state["output_file_path"], context="output_file_path")
    )
    output_payload = {
        "output_file_path": str(output_file_path),
        "exists": output_file_path.is_file(),
        "content": output_file_path.read_text(encoding="utf-8").strip()
        if output_file_path.is_file()
        else None,
    }
    if output_payload["content"] is not None:
        output_payload["timestamp_like"] = bool(
            _TIMESTAMP_PATTERN.match(str(output_payload["content"]))
        )
    else:
        output_payload["timestamp_like"] = False

    inspection = {
        "demo": state["demo_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_output_dir": str(layout.demo_output_dir),
        "gateway_state": {
            "gateway_root": str(gateway_root),
            "queue_path": str(queue_path),
            "events_path": str(events_path),
            "log_path": str(log_path),
        },
        "notifier_status": notifier_status,
        "notifier_audit": {
            "summary": audit_summary,
            "rows": [
                {
                    "poll_time_utc": row.poll_time_utc,
                    "unread_count": row.unread_count,
                    "unread_digest": row.unread_digest,
                    "request_admission": row.request_admission,
                    "active_execution": row.active_execution,
                    "queue_depth": row.queue_depth,
                    "outcome": row.outcome,
                    "enqueued_request_id": row.enqueued_request_id,
                    "detail": row.detail,
                    "unread_summary": [
                        {
                            "message_id": item.message_id,
                            "thread_id": item.thread_id,
                            "created_at_utc": item.created_at_utc,
                            "subject": item.subject,
                        }
                        for item in row.unread_summary
                    ],
                }
                for row in audit_rows
            ],
        },
        "mailbox_state": mailbox_state,
        "queue_state": queue_state,
        "output_file": output_payload,
    }
    destination = layout.inspect_path if output_path is None else output_path.resolve()
    _write_json(destination, inspection)
    return inspection


def build_report(
    *,
    output_path: Path,
    parameters_path: Path,
    state_path: Path,
) -> dict[str, Any]:
    """Build one raw demo report from the persisted demo state."""

    state = _load_state(state_path)
    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=Path(state["demo_output_dir"]))
    inspection = inspect_demo(state_path=state_path, output_path=layout.inspect_path)
    output_info = inspection["output_file"]
    queue_state = inspection["queue_state"]
    notifier_status = inspection["notifier_status"]
    mailbox_state = inspection["mailbox_state"]
    audit_summary = inspection["notifier_audit"]["summary"]
    state_session = _require_mapping(state["session"], context="session")

    checks = {
        "cao_managed": bool(_require_mapping(state["cao"], context="cao").get("managed")),
        "gateway_attached": bool(
            _require_mapping(state["gateway"], context="gateway").get("gateway_root")
        ),
        "notifier_enabled": bool(notifier_status.get("enabled")),
        "notifier_enqueued_wakeup": bool(audit_summary["has_enqueued"]),
        "notifier_poll_error_free": not bool(audit_summary["has_poll_error"]),
        "shared_mailbox_index_present": Path(mailbox_state["shared_index_sqlite_path"]).is_file(),
        "mailbox_local_sqlite_present": Path(mailbox_state["local_sqlite_path"]).is_file(),
        "mailbox_unread_present": int(mailbox_state["unread_count"]) > 0,
        "queue_has_notifier_request": bool(queue_state["notifier_request_ids"]),
        "queue_completed_notifier_request": bool(queue_state["completed_request_ids"]),
        "output_file_exists": bool(output_info["exists"]),
        "output_file_contains_timestamp": bool(output_info["timestamp_like"]),
    }

    output_payload = {
        "output_file_path": output_info["output_file_path"],
        "exists": output_info["exists"],
        "content": output_info["content"],
        "timestamp_like": output_info["timestamp_like"],
    }
    if state.get("last_delivery_metadata") is not None and output_info["exists"]:
        delivery = _require_mapping(
            state["last_delivery_metadata"],
            context="last_delivery_metadata",
        )
        delivery_dt = datetime.fromisoformat(
            _require_non_empty_string(
                delivery.get("created_at_utc"),
                context="last_delivery_metadata.created_at_utc",
            ).replace("Z", "+00:00")
        )
        modified_dt = datetime.fromtimestamp(
            Path(output_info["output_file_path"]).stat().st_mtime,
            UTC,
        )
        output_payload["modified_after_delivery"] = modified_dt >= delivery_dt
        checks["output_file_newer_than_delivery"] = bool(output_payload["modified_after_delivery"])
    else:
        output_payload["modified_after_delivery"] = None
        checks["output_file_newer_than_delivery"] = False

    report = {
        "demo": parameters.demo_id,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_output_dir": state["demo_output_dir"],
        "project_workdir": state["project_workdir"],
        "runtime_root": state["runtime_root"],
        "mailbox_root": state["mailbox_root"],
        "agent_def_dir": state["agent_def_dir"],
        "parameters": parameters_to_payload(parameters),
        "cao": state["cao"],
        "artifacts": {key: str(path) for key, path in _artifact_paths(layout).items()},
        "steps": {
            "brain_build": _read_json(layout.brain_build_path),
            "session_start": _read_json(layout.session_start_path),
            "gateway_attach": _read_json(layout.gateway_attach_path),
            "notifier_enable": _read_json(layout.notifier_enable_path),
            "idle_wait": _read_json(layout.idle_wait_path)
            if layout.idle_wait_path.is_file()
            else None,
            "last_delivery": state.get("last_delivery_metadata"),
        },
        "notifier_status": notifier_status,
        "notifier_audit": inspection["notifier_audit"],
        "mailbox_state": mailbox_state,
        "queue_state": queue_state,
        "output_file": output_payload,
        "checks": checks,
        "session_manifest": state_session.get("session_manifest"),
    }
    _write_json(output_path, report)
    return report


def _sanitize_string(value: str, *, key: str | None, parent_key: str | None) -> str:
    """Sanitize one string value using field-aware placeholders."""

    if parent_key == "output_file" and key == "content":
        return "<OUTPUT_FILE_CONTENT>"
    if parent_key == "gateway_attach" and key == "detail":
        return "<GATEWAY_ATTACH_DETAIL>"
    if key in _VALUE_PLACEHOLDERS:
        return _VALUE_PLACEHOLDERS[key]
    if key in _PATH_PLACEHOLDERS:
        return _PATH_PLACEHOLDERS[key]
    if parent_key == "cao":
        cao_placeholders = {
            "launcher_config_path": "<CAO_LAUNCHER_CONFIG_PATH>",
            "runtime_root": "<CAO_RUNTIME_ROOT>",
            "home_dir": "<CAO_HOME_DIR>",
            "profile_store": "<CAO_PROFILE_STORE>",
            "artifact_dir": "<CAO_ARTIFACT_DIR>",
            "log_file": "<CAO_LOG_FILE>",
            "launcher_result_file": "<CAO_LAUNCHER_RESULT_FILE>",
            "ownership_file": "<CAO_OWNERSHIP_FILE>",
        }
        if key in cao_placeholders:
            return cao_placeholders[key]
    if parent_key == "mailbox_state":
        mailbox_placeholders = {
            "shared_index_sqlite_path": "<MAILBOX_SHARED_INDEX_SQLITE_PATH>",
            "local_sqlite_path": "<MAILBOX_LOCAL_SQLITE_PATH>",
            "local_mailbox_dir": "<MAILBOX_LOCAL_DIR>",
        }
        if key in mailbox_placeholders:
            return mailbox_placeholders[key]
    if parent_key == "artifacts" and key is not None:
        return f"<ARTIFACT_PATH:{key}>"
    if key in {"message_id", "thread_id"}:
        return "<MESSAGE_ID>" if key == "message_id" else "<THREAD_ID>"
    if key in {"request_id", "enqueued_request_id"}:
        return "<REQUEST_ID>"
    if key in {"unread_digest", "last_notified_digest"}:
        return "<DIGEST>"
    if key in {"content"} and _TIMESTAMP_PATTERN.match(value):
        return "<TIMESTAMP>"
    if _TIMESTAMP_PATTERN.match(value):
        return "<TIMESTAMP>"
    if _ABSOLUTE_PATH_PATTERN.match(value):
        return "<ABSOLUTE_PATH>"
    return value


def sanitize_report(payload: Any, *, key: str | None = None, parent_key: str | None = None) -> Any:
    """Recursively sanitize one raw demo report payload."""

    if isinstance(payload, dict):
        if key == "notifier_audit" and "rows" in payload:
            sanitized_payload = dict(payload)
            sanitized_payload["rows"] = "<RAW_NOTIFIER_AUDIT_ROWS>"
            return {
                child_key: sanitize_report(child_value, key=child_key, parent_key=key)
                for child_key, child_value in sanitized_payload.items()
            }
        sanitized_payload = dict(payload)
        for summary_key, placeholder in (
            ("total_rows", "<ROW_COUNT>"),
            ("observed_outcomes", "<OUTCOME_SET>"),
            ("unread_message_ids", "<MESSAGE_IDS>"),
            ("request_rows", "<NOTIFIER_REQUEST_ROWS>"),
            ("notifier_request_ids", "<REQUEST_IDS>"),
            ("completed_request_ids", "<REQUEST_IDS>"),
            ("body_preview", "<BODY_PREVIEW>"),
            ("gateway_port", "<GATEWAY_PORT>"),
            ("idle_wait", "<IDLE_WAIT>"),
        ):
            if summary_key in sanitized_payload:
                sanitized_payload[summary_key] = placeholder
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


def start_demo(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
    jobs_dir: Path | None,
) -> dict[str, Any]:
    """Start the live demo session, attach the gateway, and enable notifier polling."""

    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    project_fixture = _project_fixture_dir(parameters=parameters, repo_root=repo_root)
    stop_demo_path = layout.demo_output_dir / "stop_demo.json"
    allow_project_reprovision = False

    if layout.state_path.exists():
        if not stop_demo_path.exists():
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
    layout.deliveries_dir.mkdir(parents=True, exist_ok=True)
    layout.output_dir.mkdir(parents=True, exist_ok=True)

    agent_def_dir = _agent_def_dir(parameters=parameters, repo_root=repo_root)
    cao_context = _resolve_cao_context(
        repo_root=repo_root,
        demo_output_dir=demo_output_dir,
        cao_base_url=subprocess.os.environ.get("CAO_BASE_URL", parameters.cao_base_url),
        cao_profile_store=subprocess.os.environ.get("CAO_PROFILE_STORE"),
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
            "--blueprint",
            parameters.agent.blueprint,
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
            "--blueprint",
            parameters.agent.blueprint,
            "--backend",
            parameters.backend,
            "--cao-base-url",
            _require_non_empty_string(cao_context.get("base_url"), context="cao.base_url"),
            "--cao-profile-store",
            _require_non_empty_string(
                cao_context.get("profile_store"), context="cao.profile_store"
            ),
            "--workdir",
            str(layout.project_workdir),
            "--agent-identity",
            parameters.agent.agent_identity,
            "--mailbox-transport",
            "filesystem",
            "--mailbox-root",
            str(render_mailbox_root(parameters, demo_output_dir=layout.demo_output_dir)),
            "--mailbox-principal-id",
            parameters.agent.mailbox_principal_id,
            "--mailbox-address",
            parameters.agent.mailbox_address,
        ],
        stdout_path=layout.session_start_path,
        env=env,
    )
    attach_payload = _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "attach-gateway",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            _require_non_empty_string(
                session_payload.get("session_manifest"),
                context="session_manifest",
            ),
            "--gateway-host",
            parameters.gateway.host,
        ],
        stdout_path=layout.gateway_attach_path,
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
        "mailbox_root": str(
            render_mailbox_root(parameters, demo_output_dir=layout.demo_output_dir)
        ),
        "agent_def_dir": str(agent_def_dir.resolve()),
        "jobs_dir": None if jobs_dir is None else str(jobs_dir.resolve()),
        "cao": cao_context,
        "brain_build": build_payload,
        "session": session_payload,
        "gateway": attach_payload,
        "output_file_path": str(
            render_output_file_path(parameters, demo_output_dir=layout.demo_output_dir)
        ),
        "message_counter": 0,
    }
    notifier_payload = _notifier_status_payload(
        state=state,
        interval_seconds=parameters.gateway.notifier_interval_seconds,
        enable=True,
    )
    _write_json(layout.notifier_enable_path, notifier_payload)
    state["notifier"] = notifier_payload
    _write_state(layout.state_path, state)
    return state


def manual_send(
    *,
    repo_root: Path,
    pack_dir: Path,
    state_path: Path,
    subject: str | None,
    body_content: str | None,
    body_file: str | None,
) -> dict[str, Any]:
    """Inject one message through the managed mailbox delivery boundary."""

    state = _load_state(state_path)
    parameters = load_demo_parameters(Path(state["parameters_path"]))
    return _record_delivery(
        repo_root=repo_root,
        pack_dir=pack_dir,
        state=state,
        subject=subject or parameters.delivery.subject,
        body_content=body_content,
        body_file=body_file,
        output_file_path=None,
    )


def manual_send_many(
    *,
    repo_root: Path,
    pack_dir: Path,
    state_path: Path,
    count: int,
    subject_prefix: str,
    body_content: str | None,
    body_file: str | None,
) -> dict[str, Any]:
    """Inject a burst of messages against the same live session."""

    if count < 1:
        raise ValueError("count must be >= 1")
    deliveries: list[dict[str, Any]] = []
    for index in range(count):
        deliveries.append(
            manual_send(
                repo_root=repo_root,
                pack_dir=pack_dir,
                state_path=state_path,
                subject=f"{subject_prefix} #{index + 1}",
                body_content=body_content,
                body_file=body_file,
            )
        )
    payload = {
        "count": count,
        "deliveries": deliveries,
    }
    _write_json(state_path.parent / "burst_delivery.json", payload)
    return payload


def auto_run(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
    expected_report_path: Path,
    jobs_dir: Path | None,
    snapshot: bool,
) -> dict[str, Any]:
    """Run the one-shot automatic wake-up workflow end to end."""

    parameters = load_demo_parameters(parameters_path)
    state = start_demo(
        repo_root=repo_root,
        pack_dir=pack_dir,
        demo_output_dir=demo_output_dir,
        parameters_path=parameters_path,
        jobs_dir=jobs_dir,
    )
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    try:
        idle_payload = _wait_for_idle(
            repo_root=repo_root,
            agent_def_dir=Path(state["agent_def_dir"]),
            session_manifest_path=Path(state["session"]["session_manifest"]),
            cao_base_url=str(state["cao"]["base_url"]),
            poll_interval_seconds=parameters.gateway.idle_poll_interval_seconds,
            timeout_seconds=parameters.automatic.idle_timeout_seconds,
        )
        _write_json(layout.idle_wait_path, idle_payload)
        body_file = str((layout.inputs_dir / Path(parameters.delivery.body_file).name).resolve())
        _record_delivery(
            repo_root=repo_root,
            pack_dir=pack_dir,
            state=_load_state(layout.state_path),
            subject=parameters.delivery.subject,
            body_content=None,
            body_file=body_file,
            output_file_path=render_output_file_path(
                parameters,
                demo_output_dir=layout.demo_output_dir,
            ),
        )
        output_payload = _wait_for_output_file(
            state=_load_state(layout.state_path),
            timeout_seconds=parameters.automatic.output_timeout_seconds,
        )
        report = build_report(
            output_path=layout.report_path,
            parameters_path=parameters_path,
            state_path=layout.state_path,
        )
        if not bool(output_payload["exists"]):
            raise RuntimeError("automatic output wait finished without an output file")
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
    """Stop the live session and launcher-managed CAO when present."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    if not layout.state_path.exists():
        return {
            "stopped": False,
            "already_stopped": True,
            "message": f"demo state not found: {layout.state_path}",
        }
    state = _load_state(layout.state_path)
    stop_payloads: dict[str, Any] = {"stopped": True}
    try:
        _notifier_status_payload(state=state, disable=True)
    except Exception:
        pass
    try:
        stop_payloads["session_stop"] = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "stop-session",
                "--agent-def-dir",
                str(state["agent_def_dir"]),
                "--agent-identity",
                _require_non_empty_string(
                    _require_mapping(state["session"], context="session").get("agent_identity"),
                    context="session.agent_identity",
                ),
            ],
            stdout_path=layout.demo_output_dir / "session_stop.json",
            env=_command_environment(
                jobs_dir=None if state.get("jobs_dir") is None else Path(str(state["jobs_dir"])),
            ),
        )
    except Exception as exc:
        stop_payloads["session_stop_error"] = str(exc)
    if _require_mapping(state["cao"], context="cao").get("managed"):
        try:
            stop_payloads["cao_stop"] = stop_demo_cao(
                repo_root=repo_root,
                demo_output_dir=demo_output_dir,
                cao_base_url=_require_non_empty_string(
                    state["cao"]["base_url"], context="cao.base_url"
                ),
            )
        except Exception as exc:
            stop_payloads["cao_stop_error"] = str(exc)
    _write_json(layout.demo_output_dir / "stop_demo.json", stop_payloads)
    return stop_payloads


def _cmd_validate_parameters(args: argparse.Namespace) -> int:
    """Validate the tracked parameter file."""

    load_demo_parameters(args.parameters)
    print("parameters valid")
    return 0


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


def _cmd_ensure_project_workdir(args: argparse.Namespace) -> int:
    """Provision one copied dummy-project workdir from a tracked fixture."""

    print(
        ensure_project_workdir_from_fixture(
            repo_root=args.repo_root,
            project_fixture=args.project_fixture,
            project_workdir=args.project_workdir,
            allow_reprovision=args.allow_reprovision,
        )
    )
    return 0


def _cmd_start_demo_cao(args: argparse.Namespace) -> int:
    """Start or reuse one demo-local loopback CAO service."""

    payload = start_demo_cao(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        cao_base_url=args.cao_base_url,
    )
    if args.output is not None:
        _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_stop_demo_cao(args: argparse.Namespace) -> int:
    """Stop one demo-local CAO service."""

    payload = stop_demo_cao(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        cao_base_url=args.cao_base_url,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    """Start the manual demo session."""

    try:
        payload = start_demo(
            repo_root=args.repo_root,
            pack_dir=args.pack_dir,
            demo_output_dir=args.demo_output_dir,
            parameters_path=args.parameters,
            jobs_dir=args.jobs_dir,
        )
    except DemoSkipError as exc:
        print(f"SKIP: {exc}")
        return 0
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_manual_send(args: argparse.Namespace) -> int:
    """Inject one manual message."""

    payload = manual_send(
        repo_root=args.repo_root,
        pack_dir=args.pack_dir,
        state_path=build_demo_layout(demo_output_dir=args.demo_output_dir).state_path,
        subject=args.subject,
        body_content=args.body_content,
        body_file=args.body_file,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_manual_send_many(args: argparse.Namespace) -> int:
    """Inject a burst of messages."""

    payload = manual_send_many(
        repo_root=args.repo_root,
        pack_dir=args.pack_dir,
        state_path=build_demo_layout(demo_output_dir=args.demo_output_dir).state_path,
        count=args.count,
        subject_prefix=args.subject_prefix,
        body_content=args.body_content,
        body_file=args.body_file,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect the live or durable demo artifacts."""

    payload = inspect_demo(
        state_path=build_demo_layout(demo_output_dir=args.demo_output_dir).state_path,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Build, sanitize, and verify the demo report contract."""

    layout = build_demo_layout(demo_output_dir=args.demo_output_dir)
    report = build_report(
        output_path=layout.report_path,
        parameters_path=args.parameters,
        state_path=layout.state_path,
    )
    sanitized = sanitize_report(report)
    _write_json(layout.sanitized_report_path, sanitized)
    if args.snapshot:
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
    """Stop the live demo resources."""

    payload = stop_demo(repo_root=args.repo_root, demo_output_dir=args.demo_output_dir)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the helper CLI parser."""

    parser = argparse.ArgumentParser(description="Gateway mail wake-up demo-pack helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-parameters")
    validate.add_argument("parameters", type=Path)
    validate.set_defaults(func=_cmd_validate_parameters)

    resolve_path = subparsers.add_parser("resolve-path")
    resolve_path.add_argument("--repo-root", type=Path, required=True)
    resolve_path.add_argument("--default-relative")
    resolve_path.add_argument("raw_path", nargs="?")
    resolve_path.set_defaults(func=_cmd_resolve_path)

    workdir = subparsers.add_parser(
        "ensure-project-workdir",
        aliases=["ensure-project-worktree"],
    )
    workdir.add_argument("--repo-root", type=Path, required=True)
    workdir.add_argument("--project-fixture", type=Path, required=True)
    workdir.add_argument("--project-workdir", type=Path, required=True)
    workdir.add_argument("--allow-reprovision", action="store_true")
    workdir.set_defaults(func=_cmd_ensure_project_workdir)

    start_cao = subparsers.add_parser("start-demo-cao")
    start_cao.add_argument("--repo-root", type=Path, required=True)
    start_cao.add_argument("--demo-output-dir", type=Path, required=True)
    start_cao.add_argument("--cao-base-url", required=True)
    start_cao.add_argument("--output", type=Path)
    start_cao.set_defaults(func=_cmd_start_demo_cao)

    stop_cao = subparsers.add_parser("stop-demo-cao")
    stop_cao.add_argument("--repo-root", type=Path, required=True)
    stop_cao.add_argument("--demo-output-dir", type=Path, required=True)
    stop_cao.add_argument("--cao-base-url", required=True)
    stop_cao.set_defaults(func=_cmd_stop_demo_cao)

    for command_name, func in (
        ("start", _cmd_start),
        ("auto", _cmd_auto),
        ("verify", _cmd_verify),
        ("inspect", _cmd_inspect),
        ("stop", _cmd_stop),
        ("manual-send", _cmd_manual_send),
        ("manual-send-many", _cmd_manual_send_many),
    ):
        subparser = subparsers.add_parser(command_name)
        subparser.add_argument("--repo-root", type=Path, required=True)
        subparser.add_argument("--pack-dir", type=Path, required=True)
        subparser.add_argument("--parameters", type=Path, required=True)
        subparser.add_argument(
            "--demo-output-dir",
            type=Path,
            default=_DEFAULT_DEMO_OUTPUT_DIR,
        )
        if command_name in {"auto", "verify"}:
            subparser.add_argument("--expected-report", type=Path, required=True)
            subparser.add_argument("--snapshot", action="store_true")
        if command_name in {"start", "auto"}:
            subparser.add_argument("--jobs-dir", type=Path)
        if command_name == "manual-send":
            subparser.add_argument("--subject")
            subparser.add_argument("--body-content")
            subparser.add_argument("--body-file")
        if command_name == "manual-send-many":
            subparser.add_argument("--count", type=int, default=3)
            subparser.add_argument("--subject-prefix", default="Gateway wake-up burst")
            subparser.add_argument("--body-content")
            subparser.add_argument("--body-file")
        subparser.set_defaults(func=func)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the helper CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

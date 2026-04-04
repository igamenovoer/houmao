#!/usr/bin/env python3
"""Helper utilities for the mailbox roundtrip tutorial pack."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from houmao.cao.no_proxy import is_supported_loopback_cao_base_url
from houmao.cao.rest_client import CaoRestClient
from houmao.cao.server_launcher import (
    load_cao_server_launcher_config,
    resolve_cao_server_runtime_artifacts,
)
from houmao.demo.legacy.launch_support import normalize_demo_launch_backend, resolve_demo_preset_launch
from houmao.demo.legacy.cao_interactive_demo.models import (
    DEFAULT_LIVE_CAO_TIMEOUT_SECONDS,
    DEFAULT_TERMINAL_LOG_RELATIVE_DIR,
)
from houmao.demo.legacy.cao_interactive_demo.runtime import (
    _best_effort_output_text_tail,
    _best_effort_tool_state,
)
from houmao.mailbox.filesystem import (
    resolve_active_mailbox_dir,
    resolve_active_mailbox_local_sqlite_path,
)
from houmao.mailbox.protocol import parse_message_document
from houmao.owned_paths import AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR

_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")
_ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_REPORT_FLOW = [
    "sender_build",
    "receiver_build",
    "sender_start",
    "receiver_start",
    "mail_send",
    "receiver_check",
    "mail_reply",
    "sender_check",
]
_STOP_FLOW = [
    "sender_stop",
    "receiver_stop",
]
_COMMAND_FLOW = [*_REPORT_FLOW, *_STOP_FLOW]
_ARTIFACT_FILENAMES = {label: f"{label}.json" for label in _COMMAND_FLOW}
_PATH_PLACEHOLDERS = {
    "demo_output_dir": "<DEMO_OUTPUT_DIR>",
    "control_dir": "<CONTROL_DIR>",
    "project_workdir": "<PROJECT_WORKDIR>",
    "runtime_root": "<RUNTIME_ROOT>",
    "mailbox_root": "<MAILBOX_ROOT>",
    "chat_log_path": "<CHAT_LOG_PATH>",
    "agent_def_dir": "<AGENT_DEF_DIR>",
    "session_manifest": "<SESSION_MANIFEST_PATH>",
    "manifest_path": "<BRAIN_MANIFEST_PATH>",
    "home_path": "<BRAIN_HOME_PATH>",
    "launch_helper_path": "<LAUNCH_HELPER_PATH>",
    "job_dir": "<JOB_DIR>",
    "filesystem_root": "<MAILBOX_FILESYSTEM_ROOT>",
    "cao_launcher_config_path": "<CAO_LAUNCHER_CONFIG_PATH>",
    "cao_runtime_root": "<CAO_RUNTIME_ROOT>",
    "cao_home_dir": "<CAO_HOME_DIR>",
    "cao_profile_store": "<CAO_PROFILE_STORE>",
    "cao_artifact_dir": "<CAO_ARTIFACT_DIR>",
    "cao_log_file": "<CAO_LOG_FILE>",
    "cao_launcher_result_file": "<CAO_LAUNCHER_RESULT_FILE>",
    "cao_ownership_file": "<CAO_OWNERSHIP_FILE>",
    "shared_index_sqlite_path": "<MAILBOX_SHARED_INDEX_SQLITE_PATH>",
    "sender_mailbox_dir": "<SENDER_MAILBOX_DIR>",
    "sender_local_sqlite_path": "<SENDER_MAILBOX_LOCAL_SQLITE_PATH>",
    "receiver_mailbox_dir": "<RECEIVER_MAILBOX_DIR>",
    "receiver_local_sqlite_path": "<RECEIVER_MAILBOX_LOCAL_SQLITE_PATH>",
}
_VALUE_PLACEHOLDERS = {
    "generated_at_utc": "<TIMESTAMP>",
    "bindings_version": "<BINDINGS_VERSION>",
    "message_id": "<MESSAGE_ID>",
    "thread_id": "<THREAD_ID>",
    "request_id": "<REQUEST_ID>",
    "reply_parent_message_id": "<MESSAGE_ID>",
    "agent_id": "<AGENT_ID>",
    "home_id": "<BRAIN_HOME_ID>",
}
_TIMESTAMP_KEYS = {
    "created_at",
    "generated_at_utc",
    "ts_utc",
    "received_at",
    "sent_at",
    "started_at",
    "updated_at",
}
_DEFAULT_DEMO_OUTPUT_DIR = Path("scripts/demo/mailbox-roundtrip-tutorial-pack/outputs")
_DEFAULT_AUTOMATION_CAO_PARSING_MODE = "shadow_only"
_FIXED_DEMO_PROJECT_COMMIT_UTC = "2026-03-16T12:00:00Z"
_FIXED_DEMO_PROJECT_COMMIT_MESSAGE = "Initial dummy project snapshot"
_FIXED_DEMO_PROJECT_AUTHOR_NAME = "Houmao Demo Fixture"
_FIXED_DEMO_PROJECT_AUTHOR_EMAIL = "houmao-demo-fixture@example.invalid"
_MANAGED_PROJECT_METADATA_NAME = ".houmao-demo-project.json"


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
class DemoParticipant:
    """One tutorial participant definition."""

    blueprint: str
    agent_identity: str
    mailbox_principal_id: str
    mailbox_address: str


@dataclass(frozen=True)
class MessageConfig:
    """Tracked message content configuration."""

    subject: str
    initial_body_file: str
    reply_instructions_file: str


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
    sender: DemoParticipant
    receiver: DemoParticipant
    message: MessageConfig


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
    cao_start_path: Path
    chats_path: Path
    inputs_dir: Path
    mailbox_root: Path
    state_path: Path
    report_path: Path
    sanitized_report_path: Path
    verify_result_path: Path
    stop_result_path: Path


@dataclass(frozen=True)
class AutotestParticipantRequirement:
    """Resolved real-agent participant prerequisites for one tutorial pack run."""

    role: str
    blueprint_path: Path
    brain_recipe_path: Path
    tool_adapter_path: Path
    tool: str
    launch_executable: str
    config_profile: str
    config_profile_dir: Path
    credential_profile: str
    credential_profile_dir: Path
    credential_env_path: Path
    required_credential_paths: tuple[Path, ...]
    optional_credential_paths: tuple[Path, ...]


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
    """Best-effort detect the CAO profile store for the selected base URL.

    Detection order:

    1. Launcher ownership artifact for the target base URL, if present.
    2. Launcher config `home_dir` when the config base URL matches the target URL.
    3. Launcher default server-root-local `home/` when `home_dir` is omitted and
       the config base URL matches the target URL.
    """

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


def _participant_from_payload(payload: Any, *, context: str) -> DemoParticipant:
    """Parse one participant block."""

    mapping = _require_mapping(payload, context=context)
    return DemoParticipant(
        blueprint=_require_non_empty_string(
            mapping.get("blueprint"), context=f"{context}.blueprint"
        ),
        agent_identity=_require_non_empty_string(
            mapping.get("agent_identity"), context=f"{context}.agent_identity"
        ),
        mailbox_principal_id=_require_non_empty_string(
            mapping.get("mailbox_principal_id"),
            context=f"{context}.mailbox_principal_id",
        ),
        mailbox_address=_require_non_empty_string(
            mapping.get("mailbox_address"), context=f"{context}.mailbox_address"
        ),
    )


def _message_from_payload(payload: Any) -> MessageConfig:
    """Parse one message block."""

    mapping = _require_mapping(payload, context="message")
    return MessageConfig(
        subject=_require_non_empty_string(mapping.get("subject"), context="message.subject"),
        initial_body_file=_require_non_empty_string(
            mapping.get("initial_body_file"), context="message.initial_body_file"
        ),
        reply_instructions_file=_require_non_empty_string(
            mapping.get("reply_instructions_file"), context="message.reply_instructions_file"
        ),
    )


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load and validate the tracked tutorial parameters."""

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
        sender=_participant_from_payload(payload.get("sender"), context="sender"),
        receiver=_participant_from_payload(payload.get("receiver"), context="receiver"),
        message=_message_from_payload(payload.get("message")),
    )
    if normalize_demo_launch_backend(parameters.backend) != "local_interactive":
        raise ValueError("demo parameters backend must be local_interactive or legacy cao_rest")
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
    control_dir = resolved_output_dir / "control"
    return DemoLayout(
        demo_output_dir=resolved_output_dir,
        control_dir=control_dir,
        project_workdir=resolved_output_dir / "project",
        runtime_root=resolved_output_dir / "runtime",
        cao_dir=cao_dir,
        cao_launcher_config_path=cao_dir / "launcher.toml",
        cao_runtime_root=cao_dir / "runtime",
        cao_start_path=control_dir / "cao_start.json",
        chats_path=resolved_output_dir / "chats.jsonl",
        inputs_dir=resolved_output_dir / "inputs",
        mailbox_root=resolved_output_dir / "mailbox",
        state_path=control_dir / "demo_state.json",
        report_path=control_dir / "report.json",
        sanitized_report_path=control_dir / "report.sanitized.json",
        verify_result_path=control_dir / "verify_result.json",
        stop_result_path=control_dir / "stop_result.json",
    )


def _default_autotest_jobs_dir(*, demo_output_dir: Path) -> Path:
    """Return the default demo-local jobs root for real-agent autotests."""

    return (build_demo_layout(demo_output_dir=demo_output_dir).runtime_root / "jobs").resolve()


def _default_autotest_registry_root(*, demo_output_dir: Path) -> Path:
    """Return the default demo-local registry root for real-agent autotests."""

    return (build_demo_layout(demo_output_dir=demo_output_dir).runtime_root / "registry").resolve()


def _path_is_within(path: Path, *, parent: Path) -> bool:
    """Return whether one resolved path stays under the selected parent root."""

    try:
        return path.resolve().is_relative_to(parent.resolve())
    except ValueError:
        return False


def _tool_check_payload(command_name: str) -> dict[str, Any]:
    """Return one structured local executable check."""

    resolved = shutil.which(command_name)
    return {
        "command": command_name,
        "path": resolved,
        "ok": resolved is not None,
    }


def _path_check_payload(path: Path, *, required: bool, kind: str) -> dict[str, Any]:
    """Return one structured path/readability check."""

    resolved = path.expanduser().resolve()
    exists = resolved.exists()
    is_expected_kind = resolved.is_dir() if kind == "dir" else resolved.is_file()
    readable = exists and os.access(resolved, os.R_OK)
    return {
        "path": str(resolved),
        "required": required,
        "kind": kind,
        "exists": exists,
        "readable": readable,
        "ok": (exists and is_expected_kind and readable) or (not required and not exists),
    }


def _resolve_autotest_participant_requirement(
    *,
    agent_def_dir: Path,
    participant: DemoParticipant,
    role: str,
) -> AutotestParticipantRequirement:
    """Resolve the concrete real-agent prerequisite paths for one participant."""

    resolved_launch = resolve_demo_preset_launch(
        agent_def_dir=agent_def_dir,
        preset_path=participant.blueprint,
    )
    blueprint_path = resolved_launch.preset_path
    recipe = resolved_launch.preset
    if resolved_launch.auth_path is None or resolved_launch.auth_env_path is None:
        raise ValueError(
            f"participant preset must declare auth-backed launch inputs: {blueprint_path}"
        )
    return AutotestParticipantRequirement(
        role=role,
        blueprint_path=blueprint_path,
        brain_recipe_path=resolved_launch.preset_path,
        tool_adapter_path=resolved_launch.adapter_path,
        tool=recipe.tool,
        launch_executable=resolved_launch.adapter.launch_executable,
        config_profile=recipe.config_profile,
        config_profile_dir=resolved_launch.setup_path,
        credential_profile=recipe.credential_profile,
        credential_profile_dir=resolved_launch.auth_path,
        credential_env_path=resolved_launch.auth_env_path,
        required_credential_paths=resolved_launch.required_auth_paths,
        optional_credential_paths=resolved_launch.optional_auth_paths,
    )


def _autotest_output_root_status(layout: DemoLayout) -> dict[str, Any]:
    """Return whether the selected demo-output root is fresh or safely reusable."""

    if not layout.demo_output_dir.exists():
        return {
            "status": "fresh",
            "ok": True,
            "reason": "demo output directory does not exist yet",
        }

    entries = sorted(child.name for child in layout.demo_output_dir.iterdir())
    if layout.state_path.exists():
        state = _require_mapping(_read_json(layout.state_path), context=str(layout.state_path))
        steps = _require_mapping(state.get("steps"), context="steps")
        stop_complete = bool(steps.get("stop_complete"))
        return {
            "status": "reusable" if stop_complete else "blocked",
            "ok": stop_complete,
            "reason": (
                "existing stopped demo state may be reprovisioned"
                if stop_complete
                else "demo state exists and the previous run has not completed `stop`"
            ),
            "state_path": str(layout.state_path),
            "entries": entries,
        }

    if entries:
        return {
            "status": "blocked",
            "ok": False,
            "reason": "demo output directory already contains files without a stopped demo state",
            "entries": entries,
        }

    return {
        "status": "fresh",
        "ok": True,
        "reason": "demo output directory exists but is empty",
        "entries": entries,
    }


def resolve_real_agent_preflight(
    *,
    repo_root: Path,
    pack_dir: Path,
    parameters_path: Path,
    demo_output_dir: Path,
    jobs_dir: Path | None = None,
    registry_root: Path | None = None,
    case_id: str = "real-agent-preflight",
) -> dict[str, Any]:
    """Collect fail-fast prerequisite checks for one real-agent autotest case."""

    del pack_dir
    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    agent_def_dir = resolve_repo_relative_path(
        parameters.agent_def_dir,
        repo_root=repo_root,
    )
    selected_jobs_dir = (
        jobs_dir.resolve()
        if jobs_dir is not None
        else _default_autotest_jobs_dir(demo_output_dir=layout.demo_output_dir)
    )
    selected_registry_root = (
        registry_root.resolve()
        if registry_root is not None
        else _default_autotest_registry_root(demo_output_dir=layout.demo_output_dir)
    )

    blockers: list[str] = []
    tools: dict[str, dict[str, Any]] = {}
    for command_name in ("pixi", "tmux"):
        check = _tool_check_payload(command_name)
        tools[command_name] = check
        if not check["ok"]:
            blockers.append(f"missing required executable `{command_name}` on PATH")

    participants_payload: dict[str, dict[str, Any]] = {}
    for role, participant in (("sender", parameters.sender), ("receiver", parameters.receiver)):
        try:
            requirement = _resolve_autotest_participant_requirement(
                agent_def_dir=agent_def_dir,
                participant=participant,
                role=role,
            )
        except Exception as exc:
            blockers.append(f"{role}: {exc}")
            participants_payload[role] = {
                "role": role,
                "ok": False,
                "error": str(exc),
            }
            continue

        launch_check = _tool_check_payload(requirement.launch_executable)
        tools.setdefault(requirement.launch_executable, launch_check)
        if not launch_check["ok"]:
            blockers.append(
                f"{role}: required executable `{requirement.launch_executable}` is not on PATH"
            )

        config_check = _path_check_payload(
            requirement.config_profile_dir, required=True, kind="dir"
        )
        env_check = _path_check_payload(requirement.credential_env_path, required=True, kind="file")
        required_file_checks = [
            _path_check_payload(path, required=True, kind="file")
            for path in requirement.required_credential_paths
        ]
        optional_file_checks = [
            _path_check_payload(path, required=False, kind="file")
            for path in requirement.optional_credential_paths
        ]

        failed_checks = [
            check["path"]
            for check in [config_check, env_check, *required_file_checks]
            if not bool(check["ok"])
        ]
        if failed_checks:
            blockers.append(
                f"{role}: missing or unreadable prerequisite paths: {', '.join(failed_checks)}"
            )

        participants_payload[role] = {
            "role": role,
            "ok": not failed_checks and bool(launch_check["ok"]),
            "tool": requirement.tool,
            "launch_executable": requirement.launch_executable,
            "launch_executable_path": launch_check["path"],
            "blueprint_path": str(requirement.blueprint_path),
            "brain_recipe_path": str(requirement.brain_recipe_path),
            "tool_adapter_path": str(requirement.tool_adapter_path),
            "config_profile": requirement.config_profile,
            "config_profile_dir": config_check,
            "credential_profile": requirement.credential_profile,
            "credential_profile_dir": str(requirement.credential_profile_dir),
            "credential_env": env_check,
            "required_credential_files": required_file_checks,
            "optional_credential_files": optional_file_checks,
        }

    output_root = _autotest_output_root_status(layout)
    if not bool(output_root["ok"]):
        blockers.append(str(output_root["reason"]))

    isolation = {
        "jobs_dir": str(selected_jobs_dir),
        "jobs_dir_ok": _path_is_within(selected_jobs_dir, parent=layout.demo_output_dir),
        "registry_root": str(selected_registry_root),
        "registry_root_ok": _path_is_within(selected_registry_root, parent=layout.demo_output_dir),
        "env_var_name": AGENTSYS_GLOBAL_REGISTRY_DIR_ENV_VAR,
    }
    if not isolation["jobs_dir_ok"]:
        blockers.append(
            f"autotest jobs dir must stay under the selected demo output directory: {selected_jobs_dir}"
        )
    if not isolation["registry_root_ok"]:
        blockers.append(
            "autotest registry root must stay under the selected demo output directory: "
            f"{selected_registry_root}"
        )

    selected_cao_base_url = _normalize_cao_base_url(
        os.environ.get("CAO_BASE_URL", parameters.cao_base_url)
    )
    supports_loopback = supports_loopback_cao_launcher_management(selected_cao_base_url)
    expected_cao_home = (
        _cao_server_root(layout.cao_runtime_root, base_url=selected_cao_base_url) / "home"
    ).resolve()
    expected_cao_profile_store = default_cao_profile_store(cao_home=expected_cao_home)
    requested_profile_store_raw = os.environ.get("CAO_PROFILE_STORE")
    requested_profile_store = (
        Path(requested_profile_store_raw).expanduser().resolve()
        if requested_profile_store_raw and requested_profile_store_raw.strip()
        else None
    )
    cao_payload = {
        "base_url": selected_cao_base_url,
        "supports_demo_local_loopback_management": supports_loopback,
        "expected_profile_store": str(expected_cao_profile_store),
        "requested_profile_store": (
            None if requested_profile_store is None else str(requested_profile_store)
        ),
        "ownership_mode": "demo-local-loopback" if supports_loopback else "unsupported-external",
    }
    if not supports_loopback:
        blockers.append(
            "real-agent autotest only supports loopback CAO URLs owned through the demo-local "
            f"launcher flow; received `{selected_cao_base_url}`"
        )
    if (
        requested_profile_store is not None
        and requested_profile_store != expected_cao_profile_store
    ):
        blockers.append(
            "CAO_PROFILE_STORE does not match the demo-managed loopback profile store expected "
            f"for `{selected_cao_base_url}`"
        )

    ok = not blockers
    return {
        "case_id": case_id,
        "ok": ok,
        "demo_output_dir": str(layout.demo_output_dir),
        "parameters_path": str(parameters_path.resolve()),
        "agent_def_dir": str(agent_def_dir),
        "tools": tools,
        "participants": participants_payload,
        "output_root": output_root,
        "isolation": isolation,
        "cao": cao_payload,
        "blockers": blockers,
    }


def render_mailbox_root(parameters: DemoParameters, *, demo_output_dir: Path) -> Path:
    """Render the shared mailbox root from the demo-output-dir template."""

    rendered = parameters.shared_mailbox_root_template.replace(
        "{demo_output_dir}", str(demo_output_dir.resolve())
    ).replace("{workspace_dir}", str(demo_output_dir.resolve()))
    return Path(rendered).expanduser().resolve()


def extract_json_value(path: Path, dotted_path: str) -> Any:
    """Extract one dotted-path value from a JSON document."""

    value: Any = _read_json(path)
    for segment in dotted_path.split("."):
        if isinstance(value, dict) and segment in value:
            value = value[segment]
            continue
        raise ValueError(f"{path}: missing field `{dotted_path}`")
    return value


def extract_message_id(path: Path) -> str:
    """Extract one non-empty message_id from a mail-send payload."""

    payload = _require_mapping(_read_json(path), context=str(path))
    return _require_non_empty_string(payload.get("message_id"), context="message_id")


def _resolve_canonical_message_path(mailbox_root: Path, *, message_id: str) -> Path:
    """Resolve one canonical mailbox message path by message id."""

    matches = sorted((mailbox_root.resolve() / "messages").glob(f"*/{message_id}.md"))
    if not matches:
        raise ValueError(f"missing canonical mailbox message `{message_id}` under {mailbox_root}")
    if len(matches) > 1:
        raise ValueError(
            f"multiple canonical mailbox messages found for `{message_id}` under {mailbox_root}"
        )
    return matches[0].resolve()


def _read_mailbox_unread_count(mailbox_root: Path, *, address: str) -> int:
    """Return the unread-message count from mailbox-local SQLite state."""

    local_sqlite_path = resolve_active_mailbox_local_sqlite_path(mailbox_root, address=address)
    with sqlite3.connect(local_sqlite_path) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM message_state
            WHERE is_read = 0
            """
        ).fetchone()
    if row is None:
        return 0
    return int(row[0])


def inspect_roundtrip_mailbox(
    *,
    mailbox_root: Path,
    sender_address: str,
    receiver_address: str,
    send_message_id: str,
    reply_message_id: str,
    initial_body_path: Path,
) -> dict[str, Any]:
    """Inspect canonical roundtrip mailbox artifacts for one completed demo run."""

    send_message_path = _resolve_canonical_message_path(mailbox_root, message_id=send_message_id)
    reply_message_path = _resolve_canonical_message_path(mailbox_root, message_id=reply_message_id)
    send_message = parse_message_document(send_message_path.read_text(encoding="utf-8"))
    reply_message = parse_message_document(reply_message_path.read_text(encoding="utf-8"))
    initial_body = initial_body_path.read_text(encoding="utf-8")

    sender_mailbox_dir = resolve_active_mailbox_dir(mailbox_root, address=sender_address)
    receiver_mailbox_dir = resolve_active_mailbox_dir(mailbox_root, address=receiver_address)
    sender_local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
        mailbox_root,
        address=sender_address,
    )
    receiver_local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
        mailbox_root,
        address=receiver_address,
    )
    sender_sent_projection = sender_mailbox_dir / "sent" / f"{send_message_id}.md"
    receiver_inbox_projection = receiver_mailbox_dir / "inbox" / f"{send_message_id}.md"
    receiver_sent_projection = receiver_mailbox_dir / "sent" / f"{reply_message_id}.md"
    sender_inbox_projection = sender_mailbox_dir / "inbox" / f"{reply_message_id}.md"

    return {
        "send_message_id": send_message.message_id,
        "reply_message_id": reply_message.message_id,
        "send_message_path": str(send_message_path),
        "reply_message_path": str(reply_message_path),
        "sender_mailbox_dir": str(sender_mailbox_dir),
        "sender_local_sqlite_path": str(sender_local_sqlite_path),
        "receiver_mailbox_dir": str(receiver_mailbox_dir),
        "receiver_local_sqlite_path": str(receiver_local_sqlite_path),
        "send_body_markdown": send_message.body_markdown,
        "reply_body_markdown": reply_message.body_markdown,
        "send_body_matches_input": send_message.body_markdown == initial_body,
        "reply_body_present": bool(reply_message.body_markdown.strip()),
        "send_thread_matches_message_id": send_message.thread_id == send_message_id,
        "reply_thread_matches_send": reply_message.thread_id == send_message_id,
        "reply_parent_matches_send": reply_message.in_reply_to == send_message_id,
        "reply_references_send": bool(reply_message.references)
        and reply_message.references[-1] == send_message_id,
        "sender_sent_projection_path": str(sender_sent_projection),
        "sender_sent_projection_targets_send": sender_sent_projection.is_symlink()
        and sender_sent_projection.resolve() == send_message_path,
        "receiver_inbox_projection_path": str(receiver_inbox_projection),
        "receiver_inbox_projection_targets_send": receiver_inbox_projection.is_symlink()
        and receiver_inbox_projection.resolve() == send_message_path,
        "receiver_sent_projection_path": str(receiver_sent_projection),
        "receiver_sent_projection_targets_reply": receiver_sent_projection.is_symlink()
        and receiver_sent_projection.resolve() == reply_message_path,
        "sender_inbox_projection_path": str(sender_inbox_projection),
        "sender_inbox_projection_targets_reply": sender_inbox_projection.is_symlink()
        and sender_inbox_projection.resolve() == reply_message_path,
        "sender_unread_count": _read_mailbox_unread_count(mailbox_root, address=sender_address),
        "receiver_unread_count": _read_mailbox_unread_count(mailbox_root, address=receiver_address),
    }


def _append_chat_event(
    layout: DemoLayout,
    *,
    kind: str,
    sender: str,
    recipient: str,
    content: str,
    message_id: str,
    thread_id: str,
    in_reply_to: str | None = None,
    subject: str | None = None,
) -> None:
    """Append one semantic tutorial chat event to the pack-owned chat log."""

    event = {
        "ts_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": kind,
        "from": sender,
        "to": recipient,
        "content": content,
        "message_id": message_id,
        "thread_id": thread_id,
    }
    if in_reply_to is not None:
        event["in_reply_to"] = in_reply_to
    if subject is not None:
        event["subject"] = subject
    layout.chats_path.parent.mkdir(parents=True, exist_ok=True)
    with layout.chats_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _load_chat_events(chats_path: Path) -> list[dict[str, Any]]:
    """Load append-only chat events from one tutorial chat-log path."""

    if not chats_path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in chats_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        events.append(_require_mapping(payload, context=str(chats_path)))
    return events


def inspect_chat_log(
    *,
    chats_path: Path,
    send_message_id: str,
    reply_message_id: str,
    sender_address: str,
    receiver_address: str,
    initial_body_path: Path,
    reply_body_markdown: str,
) -> dict[str, Any]:
    """Inspect semantic chat-log evidence for one completed tutorial roundtrip."""

    initial_body = initial_body_path.read_text(encoding="utf-8")
    events = _load_chat_events(chats_path)
    send_event = next(
        (
            event
            for event in events
            if event.get("kind") == "send" and event.get("message_id") == send_message_id
        ),
        None,
    )
    reply_event = next(
        (
            event
            for event in events
            if event.get("kind") == "reply" and event.get("message_id") == reply_message_id
        ),
        None,
    )
    kinds = [str(event.get("kind", "")) for event in events]
    return {
        "path": str(chats_path.resolve()),
        "event_count": len(events),
        "kinds": kinds,
        "send_event_present": send_event is not None,
        "reply_event_present": reply_event is not None,
        "send_event_matches_input": isinstance(send_event, dict)
        and send_event.get("content") == initial_body,
        "reply_event_matches_mailbox_reply": isinstance(reply_event, dict)
        and reply_event.get("content") == reply_body_markdown,
        "send_event_from_matches_sender": isinstance(send_event, dict)
        and send_event.get("from") == sender_address,
        "send_event_to_matches_receiver": isinstance(send_event, dict)
        and send_event.get("to") == receiver_address,
        "reply_event_from_matches_receiver": isinstance(reply_event, dict)
        and reply_event.get("from") == receiver_address,
        "reply_event_to_matches_sender": isinstance(reply_event, dict)
        and reply_event.get("to") == sender_address,
        "reply_event_content_present": isinstance(reply_event, dict)
        and isinstance(reply_event.get("content"), str)
        and bool(str(reply_event.get("content")).strip()),
        "reply_event_thread_matches_send": isinstance(reply_event, dict)
        and reply_event.get("thread_id") == send_message_id,
        "reply_event_parent_matches_send": isinstance(reply_event, dict)
        and reply_event.get("in_reply_to") == send_message_id,
    }


def _autotest_inspect_commands(*, pack_dir: Path, demo_output_dir: Path) -> dict[str, str]:
    """Return stable inspect command strings for both tutorial participants."""

    run_demo = (pack_dir.resolve() / "run_demo.sh").resolve()
    demo_arg = shlex.quote(str(demo_output_dir.resolve()))
    run_demo_quoted = shlex.quote(str(run_demo))
    return {
        "sender": (f"{run_demo_quoted} inspect --demo-output-dir {demo_arg} --agent sender"),
        "receiver": (
            f"{run_demo_quoted} inspect --demo-output-dir {demo_arg} "
            "--agent receiver --json --with-output-text 400"
        ),
    }


def _read_optional_json_object(path: Path) -> dict[str, Any] | None:
    """Load one optional JSON object when the file exists."""

    if not path.is_file():
        return None
    return _require_mapping(_read_json(path), context=str(path))


def _phase_logs_payload(log_dir: Path | None) -> dict[str, str]:
    """Return one stable mapping of autotest phase-log paths."""

    if log_dir is None or not log_dir.is_dir():
        return {}
    payload: dict[str, str] = {}
    for path in sorted(log_dir.iterdir()):
        if path.is_file():
            payload[path.name] = str(path.resolve())
    return payload


def build_autotest_case_result(
    *,
    pack_dir: Path,
    demo_output_dir: Path,
    case_id: str,
    status: str,
    phase: str,
    error_message: str | None = None,
    timed_out: bool = False,
    log_dir: Path | None = None,
    preflight_result_path: Path | None = None,
    enforce_mailbox_persistence: bool = False,
) -> tuple[dict[str, Any], bool]:
    """Build one machine-readable autotest result snapshot from current demo artifacts."""

    if status not in {"success", "failure"}:
        raise ValueError(f"unsupported autotest result status: {status}")

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    inspect_commands = _autotest_inspect_commands(
        pack_dir=pack_dir,
        demo_output_dir=layout.demo_output_dir,
    )
    payload: dict[str, Any] = {
        "case_id": case_id,
        "status": status,
        "phase": phase,
        "ok": status == "success",
        "timed_out": timed_out,
        "error_message": error_message,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_output_dir": str(layout.demo_output_dir),
        "control_dir": str(layout.control_dir),
        "inspect_commands": inspect_commands,
        "phase_logs": _phase_logs_payload(log_dir),
    }
    if preflight_result_path is not None:
        payload["preflight_result_path"] = str(preflight_result_path.resolve())
        payload["preflight_result"] = _read_optional_json_object(preflight_result_path)

    state = _read_optional_json_object(layout.state_path)
    if state is not None:
        payload["state_path"] = str(layout.state_path.resolve())
        payload["steps"] = _require_mapping(state.get("steps"), context="steps")
        payload["sender"] = {
            "mailbox_address": _require_non_empty_string(
                _require_mapping(state.get("sender"), context="sender").get("mailbox_address"),
                context="sender.mailbox_address",
            ),
            "inspect_command": inspect_commands["sender"],
        }
        payload["receiver"] = {
            "mailbox_address": _require_non_empty_string(
                _require_mapping(state.get("receiver"), context="receiver").get("mailbox_address"),
                context="receiver.mailbox_address",
            ),
            "inspect_command": inspect_commands["receiver"],
        }

    verify_result = _read_optional_json_object(layout.verify_result_path)
    stop_result = _read_optional_json_object(layout.stop_result_path)
    if verify_result is not None:
        payload["verify_result_path"] = str(layout.verify_result_path.resolve())
        payload["verify_result"] = verify_result
    if stop_result is not None:
        payload["stop_result_path"] = str(layout.stop_result_path.resolve())
        payload["stop_result"] = stop_result

    mailbox_evidence: dict[str, Any] | None = None
    mailbox_errors: list[str] = []
    if state is not None:
        try:
            sender_state = _require_mapping(state.get("sender"), context="sender")
            receiver_state = _require_mapping(state.get("receiver"), context="receiver")
            message_state = _require_mapping(state.get("message"), context="message")
            send_message_id = message_state.get("send_message_id")
            reply_message_id = message_state.get("reply_message_id")
            if (
                isinstance(send_message_id, str)
                and send_message_id.strip()
                and isinstance(reply_message_id, str)
                and reply_message_id.strip()
            ):
                mailbox_evidence = inspect_roundtrip_mailbox(
                    mailbox_root=layout.mailbox_root,
                    sender_address=_require_non_empty_string(
                        sender_state.get("mailbox_address"),
                        context="sender.mailbox_address",
                    ),
                    receiver_address=_require_non_empty_string(
                        receiver_state.get("mailbox_address"),
                        context="receiver.mailbox_address",
                    ),
                    send_message_id=send_message_id,
                    reply_message_id=reply_message_id,
                    initial_body_path=Path(
                        _require_non_empty_string(
                            message_state.get("initial_body_file"),
                            context="message.initial_body_file",
                        )
                    ),
                )
                mailbox_evidence["sender_mailbox_dir_exists"] = Path(
                    mailbox_evidence["sender_mailbox_dir"]
                ).is_dir()
                mailbox_evidence["receiver_mailbox_dir_exists"] = Path(
                    mailbox_evidence["receiver_mailbox_dir"]
                ).is_dir()
                mailbox_evidence["send_message_readable"] = Path(
                    mailbox_evidence["send_message_path"]
                ).is_file() and os.access(mailbox_evidence["send_message_path"], os.R_OK)
                mailbox_evidence["reply_message_readable"] = Path(
                    mailbox_evidence["reply_message_path"]
                ).is_file() and os.access(mailbox_evidence["reply_message_path"], os.R_OK)
                chat_evidence = inspect_chat_log(
                    chats_path=layout.chats_path,
                    send_message_id=send_message_id,
                    reply_message_id=reply_message_id,
                    sender_address=_require_non_empty_string(
                        sender_state.get("mailbox_address"),
                        context="sender.mailbox_address",
                    ),
                    receiver_address=_require_non_empty_string(
                        receiver_state.get("mailbox_address"),
                        context="receiver.mailbox_address",
                    ),
                    initial_body_path=Path(
                        _require_non_empty_string(
                            message_state.get("initial_body_file"),
                            context="message.initial_body_file",
                        )
                    ),
                    reply_body_markdown=_require_non_empty_string(
                        mailbox_evidence.get("reply_body_markdown"),
                        context="mailbox.reply_body_markdown",
                    ),
                )
                mailbox_evidence["chat_log"] = chat_evidence
        except Exception as exc:
            mailbox_errors.append(str(exc))

    payload["mailbox_evidence"] = mailbox_evidence
    if mailbox_errors:
        payload["mailbox_errors"] = mailbox_errors

    if status == "success":
        if mailbox_evidence is None:
            payload["ok"] = False
            payload.setdefault("validation_errors", []).append(
                "successful autotest result is missing roundtrip mailbox evidence"
            )
        if enforce_mailbox_persistence and mailbox_evidence is not None:
            persistence_checks = [
                bool(mailbox_evidence["sender_mailbox_dir_exists"]),
                bool(mailbox_evidence["receiver_mailbox_dir_exists"]),
                bool(mailbox_evidence["send_message_readable"]),
                bool(mailbox_evidence["reply_message_readable"]),
            ]
            payload["mailbox_persistence_ok"] = all(persistence_checks)
            if not all(persistence_checks):
                payload["ok"] = False
                payload.setdefault("validation_errors", []).append(
                    "post-stop mailbox evidence is missing or unreadable"
                )
        elif enforce_mailbox_persistence:
            payload["mailbox_persistence_ok"] = False
    else:
        payload["mailbox_persistence_ok"] = (
            bool(mailbox_evidence)
            and bool(mailbox_evidence.get("sender_mailbox_dir_exists"))
            and bool(mailbox_evidence.get("receiver_mailbox_dir_exists"))
            and bool(mailbox_evidence.get("send_message_readable"))
            and bool(mailbox_evidence.get("reply_message_readable"))
        )

    return payload, bool(payload["ok"])


def _artifact_path(layout: DemoLayout, label: str) -> Path:
    """Return one control-artifact path for a tracked command label."""

    return layout.control_dir / _ARTIFACT_FILENAMES[label]


def _artifact_paths(layout: DemoLayout) -> dict[str, Path]:
    """Return the expected control-artifact paths for one demo layout."""

    return {label: _artifact_path(layout, label) for label in _COMMAND_FLOW}


def _report_artifact_paths(layout: DemoLayout) -> dict[str, Path]:
    """Return the report-building artifact set for one demo layout."""

    return {label: _artifact_path(layout, label) for label in _REPORT_FLOW}


def _load_artifacts(layout: DemoLayout) -> dict[str, dict[str, Any]]:
    """Load all required JSON control artifacts for one demo layout."""

    artifacts: dict[str, dict[str, Any]] = {}
    for label, path in _report_artifact_paths(layout).items():
        artifacts[label] = _require_mapping(_read_json(path), context=str(path))
    return artifacts


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


def _git_output(
    *,
    args: list[str],
    cwd: Path,
    run_git: GitRunner,
    env: dict[str, str] | None = None,
) -> str | None:
    """Run one git command and return stripped stdout on success."""

    result = run_git(args, cwd, env)
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


def _terminal_log_path_for_cao_home(*, cao_home_dir: Path, terminal_id: str) -> str:
    """Return the CAO terminal log path for one terminal id."""

    return str(
        (
            cao_home_dir.expanduser().resolve()
            / DEFAULT_TERMINAL_LOG_RELATIVE_DIR
            / f"{terminal_id}.log"
        ).resolve()
    )


def _write_managed_project_metadata(*, project_workdir: Path, fixture_dir: Path) -> None:
    """Write one marker payload for a managed copied dummy-project workdir."""

    _write_json(
        _managed_project_metadata_path(project_workdir),
        {
            "schema_version": 1,
            "managed_by": "mailbox-roundtrip-tutorial-pack",
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
    recovery_attempted = False

    if bool(start_payload.get("reused_existing_process")) and not ownership_verified:
        recovery_attempted = True
        stop_payload = _launcher_json(
            repo_root=repo_root,
            args=["stop", "--config", str(config_path)],
            accepted_exit_codes={0, 2},
            run_launcher=run_launcher,
        )
        status_payload = _launcher_json(
            repo_root=repo_root,
            args=["status", "--config", str(config_path)],
            accepted_exit_codes={0, 2},
            run_launcher=run_launcher,
        )
        if bool(stop_payload.get("stopped")) and not bool(status_payload.get("healthy")):
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
        if not ownership_verified:
            raise RuntimeError(
                "healthy CAO server reuse could not be verified through the demo-local launcher "
                "context; stop the existing service or use an explicit external CAO flow with "
                "CAO_PROFILE_STORE set"
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
        "recovery_attempted": recovery_attempted,
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
    """Resolve the supported CAO execution context for one demo run."""

    normalized_base_url = _normalize_cao_base_url(cao_base_url)
    if supports_loopback_cao_launcher_management(normalized_base_url):
        payload = start_demo_cao(
            repo_root=repo_root,
            demo_output_dir=demo_output_dir,
            cao_base_url=normalized_base_url,
        )
        if cao_profile_store is not None and cao_profile_store.strip():
            requested_profile_store = str(Path(cao_profile_store).expanduser().resolve())
            actual_profile_store = _require_non_empty_string(
                payload.get("profile_store"),
                context="cao.profile_store",
            )
            if requested_profile_store != actual_profile_store:
                raise ValueError(
                    "CAO_PROFILE_STORE override does not match the demo-managed CAO profile store"
                )
        return payload
    if cao_profile_store is None or not cao_profile_store.strip():
        raise DemoSkipError(
            "external CAO requires explicit CAO_PROFILE_STORE=/abs/path/.../agent-store"
        )
    raise DemoSkipError(
        "external CAO is not part of the default verified tutorial contract; use the "
        "manual realm_controller walkthrough with explicit CAO_PROFILE_STORE"
    )


def _stderr_path_for(path: Path) -> Path:
    """Return the stderr artifact path paired with one stdout artifact path."""

    if path.suffix:
        return path.with_suffix(".err")
    return Path(f"{path}.err")


def _load_state(state_path: Path) -> dict[str, Any]:
    """Load one persisted demo state payload."""

    return _require_mapping(_read_json(state_path), context=str(state_path))


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    """Persist one demo state payload."""

    _write_json(path, payload)


def _copy_inputs(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Refresh the demo-local copied input files."""

    source_dir = pack_dir / "inputs"
    if not source_dir.is_dir():
        raise ValueError(f"missing tracked input directory: {source_dir}")
    if layout.inputs_dir.exists():
        shutil.rmtree(layout.inputs_dir)
    shutil.copytree(source_dir, layout.inputs_dir)


def _command_environment(*, jobs_dir: Path | None) -> dict[str, str]:
    """Return subprocess environment overrides for demo commands."""

    env = dict(os.environ)
    if jobs_dir is not None:
        env["AGENTSYS_LOCAL_JOBS_DIR"] = str(jobs_dir.resolve())
    else:
        env.pop("AGENTSYS_LOCAL_JOBS_DIR", None)
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
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"command returned malformed JSON: {exc}") from exc
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


def _agent_def_dir(*, parameters: DemoParameters, repo_root: Path) -> Path:
    """Resolve the active agent-definition directory for one demo run."""

    return resolve_repo_relative_path(
        os.environ.get("AGENT_DEF_DIR"),
        repo_root=repo_root,
        default_relative=parameters.agent_def_dir,
    )


def _participant_state(participant: DemoParticipant) -> dict[str, Any]:
    """Build the mutable per-participant state payload."""

    return {
        "blueprint": participant.blueprint,
        "requested_identity": participant.agent_identity,
        "mailbox_principal_id": participant.mailbox_principal_id,
        "mailbox_address": participant.mailbox_address,
        "build": None,
        "start": None,
        "inspect": None,
        "started_current_run": False,
        "stopped": False,
    }


def _initial_state(
    *,
    parameters: DemoParameters,
    parameters_path: Path,
    layout: DemoLayout,
    agent_def_dir: Path,
    project_fixture: Path,
    jobs_dir: Path | None,
    cao_parsing_mode: str | None,
) -> dict[str, Any]:
    """Build the initial persisted state payload for one demo root."""

    initial_body_path = layout.inputs_dir / Path(parameters.message.initial_body_file).name
    reply_instructions_path = (
        layout.inputs_dir / Path(parameters.message.reply_instructions_file).name
    )
    return {
        "schema_version": 3,
        "demo_id": parameters.demo_id,
        "parameters_path": str(parameters_path.resolve()),
        "demo_output_dir": str(layout.demo_output_dir),
        "control_dir": str(layout.control_dir),
        "project_workdir": str(layout.project_workdir),
        "project_fixture": str(project_fixture.resolve()),
        "runtime_root": str(layout.runtime_root),
        "mailbox_root": str(
            render_mailbox_root(parameters, demo_output_dir=layout.demo_output_dir)
        ),
        "chat_log_path": str(layout.chats_path),
        "agent_def_dir": str(agent_def_dir.resolve()),
        "jobs_dir": None if jobs_dir is None else str(jobs_dir.resolve()),
        "cao_parsing_mode": cao_parsing_mode,
        "cao": {},
        "sender": _participant_state(parameters.sender),
        "receiver": _participant_state(parameters.receiver),
        "message": {
            "subject": parameters.message.subject,
            "initial_body_file": str(initial_body_path.resolve()),
            "reply_instructions_file": str(reply_instructions_path.resolve()),
            "send_message_id": None,
            "reply_message_id": None,
        },
        "steps": {
            "start_complete": False,
            "roundtrip_complete": False,
            "verify_complete": False,
            "stop_complete": False,
        },
    }


def _state_jobs_dir(state: dict[str, Any]) -> Path | None:
    """Return the persisted jobs-root override when present."""

    raw_jobs_dir = state.get("jobs_dir")
    if raw_jobs_dir is None:
        return None
    return Path(_require_non_empty_string(raw_jobs_dir, context="jobs_dir")).resolve()


def _state_cao_parsing_mode(state: dict[str, Any]) -> str | None:
    """Return the persisted CAO parsing mode override when present."""

    raw_mode = state.get("cao_parsing_mode")
    if raw_mode is None:
        return None
    return _require_non_empty_string(raw_mode, context="cao_parsing_mode")


def _resolve_demo_cao_parsing_mode(
    *,
    requested_mode: str | None,
    persisted_mode: str | None,
) -> str:
    """Resolve the effective demo CAO parsing mode for tutorial-pack workflow steps."""

    if requested_mode is not None:
        normalized_requested = requested_mode.strip()
        if normalized_requested == "shadow_only":
            return normalized_requested
        raise ValueError(
            f"mailbox tutorial pack only supports `shadow_only`; received {normalized_requested!r}"
        )

    if persisted_mode is not None:
        normalized_persisted = persisted_mode.strip()
        if normalized_persisted == "shadow_only":
            return normalized_persisted
        raise ValueError(
            "mailbox tutorial pack found persisted demo state with unsupported "
            f"`cao_parsing_mode={normalized_persisted}`; recreate the demo output root "
            "so the pack can restart in `shadow_only`"
        )
    return _DEFAULT_AUTOMATION_CAO_PARSING_MODE


def _participant_identity(participant_state: dict[str, Any], *, context: str) -> str:
    """Resolve the control identity for one participant from persisted state."""

    start_payload = participant_state.get("start")
    if isinstance(start_payload, dict):
        identity = start_payload.get("agent_identity")
        if isinstance(identity, str) and identity.strip():
            return identity
    return _require_non_empty_string(
        participant_state.get("requested_identity"),
        context=f"{context}.requested_identity",
    )


def _fallback_participant_inspect_state(
    *,
    participant_state: dict[str, Any],
    state: dict[str, Any],
    context: str,
) -> dict[str, Any]:
    """Build inspect metadata from persisted start/session artifacts when needed."""

    start_payload = _require_mapping(participant_state.get("start"), context=f"{context}.start")
    session_manifest_path = Path(
        _require_non_empty_string(
            start_payload.get("session_manifest"),
            context=f"{context}.start.session_manifest",
        )
    ).resolve()
    manifest_payload = _require_mapping(
        _read_json(session_manifest_path),
        context=str(session_manifest_path),
    )
    cao_payload = _require_mapping(
        manifest_payload.get("cao"),
        context=f"{session_manifest_path}.cao",
    )
    cao_state = _require_state_mapping(state, "cao")
    cao_home_dir = Path(
        _require_non_empty_string(cao_state.get("home_dir"), context="cao.home_dir")
    ).resolve()
    terminal_id = _require_non_empty_string(
        cao_payload.get("terminal_id"),
        context=f"{session_manifest_path}.cao.terminal_id",
    )
    session_name = _require_non_empty_string(
        cao_payload.get("session_name"),
        context=f"{session_manifest_path}.cao.session_name",
    )
    return {
        "agent_identity": _participant_identity(participant_state, context=context),
        "tool": _require_non_empty_string(start_payload.get("tool"), context=f"{context}.tool"),
        "session_name": session_name,
        "tmux_target": session_name,
        "terminal_id": terminal_id,
        "terminal_log_path": _terminal_log_path_for_cao_home(
            cao_home_dir=cao_home_dir,
            terminal_id=terminal_id,
        ),
        "session_manifest": str(session_manifest_path),
        "updated_at": datetime.fromtimestamp(
            session_manifest_path.stat().st_mtime,
            tz=UTC,
        ).isoformat(timespec="seconds"),
    }


def _resolved_participant_inspect_state(
    *,
    participant_state: dict[str, Any],
    state: dict[str, Any],
    context: str,
) -> dict[str, Any]:
    """Resolve one participant inspect mapping from persisted state."""

    inspect_state = participant_state.get("inspect")
    if isinstance(inspect_state, dict):
        return inspect_state
    return _fallback_participant_inspect_state(
        participant_state=participant_state,
        state=state,
        context=context,
    )


def _record_participant_inspect_state(
    *,
    participant_state: dict[str, Any],
    start_payload: dict[str, Any],
    cao_context: dict[str, Any],
) -> None:
    """Persist inspect metadata for one started participant."""

    session_manifest_path = Path(
        _require_non_empty_string(
            start_payload.get("session_manifest"),
            context="start.session_manifest",
        )
    ).resolve()
    manifest_payload = _require_mapping(
        _read_json(session_manifest_path),
        context=str(session_manifest_path),
    )
    raw_cao_payload = manifest_payload.get("cao")
    terminal_id: str | None = None
    terminal_log_path: str | None = None
    session_name = _require_non_empty_string(
        start_payload.get("tmux_session_name"),
        context="start.tmux_session_name",
    )
    if isinstance(raw_cao_payload, dict):
        cao_payload = _require_mapping(raw_cao_payload, context=f"{session_manifest_path}.cao")
        terminal_id = _require_non_empty_string(
            cao_payload.get("terminal_id"),
            context=f"{session_manifest_path}.cao.terminal_id",
        )
        cao_home_dir = Path(
            _require_non_empty_string(cao_context.get("home_dir"), context="cao.home_dir")
        ).resolve()
        session_name = _require_non_empty_string(
            cao_payload.get("session_name"),
            context=f"{session_manifest_path}.cao.session_name",
        )
        terminal_log_path = _terminal_log_path_for_cao_home(
            cao_home_dir=cao_home_dir,
            terminal_id=terminal_id,
        )
    participant_state["inspect"] = {
        "agent_identity": _require_non_empty_string(
            start_payload.get("agent_identity"),
            context="start.agent_identity",
        ),
        "tool": _require_non_empty_string(start_payload.get("tool"), context="start.tool"),
        "session_name": session_name,
        "tmux_target": session_name,
        "terminal_id": terminal_id,
        "terminal_log_path": terminal_log_path,
        "session_manifest": str(session_manifest_path),
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def _freshen_demo_output(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Reset one demo root before reprovisioning a fresh dummy-project copy."""

    layout.demo_output_dir.mkdir(parents=True, exist_ok=True)
    for path in (layout.runtime_root, layout.mailbox_root, layout.cao_dir, layout.control_dir):
        if path.exists():
            shutil.rmtree(path)
    if layout.chats_path.exists():
        layout.chats_path.unlink()

    _copy_inputs(pack_dir=pack_dir, layout=layout)


def _require_state_mapping(state: dict[str, Any], key: str) -> dict[str, Any]:
    """Return one required mapping field from a persisted state payload."""

    return _require_mapping(state.get(key), context=key)


def _maybe_inject_fault(trigger: str) -> None:
    """Raise a synthetic failure or interrupt for a named test trigger."""

    raw_fault = os.environ.get("MAILBOX_ROUNDTRIP_DEMO_FAULT")
    if raw_fault is None or not raw_fault.strip():
        return
    normalized_fault = raw_fault.strip().lower().replace("_", "-")
    if normalized_fault == f"fail-after-{trigger}":
        raise RuntimeError(f"synthetic mailbox demo fault after {trigger}")
    if normalized_fault == f"interrupt-after-{trigger}":
        raise KeyboardInterrupt(f"synthetic mailbox demo interrupt after {trigger}")


def _compose_reply_body(
    *,
    reply_instructions_path: Path,
    reply_parent_message_id: str,
    sender_address: str,
    receiver_address: str,
) -> str:
    """Build one deterministic tutorial reply body from the tracked authoring instructions."""

    instructions = reply_instructions_path.read_text(encoding="utf-8").strip()
    if not instructions:
        raise ValueError(f"reply instructions are empty: {reply_instructions_path}")

    return "\n".join(
        [
            "# Mailbox Tutorial: Authored Reply",
            "",
            (
                "Confirmed. The mailbox roundtrip is active and this reply stays in the same "
                "thread as the original send."
            ),
            "",
            f"- Parent `message_id`: `{reply_parent_message_id}`.",
            f"- Sender mailbox: `{sender_address}`.",
            f"- Receiver mailbox: `{receiver_address}`.",
            "- The original sender can now run `mail check`.",
            "",
            "Reply authored from the tracked tutorial instructions for this pack run.",
        ]
    )


def start_demo(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
    jobs_dir: Path | None,
    cao_parsing_mode: str | None = None,
) -> dict[str, Any]:
    """Provision the demo root and start both mailbox participants."""

    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    resolved_cao_parsing_mode = _resolve_demo_cao_parsing_mode(
        requested_mode=cao_parsing_mode,
        persisted_mode=None,
    )
    project_fixture = _project_fixture_dir(parameters=parameters, repo_root=repo_root)
    allow_project_reprovision = False

    if layout.state_path.exists():
        existing_state = _load_state(layout.state_path)
        existing_steps = _require_state_mapping(existing_state, "steps")
        if not bool(existing_steps.get("stop_complete")):
            raise ValueError(
                "demo state already exists for this output directory and has not been stopped; "
                "run `run_demo.sh stop` first"
            )
        allow_project_reprovision = True

    if layout.project_workdir.exists() and not allow_project_reprovision:
        raise ValueError(
            "demo project directory already exists before a stopped demo state was found: "
            f"{layout.project_workdir.resolve()}"
        )

    _freshen_demo_output(pack_dir=pack_dir, layout=layout)
    ensure_project_workdir_from_fixture(
        repo_root=repo_root,
        project_fixture=project_fixture,
        project_workdir=layout.project_workdir,
        allow_reprovision=allow_project_reprovision,
    )
    layout.runtime_root.mkdir(parents=True, exist_ok=True)

    agent_def_dir = _agent_def_dir(parameters=parameters, repo_root=repo_root)
    if not agent_def_dir.is_dir():
        raise ValueError(f"agent definition directory not found: {agent_def_dir}")

    state = _initial_state(
        parameters=parameters,
        parameters_path=parameters_path,
        layout=layout,
        agent_def_dir=agent_def_dir,
        project_fixture=project_fixture,
        jobs_dir=jobs_dir,
        cao_parsing_mode=resolved_cao_parsing_mode,
    )
    _write_state(layout.state_path, state)

    try:
        cao_context = _resolve_cao_context(
            repo_root=repo_root,
            demo_output_dir=layout.demo_output_dir,
            cao_base_url=os.environ.get("CAO_BASE_URL", parameters.cao_base_url),
            cao_profile_store=os.environ.get("CAO_PROFILE_STORE"),
        )
        _write_json(layout.cao_start_path, cao_context)
        state["cao"] = {**cao_context, "stopped": False}
        _write_state(layout.state_path, state)

        env = _command_environment(jobs_dir=jobs_dir)
        sender_state = _require_state_mapping(state, "sender")
        sender_launch = resolve_demo_preset_launch(
            agent_def_dir=agent_def_dir,
            preset_path=resolve_repo_relative_path(
                _require_non_empty_string(
                    sender_state.get("blueprint"), context="sender.blueprint"
                ),
                repo_root=repo_root,
            ),
        )
        sender_build = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "build-brain",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(layout.runtime_root),
                "--preset",
                str(sender_launch.preset_path),
            ],
            stdout_path=_artifact_path(layout, "sender_build"),
            env=env,
        )
        sender_state["build"] = sender_build
        _write_state(layout.state_path, state)

        receiver_state = _require_state_mapping(state, "receiver")
        receiver_launch = resolve_demo_preset_launch(
            agent_def_dir=agent_def_dir,
            preset_path=resolve_repo_relative_path(
                _require_non_empty_string(
                    receiver_state.get("blueprint"),
                    context="receiver.blueprint",
                ),
                repo_root=repo_root,
            ),
        )
        receiver_build = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "build-brain",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(layout.runtime_root),
                "--preset",
                str(receiver_launch.preset_path),
            ],
            stdout_path=_artifact_path(layout, "receiver_build"),
            env=env,
        )
        receiver_state["build"] = receiver_build
        _write_state(layout.state_path, state)

        sender_start = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "start-session",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(layout.runtime_root),
                "--brain-manifest",
                _require_non_empty_string(
                    sender_build.get("manifest_path"),
                    context="sender_build.manifest_path",
                ),
                "--role",
                sender_launch.role_name,
                "--backend",
                normalize_demo_launch_backend(parameters.backend),
                "--cao-base-url",
                _require_non_empty_string(cao_context.get("base_url"), context="cao.base_url"),
                "--cao-profile-store",
                _require_non_empty_string(
                    cao_context.get("profile_store"),
                    context="cao.profile_store",
                ),
                "--workdir",
                str(layout.project_workdir),
                "--agent-identity",
                _require_non_empty_string(
                    sender_state.get("requested_identity"),
                    context="sender.requested_identity",
                ),
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(layout.mailbox_root),
                "--mailbox-principal-id",
                _require_non_empty_string(
                    sender_state.get("mailbox_principal_id"),
                    context="sender.mailbox_principal_id",
                ),
                "--mailbox-address",
                _require_non_empty_string(
                    sender_state.get("mailbox_address"),
                    context="sender.mailbox_address",
                ),
                "--cao-parsing-mode",
                resolved_cao_parsing_mode,
            ],
            stdout_path=_artifact_path(layout, "sender_start"),
            env=env,
        )
        sender_state["start"] = sender_start
        _record_participant_inspect_state(
            participant_state=sender_state,
            start_payload=sender_start,
            cao_context=cao_context,
        )
        sender_state["started_current_run"] = True
        sender_state["stopped"] = False
        _write_state(layout.state_path, state)
        _maybe_inject_fault("sender-start")

        receiver_start = _run_realm_controller_json(
            repo_root=repo_root,
            args=[
                "start-session",
                "--agent-def-dir",
                str(agent_def_dir),
                "--runtime-root",
                str(layout.runtime_root),
                "--brain-manifest",
                _require_non_empty_string(
                    receiver_build.get("manifest_path"),
                    context="receiver_build.manifest_path",
                ),
                "--role",
                receiver_launch.role_name,
                "--backend",
                normalize_demo_launch_backend(parameters.backend),
                "--cao-base-url",
                _require_non_empty_string(cao_context.get("base_url"), context="cao.base_url"),
                "--cao-profile-store",
                _require_non_empty_string(
                    cao_context.get("profile_store"),
                    context="cao.profile_store",
                ),
                "--workdir",
                str(layout.project_workdir),
                "--agent-identity",
                _require_non_empty_string(
                    receiver_state.get("requested_identity"),
                    context="receiver.requested_identity",
                ),
                "--mailbox-transport",
                "filesystem",
                "--mailbox-root",
                str(layout.mailbox_root),
                "--mailbox-principal-id",
                _require_non_empty_string(
                    receiver_state.get("mailbox_principal_id"),
                    context="receiver.mailbox_principal_id",
                ),
                "--mailbox-address",
                _require_non_empty_string(
                    receiver_state.get("mailbox_address"),
                    context="receiver.mailbox_address",
                ),
                "--cao-parsing-mode",
                resolved_cao_parsing_mode,
            ],
            stdout_path=_artifact_path(layout, "receiver_start"),
            env=env,
        )
        receiver_state["start"] = receiver_start
        _record_participant_inspect_state(
            participant_state=receiver_state,
            start_payload=receiver_start,
            cao_context=cao_context,
        )
        receiver_state["started_current_run"] = True
        receiver_state["stopped"] = False
        _write_state(layout.state_path, state)
        _maybe_inject_fault("receiver-start")
    except KeyboardInterrupt:
        _write_state(layout.state_path, state)
        try:
            stop_demo(
                repo_root=repo_root,
                demo_output_dir=layout.demo_output_dir,
                cleanup=True,
                reason="start interrupted",
                cao_parsing_mode=resolved_cao_parsing_mode,
            )
        except Exception:
            pass
        raise
    except Exception:
        _write_state(layout.state_path, state)
        try:
            stop_demo(
                repo_root=repo_root,
                demo_output_dir=layout.demo_output_dir,
                cleanup=True,
                reason="start failed",
                cao_parsing_mode=resolved_cao_parsing_mode,
            )
        except Exception:
            pass
        raise

    steps = _require_state_mapping(state, "steps")
    steps["start_complete"] = True
    _write_state(layout.state_path, state)
    return state


def roundtrip_demo(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    cao_parsing_mode: str | None = None,
) -> dict[str, Any]:
    """Run the mailbox send/check/reply/check phase against an existing demo root."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    steps = _require_state_mapping(state, "steps")
    if not bool(steps.get("start_complete")):
        raise ValueError("demo start phase has not completed for this output directory")

    message_state = _require_state_mapping(state, "message")
    initial_body_file = Path(
        _require_non_empty_string(message_state.get("initial_body_file"), context="message.initial")
    )
    reply_instructions_file = Path(
        _require_non_empty_string(
            message_state.get("reply_instructions_file"), context="message.reply_instructions"
        )
    )
    if not initial_body_file.is_file() or not reply_instructions_file.is_file():
        raise ValueError("copied message inputs are missing from the demo output directory")

    resolved_cao_parsing_mode = _resolve_demo_cao_parsing_mode(
        requested_mode=cao_parsing_mode,
        persisted_mode=_state_cao_parsing_mode(state),
    )
    env = _command_environment(jobs_dir=_state_jobs_dir(state))
    sender_state = _require_state_mapping(state, "sender")
    receiver_state = _require_state_mapping(state, "receiver")
    agent_def_dir = Path(
        _require_non_empty_string(state.get("agent_def_dir"), context="agent_def_dir")
    ).resolve()

    mail_send = _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "mail",
            "send",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            _participant_identity(sender_state, context="sender"),
            *(
                ["--cao-parsing-mode", resolved_cao_parsing_mode]
                if resolved_cao_parsing_mode is not None
                else []
            ),
            "--to",
            _require_non_empty_string(
                receiver_state.get("mailbox_address"),
                context="receiver.mailbox_address",
            ),
            "--subject",
            _require_non_empty_string(message_state.get("subject"), context="message.subject"),
            "--body-file",
            str(initial_body_file),
        ],
        stdout_path=_artifact_path(layout, "mail_send"),
        env=env,
    )
    message_state["send_message_id"] = _require_non_empty_string(
        mail_send.get("message_id"),
        context="mail_send.message_id",
    )
    send_message_id = _require_non_empty_string(
        message_state.get("send_message_id"), context="message.send_message_id"
    )
    _append_chat_event(
        layout,
        kind="send",
        sender=_require_non_empty_string(
            sender_state.get("mailbox_address"), context="sender.address"
        ),
        recipient=_require_non_empty_string(
            receiver_state.get("mailbox_address"), context="receiver.address"
        ),
        content=initial_body_file.read_text(encoding="utf-8"),
        message_id=send_message_id,
        thread_id=_require_non_empty_string(
            mail_send.get("thread_id"), context="mail_send.thread_id"
        ),
        subject=_require_non_empty_string(message_state.get("subject"), context="message.subject"),
    )
    _write_state(layout.state_path, state)
    _maybe_inject_fault("mail-send")

    _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "mail",
            "check",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            _participant_identity(receiver_state, context="receiver"),
            *(
                ["--cao-parsing-mode", resolved_cao_parsing_mode]
                if resolved_cao_parsing_mode is not None
                else []
            ),
            "--unread-only",
            "--limit",
            "10",
        ],
        stdout_path=_artifact_path(layout, "receiver_check"),
        env=env,
    )
    _maybe_inject_fault("receiver-check")

    reply_body_content = _compose_reply_body(
        reply_instructions_path=reply_instructions_file,
        reply_parent_message_id=send_message_id,
        sender_address=_require_non_empty_string(
            sender_state.get("mailbox_address"), context="sender.address"
        ),
        receiver_address=_require_non_empty_string(
            receiver_state.get("mailbox_address"), context="receiver.address"
        ),
    )

    mail_reply = _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "mail",
            "reply",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            _participant_identity(receiver_state, context="receiver"),
            *(
                ["--cao-parsing-mode", resolved_cao_parsing_mode]
                if resolved_cao_parsing_mode is not None
                else []
            ),
            "--message-id",
            _require_non_empty_string(
                message_state.get("send_message_id"),
                context="message.send_message_id",
            ),
            "--body-content",
            reply_body_content,
        ],
        stdout_path=_artifact_path(layout, "mail_reply"),
        env=env,
    )
    message_state["reply_message_id"] = _require_non_empty_string(
        mail_reply.get("message_id"),
        context="mail_reply.message_id",
    )
    _append_chat_event(
        layout,
        kind="reply",
        sender=_require_non_empty_string(
            receiver_state.get("mailbox_address"), context="receiver.address"
        ),
        recipient=_require_non_empty_string(
            sender_state.get("mailbox_address"), context="sender.address"
        ),
        content=reply_body_content,
        message_id=_require_non_empty_string(
            message_state.get("reply_message_id"), context="message.reply_message_id"
        ),
        thread_id=_require_non_empty_string(
            mail_reply.get("thread_id"), context="mail_reply.thread_id"
        ),
        in_reply_to=send_message_id,
        subject=_require_non_empty_string(message_state.get("subject"), context="message.subject"),
    )
    _write_state(layout.state_path, state)
    _maybe_inject_fault("mail-reply")

    _run_realm_controller_json(
        repo_root=repo_root,
        args=[
            "mail",
            "check",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            _participant_identity(sender_state, context="sender"),
            *(
                ["--cao-parsing-mode", resolved_cao_parsing_mode]
                if resolved_cao_parsing_mode is not None
                else []
            ),
            "--unread-only",
            "--limit",
            "10",
        ],
        stdout_path=_artifact_path(layout, "sender_check"),
        env=env,
    )
    _maybe_inject_fault("sender-check")

    steps["roundtrip_complete"] = True
    _write_state(layout.state_path, state)
    return {
        "send_message_id": message_state["send_message_id"],
        "reply_message_id": message_state["reply_message_id"],
    }


def inspect_demo_agent(
    *,
    demo_output_dir: Path,
    agent: str,
    output_text_tail_chars: int | None = None,
) -> dict[str, Any]:
    """Build one inspect payload for the selected tutorial participant."""

    if agent not in {"sender", "receiver"}:
        raise ValueError("inspect requires `--agent sender` or `--agent receiver`")
    if output_text_tail_chars is not None and output_text_tail_chars <= 0:
        raise ValueError("--with-output-text must be a positive integer")

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    participant_state = _require_state_mapping(state, agent)
    inspect_state = _resolved_participant_inspect_state(
        participant_state=participant_state,
        state=state,
        context=agent,
    )
    cao_state = _require_state_mapping(state, "cao")
    base_url = _require_non_empty_string(cao_state.get("base_url"), context="cao.base_url")
    terminal_id = _require_non_empty_string(
        inspect_state.get("terminal_id"),
        context=f"{agent}.inspect.terminal_id",
    )
    tmux_target = _require_non_empty_string(
        inspect_state.get("tmux_target"),
        context=f"{agent}.inspect.tmux_target",
    )
    terminal_log_path = _require_non_empty_string(
        inspect_state.get("terminal_log_path"),
        context=f"{agent}.inspect.terminal_log_path",
    )
    client = CaoRestClient(base_url, timeout_seconds=DEFAULT_LIVE_CAO_TIMEOUT_SECONDS)
    payload: dict[str, Any] = {
        "agent": agent,
        "agent_identity": _require_non_empty_string(
            inspect_state.get("agent_identity"),
            context=f"{agent}.inspect.agent_identity",
        ),
        "session_name": _require_non_empty_string(
            inspect_state.get("session_name"),
            context=f"{agent}.inspect.session_name",
        ),
        "tool": _require_non_empty_string(
            inspect_state.get("tool"),
            context=f"{agent}.inspect.tool",
        ),
        "tool_state": _best_effort_tool_state(terminal_id=terminal_id, client=client),
        "tmux_target": tmux_target,
        "tmux_attach_command": f"tmux attach -t {tmux_target}",
        "terminal_id": terminal_id,
        "terminal_log_path": terminal_log_path,
        "terminal_log_tail_command": f"tail -f {terminal_log_path}",
        "session_manifest": _require_non_empty_string(
            inspect_state.get("session_manifest"),
            context=f"{agent}.inspect.session_manifest",
        ),
        "project_workdir": _require_non_empty_string(
            state.get("project_workdir"),
            context="project_workdir",
        ),
        "runtime_root": _require_non_empty_string(
            state.get("runtime_root"),
            context="runtime_root",
        ),
        "updated_at": _require_non_empty_string(
            inspect_state.get("updated_at"),
            context=f"{agent}.inspect.updated_at",
        ),
    }
    if output_text_tail_chars is not None:
        output_text_tail = _best_effort_output_text_tail(
            tool=payload["tool"],
            terminal_id=terminal_id,
            output_text_tail_chars=output_text_tail_chars,
            client=client,
        )
        payload["output_text_tail_chars_requested"] = output_text_tail_chars
        payload["output_text_tail"] = output_text_tail.output_text_tail
        if output_text_tail.note is not None:
            payload["output_text_tail_note"] = output_text_tail.note
    return payload


def _render_human_inspect_output(*, payload: dict[str, Any]) -> str:
    """Render the tutorial-pack inspect payload in a human-readable form."""

    lines = [
        "Mailbox Roundtrip Tutorial Pack Inspect",
        "",
        "Session Summary",
        f"agent: {payload['agent']}",
        f"tool: {payload['tool']}",
        f"tool_state: {payload['tool_state']}",
        f"agent_identity: {payload['agent_identity']}",
        f"session_name: {payload['session_name']}",
        f"terminal_id: {payload['terminal_id']}",
        f"last_updated: {payload['updated_at']}",
        "",
        "Commands",
        f"tmux_attach: {payload['tmux_attach_command']}",
        f"terminal_log_tail: {payload['terminal_log_tail_command']}",
        "",
        "Artifacts",
        f"session_manifest: {payload['session_manifest']}",
        f"terminal_log_path: {payload['terminal_log_path']}",
        f"project_workdir: {payload['project_workdir']}",
        f"runtime_root: {payload['runtime_root']}",
    ]

    output_text_tail_chars = payload.get("output_text_tail_chars_requested")
    if isinstance(output_text_tail_chars, int):
        lines.extend(["", f"Output Text Tail (last {output_text_tail_chars} chars)"])
        note = payload.get("output_text_tail_note")
        if isinstance(note, str) and note.strip():
            lines.append(note)
        else:
            output_text_tail = payload.get("output_text_tail")
            if isinstance(output_text_tail, str) and output_text_tail:
                lines.extend(f"  {line}" for line in output_text_tail.splitlines())
            else:
                lines.append("  <empty>")

    return "\n".join(lines)


def verify_demo(
    *,
    demo_output_dir: Path,
    expected_report_path: Path,
    snapshot: bool,
) -> dict[str, Any]:
    """Build, sanitize, and verify the report contract for one demo root."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    steps = _require_state_mapping(state, "steps")
    if (
        not bool(steps.get("roundtrip_complete"))
        and not _artifact_path(layout, "mail_send").exists()
    ):
        raise ValueError("roundtrip artifacts are not available for verification")

    message_state = _require_state_mapping(state, "message")
    reply_parent_message_id = message_state.get("send_message_id")
    if not isinstance(reply_parent_message_id, str) or not reply_parent_message_id.strip():
        reply_parent_message_id = extract_message_id(_artifact_path(layout, "mail_send"))
        message_state["send_message_id"] = reply_parent_message_id

    report = build_report(
        output_path=layout.report_path,
        parameters_path=Path(
            _require_non_empty_string(state.get("parameters_path"), context="parameters_path")
        ),
        demo_output_dir=layout.demo_output_dir,
        project_workdir=Path(
            _require_non_empty_string(state.get("project_workdir"), context="project_workdir")
        ),
        runtime_root=Path(
            _require_non_empty_string(state.get("runtime_root"), context="runtime_root")
        ),
        mailbox_root=Path(
            _require_non_empty_string(state.get("mailbox_root"), context="mailbox_root")
        ),
        agent_def_dir=Path(
            _require_non_empty_string(state.get("agent_def_dir"), context="agent_def_dir")
        ),
        reply_parent_message_id=reply_parent_message_id,
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
            _require_mapping(_read_json(expected_report_path), context=str(expected_report_path)),
        )

    result = {
        "ok": True,
        "snapshot_updated": snapshot,
        "expected_report_path": str(expected_report_path.resolve()),
        "report_path": str(layout.report_path),
        "sanitized_report_path": str(layout.sanitized_report_path),
    }
    _write_json(layout.verify_result_path, result)
    steps["verify_complete"] = True
    state["last_verify_result"] = result
    _write_state(layout.state_path, state)
    return result


def stop_demo(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    cleanup: bool = False,
    reason: str | None = None,
    cao_parsing_mode: str | None = None,
) -> dict[str, Any]:
    """Stop demo-owned live resources while preserving ownership boundaries."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    if not layout.state_path.exists():
        payload = {
            "stopped": False,
            "already_stopped": True,
            "cleanup": cleanup,
            "message": f"demo state not found: {layout.state_path}",
        }
        _write_json(layout.stop_result_path, payload)
        return payload

    state = _load_state(layout.state_path)
    jobs_dir = _state_jobs_dir(state)
    resolved_cao_parsing_mode = _resolve_demo_cao_parsing_mode(
        requested_mode=cao_parsing_mode,
        persisted_mode=_state_cao_parsing_mode(state),
    )
    agent_def_dir = Path(
        _require_non_empty_string(state.get("agent_def_dir"), context="agent_def_dir")
    ).resolve()
    result: dict[str, Any] = {
        "stopped": True,
        "cleanup": cleanup,
        "reason": reason,
        "participants": {},
    }

    for role in ("sender", "receiver"):
        participant_state = _require_state_mapping(state, role)
        participant_result: dict[str, Any]
        if not bool(participant_state.get("started_current_run")):
            participant_result = {
                "attempted": False,
                "ownership": "not-started-current-run",
            }
        elif bool(participant_state.get("stopped")):
            participant_result = {
                "attempted": False,
                "ownership": "already-stopped",
            }
        else:
            artifact_name = (
                f"cleanup_{role}_stop.json" if cleanup else _ARTIFACT_FILENAMES[f"{role}_stop"]
            )
            artifact_path = layout.control_dir / artifact_name
            try:
                stop_payload = _run_realm_controller_json(
                    repo_root=repo_root,
                    args=[
                        "stop-session",
                        "--agent-def-dir",
                        str(agent_def_dir),
                        "--agent-identity",
                        _participant_identity(participant_state, context=role),
                        *(
                            ["--cao-parsing-mode", resolved_cao_parsing_mode]
                            if resolved_cao_parsing_mode is not None
                            else []
                        ),
                    ],
                    stdout_path=artifact_path,
                    env=_command_environment(jobs_dir=jobs_dir),
                )
                participant_state["stopped"] = True
                participant_result = {
                    "attempted": True,
                    "artifact_path": str(artifact_path.resolve()),
                    "payload": stop_payload,
                }
            except Exception as exc:
                participant_result = {
                    "attempted": True,
                    "error": str(exc),
                }
                result["stopped"] = False
        result["participants"][role] = participant_result

    cao_state = _require_state_mapping(state, "cao")
    if not bool(cao_state.get("managed")):
        result["cao_stop"] = {
            "attempted": False,
            "ownership": "not-demo-managed",
        }
    elif not bool(cao_state.get("started_current_run")):
        result["cao_stop"] = {
            "attempted": False,
            "ownership": "reused-existing-process",
            "message": "managed CAO was reused and left running",
        }
    elif bool(cao_state.get("stopped")):
        result["cao_stop"] = {
            "attempted": False,
            "ownership": "already-stopped",
        }
    else:
        try:
            cao_payload = stop_demo_cao(
                repo_root=repo_root,
                demo_output_dir=layout.demo_output_dir,
                cao_base_url=_require_non_empty_string(
                    cao_state.get("base_url"),
                    context="cao.base_url",
                ),
            )
            cao_state["stopped"] = True
            result["cao_stop"] = {
                "attempted": True,
                "payload": cao_payload,
            }
            if cleanup:
                _write_json(layout.control_dir / "cleanup_cao_stop.json", cao_payload)
        except Exception as exc:
            result["cao_stop"] = {
                "attempted": True,
                "error": str(exc),
            }
            result["stopped"] = False

    steps = _require_state_mapping(state, "steps")
    steps["stop_complete"] = True
    state["last_stop_result"] = result
    _write_state(layout.state_path, state)
    _write_json(layout.stop_result_path, result)
    return result


def auto_run(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
    expected_report_path: Path,
    jobs_dir: Path | None,
    snapshot: bool,
    cao_parsing_mode: str | None = None,
) -> dict[str, Any]:
    """Run the mailbox roundtrip demo end to end with cleanup on exit."""

    start_demo(
        repo_root=repo_root,
        pack_dir=pack_dir,
        demo_output_dir=demo_output_dir,
        parameters_path=parameters_path,
        jobs_dir=jobs_dir,
        cao_parsing_mode=cao_parsing_mode,
    )
    try:
        roundtrip_demo(
            repo_root=repo_root,
            demo_output_dir=demo_output_dir,
            cao_parsing_mode=cao_parsing_mode,
        )
        verify_result = verify_demo(
            demo_output_dir=demo_output_dir,
            expected_report_path=expected_report_path,
            snapshot=snapshot,
        )
    except KeyboardInterrupt:
        try:
            stop_demo(
                repo_root=repo_root,
                demo_output_dir=demo_output_dir,
                cleanup=True,
                reason="auto interrupted",
                cao_parsing_mode=cao_parsing_mode,
            )
        except Exception:
            pass
        raise
    except Exception:
        try:
            stop_demo(
                repo_root=repo_root,
                demo_output_dir=demo_output_dir,
                cleanup=True,
                reason="auto failed",
                cao_parsing_mode=cao_parsing_mode,
            )
        except Exception:
            pass
        raise

    stop_demo(
        repo_root=repo_root,
        demo_output_dir=demo_output_dir,
        cleanup=False,
        reason="auto complete",
        cao_parsing_mode=cao_parsing_mode,
    )
    return verify_result


def build_report(
    *,
    output_path: Path,
    parameters_path: Path,
    demo_output_dir: Path,
    project_workdir: Path,
    runtime_root: Path,
    mailbox_root: Path,
    agent_def_dir: Path,
    reply_parent_message_id: str,
) -> dict[str, Any]:
    """Build one raw tutorial report from captured command artifacts."""

    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    artifacts = _load_artifacts(layout)
    send_message_id = extract_message_id(_artifact_path(layout, "mail_send"))
    sender_start = artifacts["sender_start"]
    receiver_start = artifacts["receiver_start"]
    sender_mailbox = _require_mapping(sender_start.get("mailbox"), context="sender_start.mailbox")
    receiver_mailbox = _require_mapping(
        receiver_start.get("mailbox"), context="receiver_start.mailbox"
    )
    sender_address = _require_non_empty_string(
        sender_mailbox.get("address"), context="sender address"
    )
    receiver_address = _require_non_empty_string(
        receiver_mailbox.get("address"),
        context="receiver address",
    )
    mailbox_state = {
        "shared_index_sqlite_path": str((mailbox_root.resolve() / "index.sqlite").resolve()),
        "sender_mailbox_dir": str(resolve_active_mailbox_dir(mailbox_root, address=sender_address)),
        "sender_local_sqlite_path": str(
            resolve_active_mailbox_local_sqlite_path(mailbox_root, address=sender_address)
        ),
        "receiver_mailbox_dir": str(
            resolve_active_mailbox_dir(mailbox_root, address=receiver_address)
        ),
        "receiver_local_sqlite_path": str(
            resolve_active_mailbox_local_sqlite_path(mailbox_root, address=receiver_address)
        ),
    }
    cao_payload = _require_mapping(
        _read_json(layout.cao_start_path), context=str(layout.cao_start_path)
    )
    mailbox_inspection = inspect_roundtrip_mailbox(
        mailbox_root=mailbox_root,
        sender_address=sender_address,
        receiver_address=receiver_address,
        send_message_id=send_message_id,
        reply_message_id=_require_non_empty_string(
            artifacts["mail_reply"].get("message_id"), context="mail_reply.message_id"
        ),
        initial_body_path=layout.inputs_dir / Path(parameters.message.initial_body_file).name,
    )
    chat_log = inspect_chat_log(
        chats_path=layout.chats_path,
        send_message_id=send_message_id,
        reply_message_id=_require_non_empty_string(
            artifacts["mail_reply"].get("message_id"), context="mail_reply.message_id"
        ),
        sender_address=sender_address,
        receiver_address=receiver_address,
        initial_body_path=layout.inputs_dir / Path(parameters.message.initial_body_file).name,
        reply_body_markdown=_require_non_empty_string(
            mailbox_inspection.get("reply_body_markdown"), context="mailbox.reply_body_markdown"
        ),
    )

    report = {
        "demo": parameters.demo_id,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_output_dir": str(demo_output_dir.resolve()),
        "control_dir": str(layout.control_dir.resolve()),
        "project_workdir": str(project_workdir.resolve()),
        "runtime_root": str(runtime_root.resolve()),
        "mailbox_root": str(mailbox_root.resolve()),
        "chat_log_path": str(layout.chats_path.resolve()),
        "agent_def_dir": str(agent_def_dir.resolve()),
        "parameters": parameters_to_payload(parameters),
        "artifacts": {
            label: str(path.resolve()) for label, path in _report_artifact_paths(layout).items()
        },
        "cao": cao_payload,
        "flow": list(_REPORT_FLOW),
        "mailbox_state": mailbox_state,
        "chat_log": {
            "path": chat_log["path"],
            "event_count": chat_log["event_count"],
            "kinds": chat_log["kinds"],
        },
        "reply_parent_message_id": reply_parent_message_id,
        "steps": artifacts,
        "checks": {
            "cao_managed": bool(cao_payload.get("managed")),
            "sender_build_manifest_present": bool(artifacts["sender_build"].get("manifest_path")),
            "receiver_build_manifest_present": bool(
                artifacts["receiver_build"].get("manifest_path")
            ),
            "sender_start_mailbox_enabled": sender_mailbox.get("transport") == "filesystem",
            "receiver_start_mailbox_enabled": receiver_mailbox.get("transport") == "filesystem",
            "shared_mailbox_root": sender_mailbox.get("filesystem_root")
            == receiver_mailbox.get("filesystem_root")
            == str(mailbox_root.resolve()),
            "shared_mailbox_index_present": Path(
                mailbox_state["shared_index_sqlite_path"]
            ).is_file(),
            "sender_mailbox_local_sqlite_present": Path(
                mailbox_state["sender_local_sqlite_path"]
            ).is_file(),
            "receiver_mailbox_local_sqlite_present": Path(
                mailbox_state["receiver_local_sqlite_path"]
            ).is_file(),
            "send_message_id_present": bool(send_message_id),
            "reply_parent_matches_send_message_id": reply_parent_message_id == send_message_id,
            "mailbox_send_body_matches_input": bool(mailbox_inspection["send_body_matches_input"]),
            "mailbox_reply_body_present": bool(mailbox_inspection["reply_body_present"]),
            "mailbox_reply_thread_matches_send": bool(
                mailbox_inspection["reply_thread_matches_send"]
            ),
            "mailbox_reply_parent_matches_send": bool(
                mailbox_inspection["reply_parent_matches_send"]
            ),
            "chat_log_present": layout.chats_path.is_file(),
            "chat_log_has_send_event": bool(chat_log["send_event_present"]),
            "chat_log_has_reply_event": bool(chat_log["reply_event_present"]),
            "chat_log_send_matches_input": bool(chat_log["send_event_matches_input"]),
            "chat_log_reply_matches_mailbox_reply": bool(
                chat_log["reply_event_matches_mailbox_reply"]
            ),
            "chat_log_reply_parent_matches_send": bool(chat_log["reply_event_parent_matches_send"]),
        },
    }
    _write_json(output_path, report)
    return report


def _sanitize_string(value: str, *, key: str | None, parent_key: str | None) -> str:
    """Sanitize one string value using field-aware placeholders."""

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
            "sender_mailbox_dir": "<SENDER_MAILBOX_DIR>",
            "sender_local_sqlite_path": "<SENDER_MAILBOX_LOCAL_SQLITE_PATH>",
            "receiver_mailbox_dir": "<RECEIVER_MAILBOX_DIR>",
            "receiver_local_sqlite_path": "<RECEIVER_MAILBOX_LOCAL_SQLITE_PATH>",
        }
        if key in mailbox_placeholders:
            return mailbox_placeholders[key]
    if parent_key == "chat_log" and key == "path":
        return "<CHAT_LOG_PATH>"
    if key in _VALUE_PLACEHOLDERS:
        return _VALUE_PLACEHOLDERS[key]
    if key in _PATH_PLACEHOLDERS:
        return _PATH_PLACEHOLDERS[key]
    if parent_key == "artifacts" and key is not None:
        return f"<ARTIFACT_PATH:{key}>"
    if key in _TIMESTAMP_KEYS or _TIMESTAMP_PATTERN.match(value):
        return "<TIMESTAMP>"
    if _ABSOLUTE_PATH_PATTERN.match(value):
        return "<ABSOLUTE_PATH>"
    return value


def sanitize_report(payload: Any, *, key: str | None = None, parent_key: str | None = None) -> Any:
    """Recursively sanitize one raw tutorial report payload."""

    if isinstance(payload, dict):
        return {
            child_key: sanitize_report(child_value, key=child_key, parent_key=key)
            for child_key, child_value in payload.items()
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


def _cmd_validate_parameters(args: argparse.Namespace) -> int:
    """Validate the tracked parameter file."""

    load_demo_parameters(args.parameters)
    print("parameters valid")
    return 0


def _cmd_json_value(args: argparse.Namespace) -> int:
    """Print one JSON field value."""

    value = extract_json_value(args.json_path, args.dotted_path)
    if isinstance(value, (dict, list)):
        print(json.dumps(value, separators=(",", ":"), sort_keys=True))
    else:
        print(value)
    return 0


def _cmd_render_mailbox_root(args: argparse.Namespace) -> int:
    """Render the demo-local mailbox root path."""

    parameters = load_demo_parameters(args.parameters)
    print(render_mailbox_root(parameters, demo_output_dir=args.demo_output_dir))
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


def _cmd_supports_loopback_cao(args: argparse.Namespace) -> int:
    """Return success when the CAO URL can use demo-local launcher management."""

    if supports_loopback_cao_launcher_management(args.cao_base_url):
        print("managed-loopback")
        return 0
    print("external")
    return 1


def _cmd_message_id(args: argparse.Namespace) -> int:
    """Print one validated message_id."""

    print(extract_message_id(args.payload))
    return 0


def _emit_json_payload(path: Path | None, payload: dict[str, Any]) -> None:
    """Optionally write one JSON payload to disk, then print it to stdout."""

    if path is not None:
        _write_json(path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_start_demo_cao(args: argparse.Namespace) -> int:
    """Start or reuse one demo-local loopback CAO service."""

    payload = start_demo_cao(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        cao_base_url=args.cao_base_url,
    )
    _emit_json_payload(args.output, payload)
    return 0


def _cmd_stop_demo_cao(args: argparse.Namespace) -> int:
    """Stop one demo-local loopback CAO service."""

    payload = stop_demo_cao(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        cao_base_url=args.cao_base_url,
    )
    _emit_json_payload(args.output, payload)
    return 0


def _cmd_build_report(args: argparse.Namespace) -> int:
    """Build one raw report from workspace artifacts."""

    build_report(
        output_path=args.output,
        parameters_path=args.parameters,
        demo_output_dir=args.demo_output_dir,
        project_workdir=args.project_workdir,
        runtime_root=args.runtime_root,
        mailbox_root=args.mailbox_root,
        agent_def_dir=args.agent_def_dir,
        reply_parent_message_id=args.reply_parent_message_id,
    )
    print(args.output)
    return 0


def _cmd_detect_cao_profile_store(args: argparse.Namespace) -> int:
    """Print one best-effort detected CAO profile-store path."""

    detected = detect_cao_profile_store(
        repo_root=args.repo_root,
        cao_base_url=args.cao_base_url,
        launcher_config_path=args.launcher_config_path,
    )
    if detected is not None:
        print(detected)
    return 0


def _cmd_real_agent_preflight(args: argparse.Namespace) -> int:
    """Write one structured real-agent preflight result."""

    payload = resolve_real_agent_preflight(
        repo_root=args.repo_root,
        pack_dir=args.pack_dir,
        parameters_path=args.parameters,
        demo_output_dir=args.demo_output_dir,
        jobs_dir=args.jobs_dir,
        registry_root=args.registry_dir,
        case_id=args.case_id,
    )
    _emit_json_payload(args.output, payload)
    return 0 if bool(payload["ok"]) else 1


def _cmd_write_autotest_result(args: argparse.Namespace) -> int:
    """Write one machine-readable autotest result payload."""

    payload, ok = build_autotest_case_result(
        pack_dir=args.pack_dir,
        demo_output_dir=args.demo_output_dir,
        case_id=args.case_id,
        status=args.status,
        phase=args.phase,
        error_message=args.error_message,
        timed_out=args.timed_out,
        log_dir=args.log_dir,
        preflight_result_path=args.preflight_result_path,
        enforce_mailbox_persistence=args.enforce_mailbox_persistence,
    )
    _emit_json_payload(args.output, payload)
    if args.status == "failure":
        return 0
    return 0 if ok else 1


def _cmd_run_with_timeout(args: argparse.Namespace) -> int:
    """Run one subprocess with timeout-bounded stdout/stderr capture."""

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("run-with-timeout requires a command after `--`")

    args.stdout_path.parent.mkdir(parents=True, exist_ok=True)
    args.stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        args.stdout_path.open("w", encoding="utf-8") as stdout_handle,
        args.stderr_path.open(
            "w",
            encoding="utf-8",
        ) as stderr_handle,
    ):
        try:
            result = subprocess.run(
                command,
                cwd=str(args.cwd.resolve()),
                check=False,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                timeout=float(args.timeout_seconds),
            )
        except subprocess.TimeoutExpired:
            stderr_handle.write(f"TIMEOUT: exceeded {args.timeout_seconds} seconds\n")
            return 124
    return int(result.returncode)


def _cmd_start(args: argparse.Namespace) -> int:
    """Start the stepwise mailbox demo flow."""

    try:
        payload = start_demo(
            repo_root=args.repo_root,
            pack_dir=args.pack_dir,
            demo_output_dir=args.demo_output_dir,
            parameters_path=args.parameters,
            jobs_dir=args.jobs_dir,
            cao_parsing_mode=args.cao_parsing_mode,
        )
    except DemoSkipError as exc:
        print(f"SKIP: {exc}")
        return 0
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    """Run the roundtrip phase for an existing demo root."""

    payload = roundtrip_demo(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        cao_parsing_mode=args.cao_parsing_mode,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Verify or snapshot the sanitized demo report contract."""

    payload = verify_demo(
        demo_output_dir=args.demo_output_dir,
        expected_report_path=args.expected_report,
        snapshot=args.snapshot,
    )
    if args.snapshot:
        print(f"snapshot updated: {args.expected_report}")
        return 0
    print("verification passed")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect one selected tutorial participant."""

    payload = inspect_demo_agent(
        demo_output_dir=args.demo_output_dir,
        agent=args.agent,
        output_text_tail_chars=args.with_output_text,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(_render_human_inspect_output(payload=payload))
    return 0


def _cmd_auto(args: argparse.Namespace) -> int:
    """Run the mailbox demo end to end."""

    try:
        payload = auto_run(
            repo_root=args.repo_root,
            pack_dir=args.pack_dir,
            demo_output_dir=args.demo_output_dir,
            parameters_path=args.parameters,
            expected_report_path=args.expected_report,
            jobs_dir=args.jobs_dir,
            snapshot=args.snapshot,
            cao_parsing_mode=args.cao_parsing_mode,
        )
    except DemoSkipError as exc:
        print(f"SKIP: {exc}")
        return 0
    if args.snapshot:
        print(f"snapshot updated: {args.expected_report}")
    else:
        print("verification passed")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    """Stop live mailbox demo resources for one demo root."""

    payload = stop_demo(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        cleanup=False,
        reason="explicit stop",
        cao_parsing_mode=args.cao_parsing_mode,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the helper CLI parser."""

    parser = argparse.ArgumentParser(description="Mailbox roundtrip tutorial helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-parameters")
    validate_parser.add_argument("parameters", type=Path)
    validate_parser.set_defaults(func=_cmd_validate_parameters)

    json_value_parser = subparsers.add_parser("json-value")
    json_value_parser.add_argument("json_path", type=Path)
    json_value_parser.add_argument("dotted_path")
    json_value_parser.set_defaults(func=_cmd_json_value)

    resolve_path_parser = subparsers.add_parser("resolve-path")
    resolve_path_parser.add_argument("--repo-root", type=Path, required=True)
    resolve_path_parser.add_argument("--default-relative")
    resolve_path_parser.add_argument("raw_path", nargs="?")
    resolve_path_parser.set_defaults(func=_cmd_resolve_path)

    mailbox_root_parser = subparsers.add_parser("render-mailbox-root")
    mailbox_root_parser.add_argument("parameters", type=Path)
    mailbox_root_parser.add_argument("demo_output_dir", type=Path)
    mailbox_root_parser.set_defaults(func=_cmd_render_mailbox_root)

    worktree_parser = subparsers.add_parser("ensure-project-workdir")
    worktree_parser.add_argument("--repo-root", type=Path, required=True)
    worktree_parser.add_argument("--project-fixture", type=Path, required=True)
    worktree_parser.add_argument("--project-workdir", type=Path, required=True)
    worktree_parser.add_argument("--allow-reprovision", action="store_true")
    worktree_parser.set_defaults(func=_cmd_ensure_project_workdir)

    loopback_parser = subparsers.add_parser("supports-loopback-cao")
    loopback_parser.add_argument("--cao-base-url", required=True)
    loopback_parser.set_defaults(func=_cmd_supports_loopback_cao)

    message_id_parser = subparsers.add_parser("message-id")
    message_id_parser.add_argument("payload", type=Path)
    message_id_parser.set_defaults(func=_cmd_message_id)

    start_demo_cao_parser = subparsers.add_parser("start-demo-cao")
    start_demo_cao_parser.add_argument("--output", type=Path)
    start_demo_cao_parser.add_argument("--repo-root", type=Path, required=True)
    start_demo_cao_parser.add_argument("--demo-output-dir", type=Path, required=True)
    start_demo_cao_parser.add_argument("--cao-base-url", required=True)
    start_demo_cao_parser.set_defaults(func=_cmd_start_demo_cao)

    stop_demo_cao_parser = subparsers.add_parser("stop-demo-cao")
    stop_demo_cao_parser.add_argument("--output", type=Path)
    stop_demo_cao_parser.add_argument("--repo-root", type=Path, required=True)
    stop_demo_cao_parser.add_argument("--demo-output-dir", type=Path, required=True)
    stop_demo_cao_parser.add_argument("--cao-base-url", required=True)
    stop_demo_cao_parser.set_defaults(func=_cmd_stop_demo_cao)

    build_report_parser = subparsers.add_parser("build-report")
    build_report_parser.add_argument("--output", type=Path, required=True)
    build_report_parser.add_argument("--parameters", type=Path, required=True)
    build_report_parser.add_argument("--demo-output-dir", type=Path, required=True)
    build_report_parser.add_argument("--project-workdir", type=Path, required=True)
    build_report_parser.add_argument("--runtime-root", type=Path, required=True)
    build_report_parser.add_argument("--mailbox-root", type=Path, required=True)
    build_report_parser.add_argument("--agent-def-dir", type=Path, required=True)
    build_report_parser.add_argument("--reply-parent-message-id", required=True)
    build_report_parser.set_defaults(func=_cmd_build_report)

    detect_profile_store_parser = subparsers.add_parser("detect-cao-profile-store")
    detect_profile_store_parser.add_argument("--repo-root", type=Path, required=True)
    detect_profile_store_parser.add_argument("--cao-base-url", required=True)
    detect_profile_store_parser.add_argument("--launcher-config-path")
    detect_profile_store_parser.set_defaults(func=_cmd_detect_cao_profile_store)

    real_agent_preflight_parser = subparsers.add_parser("real-agent-preflight")
    real_agent_preflight_parser.add_argument("--output", type=Path)
    real_agent_preflight_parser.add_argument("--repo-root", type=Path, required=True)
    real_agent_preflight_parser.add_argument("--pack-dir", type=Path, required=True)
    real_agent_preflight_parser.add_argument("--parameters", type=Path, required=True)
    real_agent_preflight_parser.add_argument("--demo-output-dir", type=Path, required=True)
    real_agent_preflight_parser.add_argument("--jobs-dir", type=Path)
    real_agent_preflight_parser.add_argument("--registry-dir", type=Path)
    real_agent_preflight_parser.add_argument("--case-id", default="real-agent-preflight")
    real_agent_preflight_parser.set_defaults(func=_cmd_real_agent_preflight)

    autotest_result_parser = subparsers.add_parser("write-autotest-result")
    autotest_result_parser.add_argument("--output", type=Path)
    autotest_result_parser.add_argument("--pack-dir", type=Path, required=True)
    autotest_result_parser.add_argument("--demo-output-dir", type=Path, required=True)
    autotest_result_parser.add_argument("--case-id", required=True)
    autotest_result_parser.add_argument("--status", choices=["success", "failure"], required=True)
    autotest_result_parser.add_argument("--phase", required=True)
    autotest_result_parser.add_argument("--error-message")
    autotest_result_parser.add_argument("--timed-out", action="store_true")
    autotest_result_parser.add_argument("--log-dir", type=Path)
    autotest_result_parser.add_argument("--preflight-result-path", type=Path)
    autotest_result_parser.add_argument("--enforce-mailbox-persistence", action="store_true")
    autotest_result_parser.set_defaults(func=_cmd_write_autotest_result)

    run_with_timeout_parser = subparsers.add_parser("run-with-timeout")
    run_with_timeout_parser.add_argument("--cwd", type=Path, required=True)
    run_with_timeout_parser.add_argument("--stdout-path", type=Path, required=True)
    run_with_timeout_parser.add_argument("--stderr-path", type=Path, required=True)
    run_with_timeout_parser.add_argument("--timeout-seconds", type=float, required=True)
    run_with_timeout_parser.add_argument("command", nargs=argparse.REMAINDER)
    run_with_timeout_parser.set_defaults(func=_cmd_run_with_timeout)

    for command_name, func in (
        ("start", _cmd_start),
        ("roundtrip", _cmd_roundtrip),
        ("verify", _cmd_verify),
        ("inspect", _cmd_inspect),
        ("auto", _cmd_auto),
        ("stop", _cmd_stop),
    ):
        subparser = subparsers.add_parser(command_name)
        subparser.add_argument(
            "--demo-output-dir",
            type=Path,
            default=_DEFAULT_DEMO_OUTPUT_DIR,
        )
        if command_name in {"start", "roundtrip", "auto", "stop"}:
            subparser.add_argument("--repo-root", type=Path, required=True)
        if command_name in {"start", "roundtrip", "auto", "stop"}:
            subparser.add_argument(
                "--cao-parsing-mode",
                choices=["shadow_only"],
            )
        if command_name in {"start", "auto"}:
            subparser.add_argument("--pack-dir", type=Path, required=True)
            subparser.add_argument("--parameters", type=Path, required=True)
        if command_name in {"start", "auto"}:
            subparser.add_argument("--jobs-dir", type=Path)
        if command_name == "inspect":
            subparser.add_argument("--agent", choices=["sender", "receiver"], required=True)
            subparser.add_argument("--json", action="store_true")
            subparser.add_argument("--with-output-text", type=int)
        if command_name in {"verify", "auto"}:
            subparser.add_argument("--expected-report", type=Path, required=True)
            subparser.add_argument("--snapshot", action="store_true")
        subparser.set_defaults(func=func)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the helper CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:  # pragma: no cover - CLI guard
        print("error: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

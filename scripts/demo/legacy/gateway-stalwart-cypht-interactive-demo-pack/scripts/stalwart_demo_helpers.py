#!/usr/bin/env python3
"""Helper utilities for the Stalwart and Cypht interactive gateway demo pack."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from urllib import error, request
from urllib.parse import urlparse

from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayMailCheckRequestV1,
    GatewayMailCheckResponseV1,
    GatewayMailNotifierPutV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.agents.realm_controller.gateway_storage import read_gateway_notifier_audit_records
from houmao.cao.no_proxy import is_supported_loopback_cao_base_url
from houmao.cao.server_launcher import (
    load_cao_server_launcher_config,
    resolve_cao_server_runtime_artifacts,
)
from houmao.demo.legacy.launch_support import normalize_demo_launch_backend, resolve_demo_preset_launch
from houmao.mailbox.stalwart import build_stalwart_credential_ref, runtime_stalwart_credential_path

_DEFAULT_DEMO_OUTPUT_DIR = Path("tmp/demo/gateway-stalwart-cypht-interactive-demo-pack")
_WORKSPACE_MARKER = ".houmao-demo-workspace.json"
_STOP_FILENAME = "stop_demo.json"


@dataclass(frozen=True)
class DemoGateway:
    """Tracked gateway demo configuration."""

    host: str
    notifier_interval_seconds: int
    watch_poll_interval_seconds: int


@dataclass(frozen=True)
class DemoParticipant:
    """Tracked participant mailbox and session configuration."""

    blueprint: str
    agent_identity: str
    mailbox_principal_id: str
    mailbox_address: str
    login_identity: str
    cypht_username: str
    cypht_password: str


@dataclass(frozen=True)
class DemoStack:
    """Tracked Stalwart stack configuration."""

    env_file: str


@dataclass(frozen=True)
class DemoParameters:
    """Validated tracked demo parameters."""

    schema_version: int
    demo_id: str
    agent_def_dir: str
    project_fixture: str
    backend: str
    cao_base_url: str
    stack: DemoStack
    gateway: DemoGateway
    participants: dict[str, DemoParticipant]


@dataclass(frozen=True)
class DemoLayout:
    """Resolved pack-local demo filesystem layout."""

    demo_output_dir: Path
    workspace_dir: Path
    runtime_root: Path
    cao_dir: Path
    cao_launcher_config_path: Path
    stack_dir: Path
    inputs_dir: Path
    participants_dir: Path
    state_path: Path
    turns_path: Path
    inspect_path: Path
    cao_start_path: Path
    stack_start_path: Path


@dataclass(frozen=True)
class StalwartStackConfig:
    """Minimal local stack config loaded from `dockers/email-system/.env`."""

    env_file: Path
    http_port: int
    cypht_http_port: int
    bootstrap_user: str
    bootstrap_password: str
    mail_domain: str

    @property
    def base_url(self) -> str:
        """Return the Stalwart base URL."""

        return f"http://127.0.0.1:{self.http_port}"

    @property
    def jmap_url(self) -> str:
        """Return the JMAP URL."""

        return f"{self.base_url}/jmap"

    @property
    def management_url(self) -> str:
        """Return the management API URL."""

        return f"{self.base_url}/api"

    @property
    def cypht_url(self) -> str:
        """Return the Cypht URL."""

        return f"http://127.0.0.1:{self.cypht_http_port}"


def _utc_now_iso() -> str:
    """Return the current UTC time in RFC3339-like form."""

    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    """Load one JSON payload from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    """Write one JSON payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as a JSONL row."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL rows from disk when the file exists."""

    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(_require_mapping(json.loads(stripped), context=str(path)))
    return rows


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


def _optional_non_empty_string(value: Any, *, context: str) -> str | None:
    """Return one optional non-empty string."""

    if value is None:
        return None
    return _require_non_empty_string(value, context=context)


def resolve_repo_relative_path(
    raw_path: str | None,
    *,
    repo_root: Path,
    default_relative: str | Path | None = None,
) -> Path:
    """Resolve one optional path against the repository root."""

    if raw_path is None or not raw_path.strip():
        if default_relative is None:
            raise ValueError("path is required when no default is provided")
        candidate = Path(default_relative)
    else:
        candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root.resolve() / candidate).resolve()


def build_demo_layout(*, demo_output_dir: Path) -> DemoLayout:
    """Build the stable demo-owned directory layout."""

    resolved = demo_output_dir.resolve()
    cao_dir = resolved / "cao"
    return DemoLayout(
        demo_output_dir=resolved,
        workspace_dir=resolved / "workspace",
        runtime_root=resolved / "runtime",
        cao_dir=cao_dir,
        cao_launcher_config_path=cao_dir / "launcher.toml",
        stack_dir=resolved / "stack",
        inputs_dir=resolved / "inputs",
        participants_dir=resolved / "participants",
        state_path=resolved / "demo_state.json",
        turns_path=resolved / "turns.jsonl",
        inspect_path=resolved / "inspect.json",
        cao_start_path=resolved / "cao_start.json",
        stack_start_path=resolved / "stack_start.json",
    )


def _participant_dir(layout: DemoLayout, who: str) -> Path:
    """Return the artifact directory for one participant."""

    return layout.participants_dir / who


def _participant_artifact_path(layout: DemoLayout, who: str, name: str) -> Path:
    """Return one participant-local artifact path."""

    return _participant_dir(layout, who) / f"{name}.json"


def _stderr_path_for(path: Path) -> Path:
    """Return the paired stderr path for one captured artifact."""

    return path.with_suffix(path.suffix + ".err")


def _copy_inputs(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Refresh tracked pack inputs into the demo output directory."""

    if layout.inputs_dir.exists():
        shutil.rmtree(layout.inputs_dir)
    shutil.copytree(pack_dir / "inputs", layout.inputs_dir)


def _write_workspace_marker(*, layout: DemoLayout, fixture_dir: Path) -> None:
    """Record which tracked fixture populated the demo workspace."""

    _write_json(
        layout.workspace_dir / _WORKSPACE_MARKER,
        {
            "schema_version": 1,
            "managed_by": "gateway-stalwart-cypht-interactive-demo-pack",
            "fixture_dir": str(fixture_dir.resolve()),
            "prepared_at_utc": _utc_now_iso(),
        },
    )


def prepare_workspace_from_fixture(
    *,
    repo_root: Path,
    parameters: DemoParameters,
    layout: DemoLayout,
) -> Path:
    """Copy the tracked dummy-project fixture into the demo workspace."""

    fixture_dir = resolve_repo_relative_path(parameters.project_fixture, repo_root=repo_root)
    if not fixture_dir.is_dir():
        raise ValueError(f"dummy-project fixture directory not found: {fixture_dir}")
    if layout.workspace_dir.exists():
        shutil.rmtree(layout.workspace_dir)
    shutil.copytree(fixture_dir, layout.workspace_dir)
    _write_workspace_marker(layout=layout, fixture_dir=fixture_dir)
    return fixture_dir.resolve()


def _freshen_demo_output(*, pack_dir: Path, layout: DemoLayout) -> None:
    """Reset demo-owned runtime output for a fresh run."""

    for path in (
        layout.workspace_dir,
        layout.runtime_root,
        layout.cao_dir,
        layout.stack_dir,
        layout.inputs_dir,
        layout.participants_dir,
    ):
        if path.exists():
            shutil.rmtree(path)
    for path in (
        layout.state_path,
        layout.turns_path,
        layout.inspect_path,
        layout.cao_start_path,
        layout.stack_start_path,
        layout.demo_output_dir / _STOP_FILENAME,
    ):
        if path.exists():
            path.unlink()
    _copy_inputs(pack_dir=pack_dir, layout=layout)


def _normalize_cao_base_url(value: str) -> str:
    """Normalize one loopback CAO base URL."""

    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme != "http":
        raise ValueError("CAO base URL must use http")
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("CAO base URL must include host and explicit port")
    return f"http://{parsed.hostname}:{parsed.port}"


def default_cao_profile_store(*, cao_home: Path) -> Path:
    """Return the default CAO profile-store path for one CAO home."""

    return (cao_home.resolve() / ".aws" / "cli-agent-orchestrator" / "agent-store").resolve()


def _default_launcher_runner(args: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Run one CAO launcher CLI command."""

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
    """Write the demo-local CAO launcher config."""

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
) -> dict[str, Any]:
    """Run one launcher command and parse the JSON result."""

    result = _default_launcher_runner(args, repo_root.resolve())
    if result.returncode not in accepted_exit_codes:
        detail = result.stderr.strip() or result.stdout.strip() or "launcher command failed"
        raise RuntimeError(detail)
    payload_text = result.stdout.strip() or result.stderr.strip()
    if not payload_text:
        raise RuntimeError("launcher command returned no JSON payload")
    return _require_mapping(json.loads(payload_text), context="launcher result")


def start_demo_cao(*, repo_root: Path, demo_output_dir: Path, cao_base_url: str) -> dict[str, Any]:
    """Start or reuse the demo-local loopback CAO service."""

    normalized = _normalize_cao_base_url(cao_base_url)
    if not is_supported_loopback_cao_base_url(normalized):
        raise ValueError("the interactive demo pack requires a loopback CAO base URL")

    config_path = write_demo_cao_launcher_config(
        demo_output_dir=demo_output_dir,
        cao_base_url=normalized,
    )
    config = load_cao_server_launcher_config(config_path)
    artifacts = resolve_cao_server_runtime_artifacts(config)
    payload = _launcher_json(
        repo_root=repo_root,
        args=["start", "--config", str(config_path)],
        accepted_exit_codes={0},
    )
    return {
        "managed": True,
        "base_url": normalized,
        "launcher_config_path": str(config.config_path),
        "runtime_root": str(config.runtime_root),
        "home_dir": str(artifacts.home_dir),
        "profile_store": str(default_cao_profile_store(cao_home=artifacts.home_dir)),
        "artifact_dir": str(artifacts.artifact_dir),
        "log_file": str(artifacts.log_file),
        "launcher_result_file": str(artifacts.launcher_result_file),
        "ownership_file": str(artifacts.ownership_file),
        "healthy": bool(payload.get("healthy")),
        "started_current_run": bool(payload.get("started_new_process")),
        "reused_existing_process": bool(payload.get("reused_existing_process")),
        "message": _require_non_empty_string(payload.get("message"), context="launcher.message"),
    }


def stop_demo_cao(*, repo_root: Path, demo_output_dir: Path) -> dict[str, Any]:
    """Stop the demo-local CAO service."""

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
    )


def _strip_inline_comment(value: str) -> str:
    """Strip one unquoted inline env-file comment."""

    in_single = False
    in_double = False
    result: list[str] = []

    for char in value:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)

    stripped = "".join(result).strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def _load_env_file(env_file: Path) -> dict[str, str]:
    """Load simple `KEY=VALUE` pairs from an env file."""

    payload: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"invalid env line in {env_file}: {line!r}")
        key, raw_value = stripped.split("=", 1)
        payload[key.strip()] = _strip_inline_comment(raw_value)
    return payload


def _require_env_value(values: dict[str, str], key: str) -> str:
    """Return one required env value."""

    try:
        return values[key]
    except KeyError as exc:
        raise ValueError(f"missing required env value: {key}") from exc


def load_stack_config(*, repo_root: Path, parameters: DemoParameters) -> StalwartStackConfig:
    """Load the tracked Stalwart stack config."""

    env_file = resolve_repo_relative_path(parameters.stack.env_file, repo_root=repo_root)
    values = _load_env_file(env_file)
    return StalwartStackConfig(
        env_file=env_file,
        http_port=int(_require_env_value(values, "STALWART_HTTP_PORT")),
        cypht_http_port=int(_require_env_value(values, "CYPHT_HTTP_PORT")),
        bootstrap_user=_require_env_value(values, "STALWART_BOOTSTRAP_USER"),
        bootstrap_password=_require_env_value(values, "STALWART_BOOTSTRAP_PASSWORD"),
        mail_domain=_require_env_value(values, "MAIL_DOMAIN"),
    )


def _run_command_capture(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    accepted_exit_codes: set[int] | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one command and persist stdout and stderr."""

    result = subprocess.run(
        command,
        cwd=str(cwd.resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=None if env is None else {**os.environ, **env},
    )
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    allowed = accepted_exit_codes if accepted_exit_codes is not None else {0}
    if result.returncode not in allowed:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise RuntimeError(f"{detail} (exit={result.returncode})")
    return result


def _run_json_command(
    *,
    command: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    accepted_exit_codes: set[int] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run one command and parse a JSON stdout payload."""

    result = _run_command_capture(
        command=command,
        cwd=cwd,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        accepted_exit_codes=accepted_exit_codes,
        env=env,
    )
    payload_text = result.stdout.strip()
    if not payload_text:
        return {}
    return _require_mapping(json.loads(payload_text), context="command output")


def _run_realm_controller_json(
    *,
    repo_root: Path,
    args: list[str],
    stdout_path: Path,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run one `houmao.agents.realm_controller` command."""

    return _run_json_command(
        command=["pixi", "run", "python", "-m", "houmao.agents.realm_controller", *args],
        cwd=repo_root,
        stdout_path=stdout_path,
        stderr_path=_stderr_path_for(stdout_path),
        env=env,
    )


def _http_get_ok(url: str, *, timeout_seconds: float = 5.0) -> None:
    """Assert that one HTTP GET request succeeds."""

    request_obj = request.Request(url=url, method="GET")
    try:
        with request.urlopen(request_obj, timeout=timeout_seconds):
            return
    except error.URLError as exc:
        raise RuntimeError(f"GET {url} failed: {exc.reason}") from exc


def seed_runtime_mailbox_credentials(
    *,
    runtime_root: Path,
    participants: dict[str, DemoParticipant],
    jmap_url: str,
) -> dict[str, str]:
    """Seed runtime-owned Stalwart credentials so Cypht passwords stay stable."""

    written: dict[str, str] = {}
    for name, participant in participants.items():
        credential_ref = build_stalwart_credential_ref(
            address=participant.mailbox_address,
            jmap_url=jmap_url,
        )
        credential_path = runtime_stalwart_credential_path(runtime_root, credential_ref)
        _write_json(
            credential_path,
            {
                "credential_ref": credential_ref,
                "login_identity": participant.login_identity,
                "password": participant.cypht_password,
            },
        )
        credential_path.chmod(0o600)
        written[name] = str(credential_path.resolve())
    return written


def _stack_environment(stack_config: StalwartStackConfig) -> dict[str, str]:
    """Build the Stalwart management env for runtime commands."""

    return {
        "HOUMAO_STALWART_BASE_URL": stack_config.base_url,
        "HOUMAO_STALWART_MANAGEMENT_API_KEY": stack_config.bootstrap_user,
        "HOUMAO_STALWART_MANAGEMENT_API_SECRET": stack_config.bootstrap_password,
    }


def _start_stack_and_ensure_accounts(
    *,
    repo_root: Path,
    parameters: DemoParameters,
    layout: DemoLayout,
) -> dict[str, Any]:
    """Bring up the local stack and ensure the tracked Alice and Bob accounts."""

    stack_config = load_stack_config(repo_root=repo_root, parameters=parameters)
    stack_root = stack_config.env_file.parent

    _run_command_capture(
        command=["./up.sh"],
        cwd=stack_root,
        stdout_path=layout.stack_dir / "up.stdout.txt",
        stderr_path=layout.stack_dir / "up.stderr.txt",
    )
    _http_get_ok(f"{stack_config.base_url}/login")
    _http_get_ok(f"{stack_config.cypht_url}/")

    accounts: dict[str, Any] = {}
    for name, participant in parameters.participants.items():
        command = [
            "pixi",
            "run",
            "python",
            str((stack_root / "provision_stalwart.py").resolve()),
            "--env-file",
            str(stack_config.env_file),
            "ensure-account",
            "--name",
            participant.login_identity,
            "--email",
            participant.mailbox_address,
            "--password",
            participant.cypht_password,
            "--description",
            f"Interactive gateway demo mailbox for {name}",
            "--reset-password",
        ]
        artifact_root = layout.stack_dir / "accounts"
        stdout_path = artifact_root / f"{name}.stdout.txt"
        _run_command_capture(
            command=command,
            cwd=repo_root,
            stdout_path=stdout_path,
            stderr_path=artifact_root / f"{name}.stderr.txt",
        )
        accounts[name] = {
            "login_identity": participant.login_identity,
            "mailbox_address": participant.mailbox_address,
            "cypht_username": participant.cypht_username,
            "cypht_password": participant.cypht_password,
            "stdout_path": str(stdout_path.resolve()),
        }

    credential_files = seed_runtime_mailbox_credentials(
        runtime_root=layout.runtime_root,
        participants=parameters.participants,
        jmap_url=stack_config.jmap_url,
    )

    return {
        "env_file": str(stack_config.env_file.resolve()),
        "base_url": stack_config.base_url,
        "jmap_url": stack_config.jmap_url,
        "management_url": stack_config.management_url,
        "cypht_url": stack_config.cypht_url,
        "mail_domain": stack_config.mail_domain,
        "bootstrap_user": stack_config.bootstrap_user,
        "accounts": accounts,
        "runtime_credentials": credential_files,
    }


def _load_state(state_path: Path) -> dict[str, Any]:
    """Load one persisted demo state payload."""

    return _require_mapping(_read_json(state_path), context=str(state_path))


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    """Persist the current demo state."""

    _write_json(path, payload)


def _wait_for_gateway_mail_status(
    endpoint: GatewayEndpoint,
    *,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Wait for a just-attached gateway to expose `/v1/mail/status`."""

    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None
    client = GatewayClient(endpoint=endpoint)
    while time.monotonic() < deadline:
        try:
            return client.mail_status().model_dump(mode="json")
        except Exception as exc:  # pragma: no cover - narrow retry wrapper
            last_error = str(exc)
            time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for gateway mail status: {last_error}")


def _gateway_endpoint_from_payload(payload: dict[str, Any]) -> GatewayEndpoint:
    """Build one gateway endpoint from an attach payload."""

    return GatewayEndpoint(
        host=_require_non_empty_string(payload.get("gateway_host"), context="gateway_host"),
        port=int(payload.get("gateway_port")),
    )


def _participant_client(participant_state: dict[str, Any]) -> GatewayClient:
    """Build one gateway client for a participant."""

    endpoint = _gateway_endpoint_from_payload(
        _require_mapping(participant_state.get("gateway"), context="participant.gateway")
    )
    return GatewayClient(endpoint=endpoint)


def _put_notifier(participant_state: dict[str, Any], *, interval_seconds: int) -> dict[str, Any]:
    """Enable the unread-mail notifier for one participant gateway."""

    client = _participant_client(participant_state)
    payload = client.put_mail_notifier(GatewayMailNotifierPutV1(interval_seconds=interval_seconds))
    return payload.model_dump(mode="json")


def _delete_notifier(participant_state: dict[str, Any]) -> dict[str, Any]:
    """Disable the unread-mail notifier for one participant gateway."""

    client = _participant_client(participant_state)
    payload = client.delete_mail_notifier()
    return payload.model_dump(mode="json")


def _participant_parameters(
    parameters: DemoParameters,
    *,
    who: str,
) -> DemoParticipant:
    """Return the tracked participant config for one named side."""

    try:
        return parameters.participants[who]
    except KeyError as exc:
        raise ValueError(f"unknown participant: {who}") from exc


def _load_parameters_from_state(state: dict[str, Any]) -> DemoParameters:
    """Reload the tracked demo parameters for one persisted state."""

    parameters_path = Path(
        _require_non_empty_string(state.get("parameters_path"), context="parameters_path")
    )
    return load_demo_parameters(parameters_path)


def append_turn(
    *,
    layout: DemoLayout,
    state: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Append one turn record and persist the incremented turn counter."""

    next_turn = int(state.get("turn_counter", 0)) + 1
    entry = {
        "turn_index": next_turn,
        "recorded_at_utc": _utc_now_iso(),
        **payload,
    }
    _append_jsonl(layout.turns_path, entry)
    state["turn_counter"] = next_turn
    _write_state(layout.state_path, state)
    return entry


def _body_text_from_args(
    *,
    repo_root: Path,
    body_content: str | None,
    body_file: str | None,
) -> str:
    """Resolve one send or reply body from inline text or a file."""

    if body_content is not None and body_file is not None:
        raise ValueError("use either --body-content or --body-file, not both")
    if body_content is not None:
        if not body_content.strip():
            raise ValueError("--body-content must not be empty")
        return body_content
    if body_file is None:
        raise ValueError("either --body-content or --body-file is required")
    path = resolve_repo_relative_path(body_file, repo_root=repo_root)
    return path.read_text(encoding="utf-8")


def _recipient_address(parameters: DemoParameters, raw_value: str) -> str:
    """Resolve a participant alias or raw mailbox address."""

    participant = parameters.participants.get(raw_value)
    if participant is not None:
        return participant.mailbox_address
    if "@" not in raw_value:
        raise ValueError(f"recipient must be a known participant or mailbox address: {raw_value}")
    return raw_value


def format_check_response(*, who: str, response: GatewayMailCheckResponseV1) -> str:
    """Render one gateway mailbox check response for human inspection."""

    lines = [
        f"Mailbox: {who} ({response.address})",
        f"Transport: {response.transport}",
        f"Unread-only: {str(response.unread_only).lower()}",
        f"Shown: {response.message_count}",
        f"Unread total: {response.unread_count}",
    ]
    if not response.messages:
        lines.append("Messages: none")
        return "\n".join(lines)

    for index, message in enumerate(response.messages, start=1):
        sender = message.sender.address
        body = message.body_text or message.body_preview or ""
        lines.extend(
            [
                "",
                f"[{index}] {message.created_at_utc}",
                f"From: {sender}",
                f"Subject: {message.subject}",
                f"Message-Ref: {message.message_ref}",
                f"Unread: {str(bool(message.unread)).lower()}",
                "Body:",
                body.rstrip(),
            ]
        )
    return "\n".join(lines)


def summarize_notifier_audit_records(rows: list[Any]) -> dict[str, Any]:
    """Reduce raw notifier audit rows to a stable summary."""

    outcomes = [row.outcome for row in rows]
    unread_subjects: list[str] = []
    unread_refs: list[str] = []
    latest_poll: str | None = None
    max_unread_count = 0
    for row in rows:
        latest_poll = row.poll_time_utc
        if row.unread_count is not None:
            max_unread_count = max(max_unread_count, row.unread_count)
        for unread in row.unread_summary:
            if unread.subject not in unread_subjects:
                unread_subjects.append(unread.subject)
            if unread.message_ref not in unread_refs:
                unread_refs.append(unread.message_ref)

    counts = Counter(outcomes)
    return {
        "row_count": len(rows),
        "latest_poll_time_utc": latest_poll,
        "observed_outcomes": sorted(counts.keys()),
        "outcome_counts": dict(sorted(counts.items())),
        "has_enqueued": counts.get("enqueued", 0) > 0,
        "has_busy_skip": counts.get("busy_skip", 0) > 0,
        "has_repeated_enqueued": counts.get("enqueued", 0) > 1,
        "has_poll_error": counts.get("poll_error", 0) > 0,
        "max_unread_count": max_unread_count,
        "unread_subjects": unread_subjects,
        "unread_message_refs": unread_refs,
    }


def format_inspect_summary(payload: dict[str, Any]) -> str:
    """Render one compact human summary for `inspect`."""

    lines = [
        f"Cypht: {payload['stack']['cypht_url']}",
        f"Turns recorded: {len(payload['turn_history'])}",
    ]
    for who, participant in payload["participants"].items():
        unread = _require_mapping(participant["unread_check"], context=f"{who}.unread_check")
        notifier = _require_mapping(participant["notifier_status"], context=f"{who}.notifier")
        audit = _require_mapping(participant["notifier_audit_summary"], context=f"{who}.audit")
        lines.extend(
            [
                "",
                f"{who}:",
                f"  mailbox={participant['mail_status']['address']}",
                f"  gateway=http://127.0.0.1:{participant['gateway']['gateway_port']}",
                f"  unread_count={unread['unread_count']}",
                f"  notifier_enabled={str(bool(notifier['enabled'])).lower()}",
                f"  notifier_outcomes={','.join(audit['observed_outcomes']) or 'none'}",
            ]
        )
    return "\n".join(lines)


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load and validate the tracked demo parameters."""

    payload = _require_mapping(_read_json(path), context=str(path))
    schema_version = int(payload.get("schema_version"))
    if schema_version != 1:
        raise ValueError("demo parameters must use schema_version=1")

    stack_payload = _require_mapping(payload.get("stack"), context="stack")
    gateway_payload = _require_mapping(payload.get("gateway"), context="gateway")
    participants_payload = _require_mapping(payload.get("participants"), context="participants")

    participants: dict[str, DemoParticipant] = {}
    for name, raw_participant in participants_payload.items():
        mapping = _require_mapping(raw_participant, context=f"participants.{name}")
        participants[name] = DemoParticipant(
            blueprint=_require_non_empty_string(
                mapping.get("blueprint"), context=f"{name}.blueprint"
            ),
            agent_identity=_require_non_empty_string(
                mapping.get("agent_identity"), context=f"{name}.agent_identity"
            ),
            mailbox_principal_id=_require_non_empty_string(
                mapping.get("mailbox_principal_id"),
                context=f"{name}.mailbox_principal_id",
            ),
            mailbox_address=_require_non_empty_string(
                mapping.get("mailbox_address"), context=f"{name}.mailbox_address"
            ),
            login_identity=_require_non_empty_string(
                mapping.get("login_identity"), context=f"{name}.login_identity"
            ),
            cypht_username=_require_non_empty_string(
                mapping.get("cypht_username"), context=f"{name}.cypht_username"
            ),
            cypht_password=_require_non_empty_string(
                mapping.get("cypht_password"), context=f"{name}.cypht_password"
            ),
        )

    if {"alice", "bob"} - set(participants):
        raise ValueError("demo parameters must include both `alice` and `bob` participants")

    parameters = DemoParameters(
        schema_version=schema_version,
        demo_id=_require_non_empty_string(payload.get("demo_id"), context="demo_id"),
        agent_def_dir=_require_non_empty_string(
            payload.get("agent_def_dir"), context="agent_def_dir"
        ),
        project_fixture=_require_non_empty_string(
            payload.get("project_fixture"), context="project_fixture"
        ),
        backend=_require_non_empty_string(payload.get("backend"), context="backend"),
        cao_base_url=_require_non_empty_string(payload.get("cao_base_url"), context="cao_base_url"),
        stack=DemoStack(
            env_file=_require_non_empty_string(
                stack_payload.get("env_file"), context="stack.env_file"
            )
        ),
        gateway=DemoGateway(
            host=_require_non_empty_string(gateway_payload.get("host"), context="gateway.host"),
            notifier_interval_seconds=int(gateway_payload.get("notifier_interval_seconds")),
            watch_poll_interval_seconds=int(gateway_payload.get("watch_poll_interval_seconds")),
        ),
        participants=participants,
    )
    if normalize_demo_launch_backend(parameters.backend) != "local_interactive":
        raise ValueError("demo parameters backend must be `local_interactive` or legacy `cao_rest`")
    if parameters.gateway.host != "127.0.0.1":
        raise ValueError("the interactive demo pack requires loopback-only gateway host")
    if parameters.gateway.notifier_interval_seconds < 1:
        raise ValueError("gateway.notifier_interval_seconds must be >= 1")
    if parameters.gateway.watch_poll_interval_seconds < 1:
        raise ValueError("gateway.watch_poll_interval_seconds must be >= 1")
    return parameters


def start_demo(
    *,
    repo_root: Path,
    pack_dir: Path,
    demo_output_dir: Path,
    parameters_path: Path,
) -> dict[str, Any]:
    """Start the Stalwart stack, two sessions, and two gateways."""

    parameters = load_demo_parameters(parameters_path)
    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    stop_demo_path = layout.demo_output_dir / _STOP_FILENAME
    if layout.state_path.exists() and not stop_demo_path.exists():
        raise ValueError(
            "demo state already exists for this output directory and has not been stopped; "
            "run `run_demo.sh stop` first"
        )

    _freshen_demo_output(pack_dir=pack_dir, layout=layout)
    fixture_dir = prepare_workspace_from_fixture(
        repo_root=repo_root,
        parameters=parameters,
        layout=layout,
    )
    layout.runtime_root.mkdir(parents=True, exist_ok=True)

    agent_def_dir = resolve_repo_relative_path(
        os.environ.get("AGENT_DEF_DIR"),
        repo_root=repo_root,
        default_relative=parameters.agent_def_dir,
    )
    cao_context = start_demo_cao(
        repo_root=repo_root,
        demo_output_dir=demo_output_dir,
        cao_base_url=parameters.cao_base_url,
    )
    _write_json(layout.cao_start_path, cao_context)

    state: dict[str, Any] = {
        "schema_version": 1,
        "demo_id": parameters.demo_id,
        "parameters_path": str(parameters_path.resolve()),
        "demo_output_dir": str(layout.demo_output_dir),
        "workspace_dir": str(layout.workspace_dir),
        "workspace_fixture": str(fixture_dir),
        "runtime_root": str(layout.runtime_root),
        "agent_def_dir": str(agent_def_dir),
        "cao": cao_context,
        "participants": {},
        "turn_counter": 0,
        "started_at_utc": _utc_now_iso(),
    }
    _write_state(layout.state_path, state)

    try:
        stack_state = _start_stack_and_ensure_accounts(
            repo_root=repo_root,
            parameters=parameters,
            layout=layout,
        )
        state["stack"] = stack_state
        _write_json(layout.stack_start_path, stack_state)
        _write_state(layout.state_path, state)

        base_env = _stack_environment(load_stack_config(repo_root=repo_root, parameters=parameters))
        for name, participant in parameters.participants.items():
            participant_dir = _participant_dir(layout, name)
            participant_dir.mkdir(parents=True, exist_ok=True)
            resolved_launch = resolve_demo_preset_launch(
                agent_def_dir=agent_def_dir,
                preset_path=(repo_root / participant.blueprint).resolve(),
            )

            build_payload = _run_realm_controller_json(
                repo_root=repo_root,
                args=[
                    "build-brain",
                    "--agent-def-dir",
                    str(agent_def_dir),
                    "--runtime-root",
                    str(layout.runtime_root),
                    "--preset",
                    str(resolved_launch.preset_path),
                ],
                stdout_path=_participant_artifact_path(layout, name, "brain_build"),
                env=base_env,
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
                    _require_non_empty_string(
                        build_payload.get("manifest_path"),
                        context=f"{name}.build.manifest_path",
                    ),
                    "--role",
                    resolved_launch.role_name,
                    "--backend",
                    normalize_demo_launch_backend(parameters.backend),
                    "--cao-base-url",
                    _require_non_empty_string(
                        cao_context.get("base_url"),
                        context="cao.base_url",
                    ),
                    "--cao-profile-store",
                    _require_non_empty_string(
                        cao_context.get("profile_store"),
                        context="cao.profile_store",
                    ),
                    "--workdir",
                    str(layout.workspace_dir),
                    "--agent-identity",
                    participant.agent_identity,
                    "--mailbox-transport",
                    "stalwart",
                    "--mailbox-principal-id",
                    participant.mailbox_principal_id,
                    "--mailbox-address",
                    participant.mailbox_address,
                    "--mailbox-stalwart-base-url",
                    _require_non_empty_string(
                        stack_state.get("base_url"), context="stack.base_url"
                    ),
                    "--mailbox-stalwart-login-identity",
                    participant.login_identity,
                ],
                stdout_path=_participant_artifact_path(layout, name, "session_start"),
                env=base_env,
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
                        context=f"{name}.session_manifest",
                    ),
                    "--gateway-host",
                    parameters.gateway.host,
                ],
                stdout_path=_participant_artifact_path(layout, name, "gateway_attach"),
                env=base_env,
            )
            endpoint = _gateway_endpoint_from_payload(attach_payload)
            mail_status = _wait_for_gateway_mail_status(endpoint)
            participant_state: dict[str, Any] = {
                "account": asdict(participant),
                "build": build_payload,
                "session": session_payload,
                "gateway": attach_payload,
                "mail_status": mail_status,
            }
            participant_state["notifier"] = _put_notifier(
                participant_state,
                interval_seconds=parameters.gateway.notifier_interval_seconds,
            )
            _write_json(
                _participant_artifact_path(layout, name, "notifier_enable"),
                participant_state["notifier"],
            )
            state["participants"][name] = participant_state
            _write_state(layout.state_path, state)
    except Exception:
        _write_state(layout.state_path, state)
        try:
            stop_demo(repo_root=repo_root, demo_output_dir=demo_output_dir, cleanup_only=True)
        except Exception:
            pass
        raise

    return state


def send_demo(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    sender: str,
    recipient: str,
    subject: str,
    body_content: str | None,
    body_file: str | None,
) -> dict[str, Any]:
    """Send one message through the sender gateway mailbox facade."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    parameters = _load_parameters_from_state(state)
    sender_state = _require_mapping(state["participants"][sender], context=f"participants.{sender}")
    body_text = _body_text_from_args(
        repo_root=repo_root,
        body_content=body_content,
        body_file=body_file,
    )
    payload = _participant_client(sender_state).send_mail(
        GatewayMailSendRequestV1(
            to=[_recipient_address(parameters, recipient)],
            subject=subject,
            body_content=body_text,
        )
    )
    result = payload.model_dump(mode="json")
    _write_json(_participant_artifact_path(layout, sender, "last_send"), result)
    append_turn(
        layout=layout,
        state=state,
        payload={
            "operation": "send",
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "message_ref": result["message"]["message_ref"],
        },
    )
    return result


def _latest_unread_message_ref(participant_state: dict[str, Any]) -> str:
    """Resolve the newest unread message reference for one participant."""

    response = _participant_client(participant_state).check_mail(
        GatewayMailCheckRequestV1(unread_only=True, limit=50)
    )
    if not response.messages:
        raise ValueError("no unread messages are available to reply to")
    newest = max(response.messages, key=lambda message: message.created_at_utc)
    return newest.message_ref


def reply_demo(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    sender: str,
    message_ref: str | None,
    latest_unread: bool,
    body_content: str | None,
    body_file: str | None,
) -> dict[str, Any]:
    """Reply to one unread or explicit message through the sender gateway."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    sender_state = _require_mapping(state["participants"][sender], context=f"participants.{sender}")
    reply_target = message_ref
    if latest_unread:
        reply_target = _latest_unread_message_ref(sender_state)
    if reply_target is None:
        raise ValueError("reply requires --message-ref or --latest-unread")
    body_text = _body_text_from_args(
        repo_root=repo_root,
        body_content=body_content,
        body_file=body_file,
    )
    payload = _participant_client(sender_state).reply_mail(
        GatewayMailReplyRequestV1(message_ref=reply_target, body_content=body_text)
    )
    result = payload.model_dump(mode="json")
    _write_json(_participant_artifact_path(layout, sender, "last_reply"), result)
    append_turn(
        layout=layout,
        state=state,
        payload={
            "operation": "reply",
            "sender": sender,
            "message_ref": reply_target,
            "result_message_ref": result["message"]["message_ref"],
        },
    )
    return result


def check_demo(
    *,
    demo_output_dir: Path,
    who: str,
    unread_only: bool,
    limit: int | None,
    since: str | None,
) -> dict[str, Any]:
    """Check one participant mailbox through the gateway facade."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    participant_state = _require_mapping(state["participants"][who], context=f"participants.{who}")
    payload = _participant_client(participant_state).check_mail(
        GatewayMailCheckRequestV1(unread_only=unread_only, limit=limit, since=since)
    )
    result = payload.model_dump(mode="json")
    _write_json(_participant_artifact_path(layout, who, "last_check"), result)
    append_turn(
        layout=layout,
        state=state,
        payload={
            "operation": "check",
            "participant": who,
            "unread_only": unread_only,
            "message_count": result["message_count"],
            "unread_count": result["unread_count"],
        },
    )
    print(format_check_response(who=who, response=payload))
    return result


def watch_demo(
    *,
    demo_output_dir: Path,
    who: str,
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, Any]:
    """Poll unread mail until the unread set changes or the timeout expires."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    participant_state = _require_mapping(state["participants"][who], context=f"participants.{who}")
    client = _participant_client(participant_state)
    deadline = time.monotonic() + timeout_seconds
    last_refs: tuple[str, ...] = ()

    while time.monotonic() < deadline:
        response = client.check_mail(GatewayMailCheckRequestV1(unread_only=True, limit=50))
        current_refs = tuple(message.message_ref for message in response.messages)
        if current_refs and current_refs != last_refs:
            result = response.model_dump(mode="json")
            _write_json(_participant_artifact_path(layout, who, "last_watch"), result)
            append_turn(
                layout=layout,
                state=state,
                payload={
                    "operation": "watch",
                    "participant": who,
                    "message_count": result["message_count"],
                    "unread_count": result["unread_count"],
                },
            )
            print(format_check_response(who=who, response=response))
            return {
                "timed_out": False,
                "message_count": result["message_count"],
                "unread_count": result["unread_count"],
            }
        last_refs = current_refs
        time.sleep(interval_seconds)

    payload = {"timed_out": True, "participant": who, "timeout_seconds": timeout_seconds}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def inspect_demo(
    *,
    demo_output_dir: Path,
    who: str | None,
) -> dict[str, Any]:
    """Inspect current stack, gateway, notifier, and turn-history state."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    state = _load_state(layout.state_path)
    parameters = _load_parameters_from_state(state)
    selected = [who] if who is not None else sorted(parameters.participants)

    participants_payload: dict[str, Any] = {}
    for name in selected:
        participant_state = _require_mapping(
            state["participants"][name],
            context=f"participants.{name}",
        )
        client = _participant_client(participant_state)
        unread_payload = client.check_mail(GatewayMailCheckRequestV1(unread_only=True, limit=20))
        notifier_payload = client.get_mail_notifier().model_dump(mode="json")
        queue_path = (
            Path(
                _require_non_empty_string(
                    participant_state["gateway"]["gateway_root"],
                    context=f"{name}.gateway_root",
                )
            )
            / "queue.sqlite"
        )
        audit_summary = summarize_notifier_audit_records(
            read_gateway_notifier_audit_records(queue_path)
        )
        participants_payload[name] = {
            "account": participant_state["account"],
            "gateway": participant_state["gateway"],
            "mail_status": client.mail_status().model_dump(mode="json"),
            "notifier_status": notifier_payload,
            "unread_check": unread_payload.model_dump(mode="json"),
            "notifier_audit_summary": audit_summary,
        }

    payload = {
        "generated_at_utc": _utc_now_iso(),
        "demo_id": state["demo_id"],
        "stack": _require_mapping(state["stack"], context="stack"),
        "participants": participants_payload,
        "turn_history": _read_jsonl(layout.turns_path),
    }
    _write_json(layout.inspect_path, payload)
    print(format_inspect_summary(payload))
    return payload


def stop_demo(
    *,
    repo_root: Path,
    demo_output_dir: Path,
    cleanup_only: bool = False,
) -> dict[str, Any]:
    """Stop live sessions, gateway polling, CAO, and the local email stack."""

    layout = build_demo_layout(demo_output_dir=demo_output_dir)
    if not layout.state_path.exists():
        return {
            "stopped": False,
            "already_stopped": True,
            "message": f"demo state not found: {layout.state_path}",
        }

    state = _load_state(layout.state_path)
    stop_payload: dict[str, Any] = {"stopped": True, "participants": {}}

    for name, raw_participant in _require_mapping(
        state.get("participants"), context="participants"
    ).items():
        participant_state = _require_mapping(raw_participant, context=f"participants.{name}")
        participant_payload: dict[str, Any] = {}
        try:
            participant_payload["notifier_disable"] = _delete_notifier(participant_state)
        except Exception as exc:
            participant_payload["notifier_disable_error"] = str(exc)
        try:
            participant_payload["session_stop"] = _run_realm_controller_json(
                repo_root=repo_root,
                args=[
                    "stop-session",
                    "--agent-def-dir",
                    _require_non_empty_string(state.get("agent_def_dir"), context="agent_def_dir"),
                    "--agent-identity",
                    _require_non_empty_string(
                        participant_state["session"]["agent_identity"],
                        context=f"{name}.session.agent_identity",
                    ),
                ],
                stdout_path=_participant_artifact_path(layout, name, "session_stop"),
            )
        except Exception as exc:
            participant_payload["session_stop_error"] = str(exc)
        stop_payload["participants"][name] = participant_payload

    try:
        stop_payload["cao_stop"] = stop_demo_cao(
            repo_root=repo_root,
            demo_output_dir=demo_output_dir,
        )
    except Exception as exc:
        stop_payload["cao_stop_error"] = str(exc)

    try:
        parameters = _load_parameters_from_state(state)
        stack_config = load_stack_config(repo_root=repo_root, parameters=parameters)
        _run_command_capture(
            command=["./down.sh"],
            cwd=stack_config.env_file.parent,
            stdout_path=layout.stack_dir / "down.stdout.txt",
            stderr_path=layout.stack_dir / "down.stderr.txt",
            accepted_exit_codes={0},
        )
        stop_payload["stack_stop"] = {
            "env_file": str(stack_config.env_file.resolve()),
            "stopped_at_utc": _utc_now_iso(),
        }
    except Exception as exc:
        stop_payload["stack_stop_error"] = str(exc)

    state["stopped_at_utc"] = _utc_now_iso()
    _write_state(layout.state_path, state)
    _write_json(layout.demo_output_dir / _STOP_FILENAME, stop_payload)
    if cleanup_only:
        return stop_payload
    print(json.dumps(stop_payload, indent=2, sort_keys=True))
    return stop_payload


def parameters_to_payload(parameters: DemoParameters) -> dict[str, Any]:
    """Return a JSON-serializable form of the validated parameters."""

    return asdict(parameters)


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


def _cmd_validate_parameters(args: argparse.Namespace) -> int:
    """Validate the tracked demo parameters."""

    payload = parameters_to_payload(load_demo_parameters(args.parameters))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    """Run the `start` command."""

    payload = start_demo(
        repo_root=args.repo_root,
        pack_dir=args.pack_dir,
        demo_output_dir=args.demo_output_dir,
        parameters_path=args.parameters,
    )
    print(
        json.dumps(
            {
                "demo_output_dir": str(args.demo_output_dir.resolve()),
                "cypht_url": payload["stack"]["cypht_url"],
                "participants": {
                    name: {
                        "cypht_username": participant["account"]["cypht_username"],
                        "cypht_password": participant["account"]["cypht_password"],
                        "mailbox_address": participant["account"]["mailbox_address"],
                        "gateway_port": participant["gateway"]["gateway_port"],
                    }
                    for name, participant in payload["participants"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _cmd_send(args: argparse.Namespace) -> int:
    """Run the `send` command."""

    payload = send_demo(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        sender=args.sender,
        recipient=args.recipient,
        subject=args.subject,
        body_content=args.body_content,
        body_file=args.body_file,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_reply(args: argparse.Namespace) -> int:
    """Run the `reply` command."""

    payload = reply_demo(
        repo_root=args.repo_root,
        demo_output_dir=args.demo_output_dir,
        sender=args.sender,
        message_ref=args.message_ref,
        latest_unread=args.latest_unread,
        body_content=args.body_content,
        body_file=args.body_file,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Run the `check` command."""

    check_demo(
        demo_output_dir=args.demo_output_dir,
        who=args.who,
        unread_only=not args.all_messages,
        limit=args.limit,
        since=args.since,
    )
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    """Run the `watch` command."""

    watch_demo(
        demo_output_dir=args.demo_output_dir,
        who=args.who,
        timeout_seconds=args.timeout_seconds,
        interval_seconds=args.interval_seconds,
    )
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Run the `inspect` command."""

    inspect_demo(demo_output_dir=args.demo_output_dir, who=args.who)
    return 0


def _cmd_stop(args: argparse.Namespace) -> int:
    """Run the `stop` command."""

    stop_demo(repo_root=args.repo_root, demo_output_dir=args.demo_output_dir)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the demo helper."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_path = subparsers.add_parser("resolve-path", help="Resolve one optional repo path.")
    resolve_path.add_argument("--repo-root", type=Path, required=True)
    resolve_path.add_argument("--default-relative")
    resolve_path.add_argument("raw_path", nargs="?")
    resolve_path.set_defaults(func=_cmd_resolve_path)

    validate = subparsers.add_parser(
        "validate-parameters",
        help="Validate the tracked demo parameters.",
    )
    validate.add_argument("--parameters", type=Path, required=True)
    validate.set_defaults(func=_cmd_validate_parameters)

    for command_name, help_text, handler in (
        ("start", "Start the Stalwart stack, sessions, and gateways.", _cmd_start),
        ("send", "Send one message through a sender gateway.", _cmd_send),
        ("reply", "Reply through one sender gateway.", _cmd_reply),
        ("check", "Check one participant mailbox through the gateway.", _cmd_check),
        ("watch", "Poll unread gateway state until mail appears.", _cmd_watch),
        ("inspect", "Inspect stack, gateways, notifier state, and turn history.", _cmd_inspect),
        ("stop", "Stop the interactive demo.", _cmd_stop),
    ):
        command = subparsers.add_parser(command_name, help=help_text)
        command.add_argument("--repo-root", type=Path, required=True)
        command.add_argument("--pack-dir", type=Path, required=True)
        command.add_argument("--parameters", type=Path, required=True)
        command.add_argument("--demo-output-dir", type=Path, required=True)
        command.set_defaults(func=handler)

    send_parser = subparsers.choices["send"]
    send_parser.add_argument("--from", dest="sender", required=True, choices=["alice", "bob"])
    send_parser.add_argument("--to", dest="recipient", required=True)
    send_parser.add_argument("--subject", required=True)
    send_parser.add_argument("--body-content")
    send_parser.add_argument("--body-file")

    reply_parser = subparsers.choices["reply"]
    reply_parser.add_argument("--from", dest="sender", required=True, choices=["alice", "bob"])
    reply_target_group = reply_parser.add_mutually_exclusive_group(required=True)
    reply_target_group.add_argument("--message-ref")
    reply_target_group.add_argument("--latest-unread", action="store_true")
    reply_parser.add_argument("--body-content")
    reply_parser.add_argument("--body-file")

    check_parser = subparsers.choices["check"]
    check_parser.add_argument("--who", required=True, choices=["alice", "bob"])
    check_parser.add_argument("--all-messages", action="store_true")
    check_parser.add_argument("--limit", type=int)
    check_parser.add_argument("--since")

    watch_parser = subparsers.choices["watch"]
    watch_parser.add_argument("--who", required=True, choices=["alice", "bob"])
    watch_parser.add_argument("--timeout-seconds", type=int, default=30)
    watch_parser.add_argument("--interval-seconds", type=int, default=1)

    inspect_parser = subparsers.choices["inspect"]
    inspect_parser.add_argument("--who", choices=["alice", "bob"])

    return parser


def main() -> int:
    """Run the demo helper CLI."""

    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

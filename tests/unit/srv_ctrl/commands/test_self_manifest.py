"""Exercise verified self without loading launch definitions or activating runtimes."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller import self_manifest
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    SELF_TMUX_SESSION_ENV_VAR,
    SELF_TMUX_SOCKET_ENV_VAR,
)
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.service_runtime import ManagedServiceSessionState
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    parse_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import BackendKind, LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxesV1,
    RegistryMailboxSlotV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import publish_managed_agent_record
from houmao.execution.context import observed_local_binding
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from houmao.srv_ctrl.commands.agents import core
from houmao.srv_ctrl.commands.agents.self_identity import identity_from_manifest
from houmao.srv_ctrl.commands.main import cli


@pytest.fixture(autouse=True)
def _isolated_self_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep test resolution independent of the user's enclosing session and registry."""

    for key in (
        "TMUX",
        "TMUX_PANE",
        AGENT_MANIFEST_PATH_ENV_VAR,
        AGENT_DEF_DIR_ENV_VAR,
        HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
        SELF_TMUX_SOCKET_ENV_VAR,
        SELF_TMUX_SESSION_ENV_VAR,
    ):
        monkeypatch.delenv(key, raising=False)


def _publish_manifest(tmp_path: Path, backend: BackendKind) -> Path:
    """Publish a complete synthetic session with no role or gateway files."""

    socket = str(tmp_path / "owned.sock")
    root = tmp_path / "runtime"
    registry = tmp_path / "registry"
    binding = observed_local_binding(
        working_directory=tmp_path,
        runtime_root=root,
        registry_root=registry,
        tmux_socket=socket,
    )
    tool = "dsh" if backend == "dsh_web" else "kimi" if backend == "kimi_acp" else "claude"
    plan = LaunchPlan(
        backend=backend,
        tool=tool,
        executable=tool,
        args=[],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=root / "home",
        env={"PROVIDER_TOKEN": "private-fixture-value"},
        env_var_names=["PROVIDER_TOKEN"],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt", role_name="role", prompt="private-role"
        ),
        metadata={"tmux_socket_path": socket},
        execution_binding=binding,
        native_surface_kind=(
            "web"
            if backend == "dsh_web"
            else "terminal"
            if backend == "local_interactive"
            else None
        ),
    )
    backend_state: dict[str, Any] = {"tmux_window_name": "published-window", "tmux_pane_id": "%1"}
    if backend == "dsh_web":
        backend_state.update(
            origin="http://127.0.0.1:52731",
            browser_url="http://127.0.0.1:52731",
            native_pid=os.getpid(),
            native_birth_token=_dispatch_origin_birth_token(os.getpid()),
            web_identity={
                "protocol_version": 1,
                "agent_id": "agent-id",
                "runtime_session_id": "session-id",
                "generation": "generation-1",
                "host_incarnation": "host",
                "native_session_id": "native",
                "agent_incarnation": "body",
            },
        )
    if backend == "kimi_acp":
        backend_state.update(
            ManagedServiceSessionState(
                runtime_session_id="session-id",
                generation_id="generation-1",
                service_incarnation="provider-owner",
                native_session_id="native",
                working_directory=str(tmp_path),
                tmux_session_name="owner-session",
                tmux_pane_id="%1",
                tmux_window_id="@1",
            ).to_payload()
        )
    path = default_manifest_path(root, backend, "session-id")
    manifest = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "missing-brain.yaml",
            backend_state=backend_state,
            agent_name="agent-name",
            agent_id="agent-id",
            session_id="session-id",
            tmux_session_name="owner-session",
            agent_def_dir=tmp_path / "missing-definitions",
            registry_generation_id="generation-1",
        )
    )
    write_session_manifest(path, manifest)
    payload = parse_session_manifest_payload(manifest, source=str(path))
    now = datetime.now(UTC)
    record = ManagedAgentRegistryRecordV3(
        agent_name="agent-name",
        agent_id="agent-id",
        generation_id="generation-1",
        execution_binding=binding,
        lifecycle=RegistryLifecycleV1(
            state="active", relaunchable=True, state_updated_at=now.isoformat()
        ),
        identity=RegistryIdentityV1(backend=backend, tool=tool),
        mode=payload.mode,
        native_surface=payload.native_surface,
        runtime=RegistryRuntimeV1(manifest_path=str(path), session_root=str(path.parent)),
        terminal=RegistryTerminalV2(
            current_session_name="owner-session",
            last_session_name="owner-session",
            socket_path=socket,
        ),
        liveness=RegistryLivenessV1(
            published_at=now.isoformat(), lease_expires_at=(now + timedelta(hours=1)).isoformat()
        ),
        mailboxes=RegistryMailboxesV1(
            offline=RegistryMailboxSlotV1(revision="offline-empty", binding=None),
            online=RegistryMailboxSlotV1(revision="online-empty", binding=None),
        ),
        canonical_mail_identity=None,
    )
    publish_managed_agent_record(record, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str(registry)})
    return path


@pytest.mark.parametrize(
    ("backend", "mode", "tool"),
    [
        ("claude_headless", "headless", "claude"),
        ("kimi_acp", "service", "kimi"),
        ("local_interactive", "tui", "claude"),
        ("dsh_web", "web", "dsh"),
    ],
)
def test_identity_projection_preserves_current_fields(
    tmp_path: Path, backend: BackendKind, mode: str, tool: str
) -> None:
    """Project identity details consistently from each maintained mode's manifest."""

    path = _publish_manifest(tmp_path, backend)
    payload = parse_session_manifest_payload(json.loads(path.read_text()), source=str(path))
    identity = identity_from_manifest(path, payload)
    assert identity.model_dump() == {
        "tracked_agent_id": "agent-id",
        "transport": mode,
        "mode": mode,
        "backend": backend,
        "native_surface": None
        if payload.native_surface is None
        else payload.native_surface.model_dump(),
        "tool": tool,
        "session_name": "owner-session" if mode == "tui" else None,
        "terminal_id": None,
        "runtime_session_id": "session-id",
        "tmux_session_name": "owner-session",
        "tmux_window_name": "published-window",
        "manifest_path": str(path),
        "session_root": str(path.parent),
        "agent_name": "agent-name",
        "agent_id": "agent-id",
        "lifecycle_state": None,
        "management_kind": "local_lifecycle",
        "lifecycle_owner": "local",
        "external_agent_id": None,
        "remote_pair_api_base_url": None,
        "remote_agent_ref": None,
        "execution_context": payload.runtime.execution_binding.model_dump(),
        "execution_status": "available",
    }
    assert "private-fixture-value" not in identity.model_dump_json()
    assert "private-role" not in identity.model_dump_json()


@pytest.mark.parametrize("style", ["plain", "json"])
def test_self_identity_reads_only_runtime_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, style: str
) -> None:
    """Answer from a detached headless runtime with no definition directory or tmux context."""

    path = _publish_manifest(tmp_path, "claude_headless")
    monkeypatch.setenv(AGENT_MANIFEST_PATH_ENV_VAR, str(path))
    controller = Mock(side_effect=AssertionError("identity must not resume a controller"))
    monkeypatch.setattr(core, "resolve_current_session_managed_agent_target", controller)
    tmux = Mock(side_effect=AssertionError("headless identity must not probe tmux"))
    monkeypatch.setattr(self_manifest, "run_tmux", tmux)
    before = {file: file.read_bytes() for file in tmp_path.rglob("*") if file.is_file()}

    result = CliRunner().invoke(cli, [f"--print-{style}", "agents", "self", "identity"])

    assert result.exit_code == 0, result.output
    if style == "json":
        assert json.loads(result.output)["agent_id"] == "agent-id"
    else:
        assert "agent-id" in result.output and "agent_name" in result.output
    assert "private-fixture-value" not in result.output
    assert {file: file.read_bytes() for file in tmp_path.rglob("*") if file.is_file()} == before
    controller.assert_not_called()
    tmux.assert_not_called()


@pytest.mark.parametrize(
    ("damage", "diagnostic"),
    [
        ("absent", "current managed runtime"),
        ("malformed", "Invalid JSON"),
        ("stale", "stale registry generation"),
        ("foreign", "does not match the current managed runtime"),
        ("symlink", "confined runtime manifest"),
        ("foreign-root", "outside the owning runtime"),
    ],
)
def test_self_manifest_rejects_invalid_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str, diagnostic: str
) -> None:
    """Reject a stale generation and unsafe substitutes without using a fallback owner."""

    path = _publish_manifest(tmp_path, "claude_headless")
    if damage == "malformed":
        path.write_text("this is not JSON", encoding="utf-8")
    elif damage == "stale":
        payload = json.loads(path.read_text())
        payload["registry_generation_id"] = payload["runtime"]["registry_generation_id"] = "old"
        path.write_text(json.dumps(payload), encoding="utf-8")
    elif damage != "absent":
        alternate_root = (
            tmp_path / "foreign-runtime" if damage == "foreign-root" else tmp_path / "runtime"
        )
        substitute = default_manifest_path(alternate_root, "claude_headless", "copied")
        substitute.parent.mkdir(parents=True)
        if damage == "symlink":
            substitute.symlink_to(path)
        else:
            substitute.write_bytes(path.read_bytes())
        path = substitute
    if damage != "absent":
        monkeypatch.setenv(AGENT_MANIFEST_PATH_ENV_VAR, str(path))
    with pytest.raises(ValueError, match=diagnostic):
        self_manifest.resolve_self_manifest()


def test_detached_web_context_requires_the_exact_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate both the persisted tmux owner and its captured Web process."""

    path = _publish_manifest(tmp_path, "dsh_web")
    monkeypatch.setenv(SELF_TMUX_SESSION_ENV_VAR, "owner-session")
    socket = str(tmp_path / "owned.sock")
    monkeypatch.setenv(SELF_TMUX_SOCKET_ENV_VAR, socket)
    session_env = {AGENT_ID_ENV_VAR: "agent-id", AGENT_MANIFEST_PATH_ENV_VAR: str(path)}
    read_tmux = Mock(side_effect=lambda *, session_name, variable_name: session_env[variable_name])
    monkeypatch.setattr(self_manifest, "read_tmux_session_environment_value", read_tmux)

    assert self_manifest.resolve_self_manifest().path == path
    assert all(call.kwargs["session_name"] == "=owner-session" for call in read_tmux.call_args_list)

    monkeypatch.setenv(SELF_TMUX_SOCKET_ENV_VAR, str(tmp_path / "another.sock"))
    with pytest.raises(ValueError, match="owning tmux socket and session"):
        self_manifest.resolve_self_manifest()

    monkeypatch.setenv(SELF_TMUX_SOCKET_ENV_VAR, socket)
    monkeypatch.setattr(self_manifest, "_dispatch_origin_birth_token", lambda _: "reused-pid")
    with pytest.raises(ValueError, match="current native Web owner"):
        self_manifest.resolve_self_manifest()


def test_self_resolves_tmux_published_id_through_current_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolve an identifier-only tmux session through its owning registry."""

    path = _publish_manifest(tmp_path, "claude_headless")
    monkeypatch.setenv("TMUX", f"{tmp_path / 'owned.sock'},100,2")
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    tmux = Mock(return_value=CompletedProcess([], 0, stdout="owner-session\n"))
    monkeypatch.setattr(self_manifest, "run_tmux", tmux)
    session_env = {AGENT_ID_ENV_VAR: "agent-id", AGENT_MANIFEST_PATH_ENV_VAR: None}
    monkeypatch.setattr(
        self_manifest,
        "read_tmux_session_environment_value",
        lambda *, session_name, variable_name: session_env[variable_name],
    )

    assert self_manifest.resolve_self_manifest().path == path
    tmux.assert_called_once_with(["display-message", "-p", "-t", "$2:", "#{session_name}"])

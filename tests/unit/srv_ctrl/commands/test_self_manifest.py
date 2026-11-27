"""Exercise verified self without loading launch definitions or activating runtimes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller import hermes_self, self_manifest
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    SELF_TMUX_SESSION_ENV_VAR,
    SELF_TMUX_SOCKET_ENV_VAR,
)
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.hermes_native import (
    HermesDaemonIdentity,
    write_hermes_evidence,
)
from houmao.agents.realm_controller.backends.service_runtime import ManagedServiceSessionState
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import SessionManifestError
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
from houmao.agents.realm_controller.registry_storage import (
    _managed_agent_record_lock,
    load_managed_agent_record_by_agent_id,
    publish_managed_agent_record,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController
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
        "HERMES_HOME",
        AGENT_ID_ENV_VAR,
        AGENT_MANIFEST_PATH_ENV_VAR,
        AGENT_DEF_DIR_ENV_VAR,
        HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
        SELF_TMUX_SOCKET_ENV_VAR,
        SELF_TMUX_SESSION_ENV_VAR,
    ):
        monkeypatch.delenv(key, raising=False)


def _publish_manifest(
    tmp_path: Path,
    backend: BackendKind,
    *,
    generation: str = "generation-1",
    previous_generation: str | None = None,
    agent_id: str = "agent-id",
) -> Path:
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
    tool = (
        "hermes"
        if backend in hermes_self.HERMES_DETACHED_SELF_BACKENDS
        else "dsh"
        if backend == "dsh_web"
        else "kimi"
        if backend == "kimi_acp"
        else "claude"
    )
    plan = LaunchPlan(
        backend=backend,
        tool=tool,
        executable=tool,
        args=[],
        working_directory=tmp_path,
        home_env_var="HERMES_HOME" if tool == "hermes" else "CLAUDE_CONFIG_DIR",
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
            if backend in {"local_interactive", "hermes_tui"}
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
    if backend in {"kimi_acp", "hermes_service"}:
        service_state = ManagedServiceSessionState(
            runtime_session_id="session-id",
            generation_id=generation,
            service_incarnation="provider-owner",
            native_session_id="native",
            working_directory=str(tmp_path),
            tmux_session_name="owner-session",
            tmux_pane_id="%1",
            tmux_window_id="@1",
        ).to_payload()
        if backend == "hermes_service":
            backend_state = service_state
        else:
            backend_state.update(service_state)
    if backend == "hermes_tui":
        backend_state = {
            "session_name": "owner-session",
            "pane_id": "%1",
            "window_id": "@1",
            "tmux_session_id": "$2",
            "tmux_socket_path": socket,
            "hint_directory": str(root / "hint"),
            "native_session_id": "native",
            "home": str(plan.home_path),
            "working_directory": str(tmp_path),
        }
    path = default_manifest_path(root, backend, "session-id")
    manifest = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="role",
            brain_manifest_path=tmp_path / "missing-brain.yaml",
            backend_state=backend_state,
            agent_name="agent-name",
            agent_id=agent_id,
            session_id="session-id",
            tmux_session_name="owner-session",
            agent_def_dir=tmp_path / "missing-definitions",
            registry_generation_id=generation,
        )
    )
    write_session_manifest(path, manifest, expected_registry_generation_id=previous_generation)
    payload = parse_session_manifest_payload(manifest, source=str(path))
    now = datetime.now(UTC)
    record = ManagedAgentRegistryRecordV3(
        agent_name="agent-name",
        agent_id=agent_id,
        generation_id=generation,
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
    publish_managed_agent_record(
        record,
        env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str(registry)},
        expected_generation_id=previous_generation,
    )
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
    tmux = Mock(side_effect=AssertionError("headless identity must not dispatch tmux"))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setattr("houmao.execution.tmux.TmuxServer.checked_command", tmux)
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
    assert all(call.kwargs["session_name"] == "owner-session" for call in read_tmux.call_args_list)

    monkeypatch.setenv(SELF_TMUX_SOCKET_ENV_VAR, str(tmp_path / "another.sock"))
    with pytest.raises(ValueError, match="owning tmux socket and session"):
        self_manifest.resolve_self_manifest()

    monkeypatch.setenv(SELF_TMUX_SOCKET_ENV_VAR, socket)
    monkeypatch.setattr(self_manifest, "_dispatch_origin_birth_token", lambda _: "reused-pid")
    with pytest.raises(ValueError, match="current native Web owner"):
        self_manifest.resolve_self_manifest()


def _prepare_hermes_evidence(
    path: Path, pid: int
) -> tuple[
    SessionManifestPayloadV4,
    ManagedAgentRegistryRecordV3,
    hermes_self._RuntimeDaemonBinding,
    HermesDaemonIdentity,
]:
    """Record the verified native daemon and ACP binding used by lifecycle publication."""

    payload = parse_session_manifest_payload(json.loads(path.read_text()), source=str(path))
    home = Path(payload.launch_plan.home_selector.home_path)
    home.mkdir(mode=0o700, exist_ok=True)
    assert (execution := payload.runtime.execution_binding) is not None
    record = load_managed_agent_record_by_agent_id(
        payload.agent_id, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: execution.registry_root}
    )
    assert record is not None
    binding = hermes_self._runtime_daemon_binding(path, payload)
    if binding.service_incarnation is not None:
        write_hermes_evidence(
            binding.root / "hermes-acp-binding.json",
            {
                "native_session_id": binding.native_session_id,
                "generation_id": record.generation_id,
                "service_incarnation": binding.service_incarnation,
                "workspace": payload.working_directory,
                "protocol_version": 1,
                "binding_method": "session/new",
            },
        )
    birth = _dispatch_origin_birth_token(pid)
    assert birth is not None
    identity = HermesDaemonIdentity(
        home=home,
        pid=pid,
        birth_token=birth,
        instance_id="daemon-incarnation",
        authority_epoch=1,
        profile_id="native-profile",
        websocket_url="ws://127.0.0.1:1",
    )
    write_hermes_evidence(
        binding.root / "hermes-daemon.json",
        {
            "home": str(home),
            "workspace": payload.working_directory,
            "pid": pid,
            "birth_token": birth,
            "instance_id": identity.instance_id,
            "authority_epoch": identity.authority_epoch,
        },
    )
    return payload, record, binding, identity


@pytest.mark.parametrize("backend", ["hermes_service", "hermes_tui"])
@pytest.mark.parametrize("inherited_locator", [False, True])
def test_detached_hermes_tool_resolves_from_real_daemon_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    backend: BackendKind,
    inherited_locator: bool,
) -> None:
    """Resolve a real child of the saved process, including stock-started adoption."""

    path = _publish_manifest(tmp_path, backend)
    env = dict(os.environ)
    env["HERMES_HOME"] = str(tmp_path / "runtime" / "home")
    if inherited_locator:
        env[AGENT_MANIFEST_PATH_ENV_VAR] = str(path)
        env[AGENT_ID_ENV_VAR] = "agent-id"
        if backend == "hermes_service":
            env[SELF_TMUX_SESSION_ENV_VAR] = "supervisor-is-absent"
            env[SELF_TMUX_SOCKET_ENV_VAR] = str(tmp_path / "absent.sock")
    # Use a separate session for the CLI child to require a parent walk even when its SID differs.
    script = """
import subprocess, sys
sys.stdin.readline()
command = [sys.executable, '-c', 'from houmao.srv_ctrl.commands.main import main; '
           'raise SystemExit(main(["--print-json", "agents", "self", "identity"]))']
raise SystemExit(subprocess.run(command, start_new_session=True).returncode)
"""
    with subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as daemon:
        try:
            payload, record, binding, identity = _prepare_hermes_evidence(path, daemon.pid)
            native = SimpleNamespace(identity=identity)
            fake = SimpleNamespace(
                client=lambda: nullcontext(native),
                resume_session=Mock(),
                discover=lambda: identity,
            )
            monkeypatch.setattr(hermes_self.HermesDaemon, "from_launch_plan", lambda *_: fake)
            plan = LaunchPlan(
                backend=backend,
                tool="hermes",
                executable="hermes",
                args=[],
                working_directory=tmp_path,
                home_env_var="HERMES_HOME",
                home_path=binding.home,
                env={},
                env_var_names=[],
                role_injection=RoleInjectionPlan("native_home_system_prompt", "role", "prompt"),
                execution_binding=binding.execution_binding,
            )
            controller = RuntimeSessionController(
                plan,
                role_name="role",
                brain_manifest_path=tmp_path / "missing-brain.yaml",
                manifest_path=path,
                backend_session=Mock(),
                agent_identity=record.agent_name,
                agent_id=record.agent_id,
                registry_generation_id=record.generation_id,
                m_tmux_binding=payload.tmux,
            )
            assert controller.refresh_shared_registry_record() is not None
            assert hermes_self.require_live_hermes_daemon_authority(path, payload).pid == daemon.pid

            # A separate managed daemon under this UID cannot claim the first daemon's locator.
            other_path = _publish_manifest(
                tmp_path / "other-agent", backend, agent_id="other-agent"
            )
            other_payload, _, other_binding, other_daemon = _prepare_hermes_evidence(
                other_path, os.getpid()
            )
            hermes_self.publish_hermes_daemon_authority(other_path, other_payload, other_daemon)
            monkeypatch.setenv("HERMES_HOME", str(other_binding.home))
            assert self_manifest.resolve_self_manifest().path == other_path
            monkeypatch.setenv("HERMES_HOME", str(binding.home))
            with pytest.raises(ValueError, match="does not belong to the current managed Hermes"):
                self_manifest.resolve_self_manifest()

            output, error = daemon.communicate("run\n", timeout=10)
            assert daemon.returncode == 0, error
            result = json.loads(output)
            assert result["agent_id"] == "agent-id"
            assert result["backend"] == backend
            assert result["manifest_path"] == str(path)
            with pytest.raises(
                SessionManifestError, match="Current Hermes daemon authority is unavailable"
            ):
                hermes_self.require_live_hermes_daemon_authority(path, payload)
        finally:
            if daemon.poll() is None:
                daemon.kill()


@pytest.mark.parametrize(
    ("damage", "diagnostic"),
    [
        ("foreign-home", "locator does not match"),
        ("wrong-daemon", "Current Hermes daemon authority is unavailable"),
        ("reused-pid", "Current Hermes daemon authority is unavailable"),
        ("stale-generation", "locator does not match"),
        ("unsafe-evidence", "Current Hermes daemon authority is unavailable"),
        ("symlink-evidence", "Current Hermes daemon authority is unavailable"),
    ],
)
def test_detached_hermes_self_fails_closed_on_invalid_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str, diagnostic: str
) -> None:
    """Require process and generation evidence even when a caller claims an agent's locator."""

    path = _publish_manifest(tmp_path, "hermes_tui")
    payload, _, binding, identity = _prepare_hermes_evidence(path, os.getpid())
    hermes_self.publish_hermes_daemon_authority(path, payload, identity)
    monkeypatch.setenv("HERMES_HOME", str(binding.home))
    monkeypatch.setenv(AGENT_MANIFEST_PATH_ENV_VAR, str(path))
    tmux = Mock(side_effect=AssertionError("Detached Hermes identity must not probe tmux"))
    monkeypatch.setattr(self_manifest, "_self_tmux_session", tmux)
    assert self_manifest.resolve_self_manifest().path == path

    if damage == "foreign-home":
        home = tmp_path / "other-home"
        home.mkdir()
        locator = hermes_self.read_hermes_self_locator(binding.home)
        assert locator is not None
        write_hermes_evidence(home / binding.locator.name, locator.model_dump(mode="json"))
        monkeypatch.setenv("HERMES_HOME", str(home))
    elif damage == "wrong-daemon":
        daemon_path = binding.root / "hermes-daemon.json"
        candidate = json.loads(daemon_path.read_text())
        candidate["instance_id"] = "another-daemon"
        write_hermes_evidence(daemon_path, candidate)
    elif damage == "reused-pid":
        monkeypatch.setattr(hermes_self, "_dispatch_origin_birth_token", lambda _: "new-birth")
    elif damage == "stale-generation":
        _publish_manifest(
            tmp_path, "hermes_tui", generation="replacement", previous_generation="generation-1"
        )
    elif damage == "unsafe-evidence":
        binding.authority_path.chmod(0o644)
    else:
        evidence = tmp_path / "outside-evidence.json"
        binding.authority_path.rename(evidence)
        binding.authority_path.symlink_to(evidence)
    with pytest.raises(ValueError, match=diagnostic):
        self_manifest.resolve_self_manifest()
    tmux.assert_not_called()


def test_hermes_self_publication_fences_stale_writer_and_same_daemon_reuse(tmp_path: Path) -> None:
    """Reject old writers and prevent an old tool from carrying a daemon identity forward."""

    path = _publish_manifest(tmp_path, "hermes_tui")
    old_payload, _, old_binding, old_daemon = _prepare_hermes_evidence(path, os.getpid())
    hermes_self.publish_hermes_daemon_authority(path, old_payload, old_daemon)
    before = old_binding.locator.read_bytes()
    _publish_manifest(
        tmp_path, "hermes_tui", generation="replacement", previous_generation="generation-1"
    )
    new_payload, _, new_binding, _ = _prepare_hermes_evidence(path, os.getpid())

    with pytest.raises(
        SessionManifestError, match="Current Hermes daemon authority is unavailable"
    ):
        hermes_self.publish_hermes_daemon_authority(path, old_payload, old_daemon)
    with pytest.raises(
        SessionManifestError, match="Current Hermes daemon authority is unavailable"
    ):
        hermes_self.publish_hermes_daemon_authority(path, new_payload, old_daemon)
    assert old_binding.locator.read_bytes() == before
    assert not new_binding.authority_path.exists()


@pytest.mark.parametrize("contested", ["home", "registry"])
def test_prompt_daemon_refresh_refuses_contested_publication(
    tmp_path: Path, contested: str
) -> None:
    """A prompt cannot wait on concurrent lifecycle publication locks."""

    path = _publish_manifest(tmp_path, "hermes_tui")
    payload, record, binding, identity = _prepare_hermes_evidence(path, os.getpid())
    owner_lock = (
        hermes_self._home_locator_lock(binding.home, blocking=True)
        if contested == "home"
        else _managed_agent_record_lock(
            payload.agent_id,
            env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: binding.execution_binding.registry_root},
        )
    )
    with (
        owner_lock,
        pytest.raises(SessionManifestError, match="Current Hermes daemon authority is unavailable"),
    ):
        hermes_self.publish_verified_hermes_daemon_for_generation(
            path, record.generation_id, identity
        )
    assert not binding.locator.exists()
    hermes_self.publish_verified_hermes_daemon_for_generation(path, record.generation_id, identity)
    assert hermes_self.require_live_hermes_daemon_authority(path, payload).pid == os.getpid()


def test_hermes_service_requires_the_current_native_binding(tmp_path: Path) -> None:
    """Daemon liveness cannot substitute for the saved service incarnation and session."""

    path = _publish_manifest(tmp_path, "hermes_service")
    payload, _, binding, daemon = _prepare_hermes_evidence(path, os.getpid())
    hermes_self.publish_hermes_daemon_authority(path, payload, daemon)
    evidence = binding.root / "hermes-acp-binding.json"
    native = json.loads(evidence.read_text())
    native["service_incarnation"] = "old-incarnation"
    write_hermes_evidence(evidence, native)
    with pytest.raises(
        SessionManifestError, match="Current Hermes daemon authority is unavailable"
    ):
        hermes_self.require_live_hermes_daemon_authority(path, payload)


def test_hermes_self_rechecks_generation_after_process_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relaunch between the registry lookup and the final proof fences the caller."""

    path = _publish_manifest(tmp_path, "hermes_tui")
    payload, _, binding, daemon = _prepare_hermes_evidence(path, os.getpid())
    hermes_self.publish_hermes_daemon_authority(path, payload, daemon)
    monkeypatch.setenv("HERMES_HOME", str(binding.home))

    def replace_generation(_: object) -> None:
        """Change the runtime generation immediately after the first proof read."""

        _publish_manifest(
            tmp_path, "hermes_tui", generation="replacement", previous_generation="generation-1"
        )

    monkeypatch.setattr(self_manifest, "require_hermes_daemon_caller", replace_generation)
    with pytest.raises(ValueError, match="The managed Hermes owner changed"):
        self_manifest.resolve_self_manifest()


def test_self_resolves_tmux_published_id_through_current_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolve an identifier-only tmux session through its owning registry."""

    path = _publish_manifest(tmp_path, "claude_headless")
    monkeypatch.setenv("TMUX", f"{tmp_path / 'owned.sock'},100,2")
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    tmux = Mock(return_value=CompletedProcess([], 0, stdout="owner-session\n"))
    monkeypatch.setattr("houmao.execution.tmux.TmuxServer.checked_command", tmux)
    session_env = {AGENT_ID_ENV_VAR: "agent-id", AGENT_MANIFEST_PATH_ENV_VAR: None}
    monkeypatch.setattr(
        self_manifest,
        "read_tmux_session_environment_value",
        lambda *, session_name, variable_name: session_env[variable_name],
    )

    assert self_manifest.resolve_self_manifest().path == path
    tmux.assert_called_once_with(["display-message", "-p", "-t", "$2:", "#{session_name}"])

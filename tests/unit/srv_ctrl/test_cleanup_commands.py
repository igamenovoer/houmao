from __future__ import annotations
import click
import json
import sqlite3
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import houmao.srv_ctrl.commands.agents.gateway as gateway_commands
import houmao.srv_ctrl.commands.runtime_cleanup as runtime_cleanup
from houmao.agents.realm_controller import registry_storage
from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.errors import RetiredJoinedSessionError
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_session_root
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.mailbox import bootstrap_filesystem_mailbox
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    RegisterMailboxRequest,
    deregister_mailbox,
    register_mailbox,
)
from houmao.agents.realm_controller.registry_storage import RegistryCleanupAction
from houmao.execution.tmux import (
    TmuxCommandError,
    TmuxCommandResult,
    TmuxServer,
    current_tmux_socket_path,
    tmux_server_scope,
)
from houmao.project.overlay import bootstrap_project_overlay
from houmao.srv_ctrl.commands.main import cli


@pytest.fixture(autouse=True)
def _bind_absent_owner_socket() -> Iterator[None]:
    """Bind synthetic records to an isolated socket that never starts a server."""

    with TemporaryDirectory(prefix="hm-cleanup-") as directory:
        with tmux_server_scope(Path(directory) / "owner.sock"):
            yield


def _launch_plan(
    tmp_path: Path,
    *,
    runtime_root: Path,
    backend: str = "codex_headless",
    tool: str = "codex",
) -> LaunchPlan:
    home_path = (runtime_root / "homes" / "home-1").resolve()
    home_path.mkdir(parents=True, exist_ok=True)
    return LaunchPlan(
        backend=backend,
        tool=tool,
        executable=tool,
        args=[],
        working_directory=tmp_path.resolve(),
        home_env_var=f"{tool.upper()}_HOME",
        home_path=home_path,
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="r",
            prompt="role prompt",
        ),
    )


def _write_runtime_manifest(
    tmp_path: Path,
    *,
    runtime_root: Path | None = None,
    tmux_session_name: str = "join-sess",
    session_id: str = "session-1",
) -> Path:
    resolved_runtime_root = (runtime_root or (tmp_path / "runtime")).resolve()
    session_root = (resolved_runtime_root / "sessions" / "codex_headless" / session_id).resolve()
    session_root.mkdir(parents=True, exist_ok=True)
    manifest_path = (session_root / "manifest.json").resolve()
    brain_manifest_path = (resolved_runtime_root / "manifests" / "brain-1.yaml").resolve()
    brain_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    brain_manifest_path.write_text('{"schema_version": 2, "runtime": {}, "credentials": {}}\n')
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    memory_root = (tmp_path / ".houmao" / "memory" / "agents" / "agent-joined").resolve()
    pages_dir = (memory_root / "pages").resolve()
    pages_dir.mkdir(parents=True, exist_ok=True)
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=_launch_plan(tmp_path, runtime_root=resolved_runtime_root),
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            backend_state={
                "session_id": session_id,
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path.resolve()),
            },
            agent_name="joined-agent",
            agent_id="agent-joined",
            tmux_session_name=tmux_session_name,
            tmux_binding=SessionManifestTmuxSectionV1(
                session_name=tmux_session_name,
                socket_path=current_tmux_socket_path(),
            ),
            registry_generation_id="generation-1",
            session_id=session_id,
            agent_def_dir=agent_def_dir,
            memory_root=memory_root,
            memo_file=(memory_root / "houmao-memo.md").resolve(),
            pages_dir=pages_dir,
        )
    )
    write_session_manifest(manifest_path, payload)
    return manifest_path


def _write_retired_runtime_manifest(
    tmp_path: Path,
    *,
    tmux_session_name: str = "retired-session",
) -> Path:
    """Write saved adoption evidence without using the current manifest writer."""

    manifest_path = _write_runtime_manifest(tmp_path, tmux_session_name=tmux_session_name)
    payload = json.loads(manifest_path.read_text())
    payload["launch_plan"]["metadata"]["session_origin"] = "joined_tmux"
    payload["launch_plan"]["mailboxes"]["online"]["binding"] = {
        "transport": "stalwart",
        "credential_ref": "retired-mailbox",
    }
    manifest_path.write_text(json.dumps(payload))
    return manifest_path


def _registry_record(
    *,
    manifest_path: Path,
    session_root: Path | None,
    session_name: str = "join-sess",
    agent_id: str = "agent-joined",
    agent_name: str = "joined-agent",
    lifecycle_state: str = "stopped",
) -> ManagedAgentRegistryRecordV3:
    """Build one lifecycle-aware registry record for cleanup tests."""

    published_at = datetime.now(UTC)
    current_session_name = session_name if lifecycle_state == "active" else None
    return ManagedAgentRegistryRecordV3(
        agent_id=agent_id,
        agent_name=agent_name,
        generation_id="generation-1",
        lifecycle=RegistryLifecycleV1(
            state=lifecycle_state,
            relaunchable=lifecycle_state != "retired",
            state_updated_at=published_at.isoformat(timespec="seconds"),
            stopped_at=(
                published_at.isoformat(timespec="seconds")
                if lifecycle_state in {"stopped", "retired"}
                else None
            ),
            stop_reason="operator_stop" if lifecycle_state in {"stopped", "retired"} else None,
        ),
        mode="headless",
        identity=RegistryIdentityV1(backend="codex_headless", tool="codex"),
        runtime=RegistryRuntimeV1(
            manifest_path=str(manifest_path.resolve()),
            session_root=(str(session_root.resolve()) if session_root is not None else None),
            agent_def_dir="/tmp/agents",
        ),
        terminal=RegistryTerminalV2(
            current_session_name=current_session_name,
            last_session_name=session_name or "join-sess",
            socket_path=current_tmux_socket_path(),
        ),
        liveness=(
            RegistryLivenessV1(
                published_at=published_at.isoformat(timespec="seconds"),
                lease_expires_at=(published_at + timedelta(minutes=5)).isoformat(
                    timespec="seconds"
                ),
            )
            if lifecycle_state == "active"
            else None
        ),
        mailboxes={
            "offline": {"revision": "off-empty", "binding": None},
            "online": {"revision": "on-empty", "binding": None},
        },
        canonical_mail_identity=None,
    )


@pytest.mark.parametrize("selector", ["agent_id", "agent_name", "manifest_path", "session_root"])
@pytest.mark.parametrize("registry_present", [True, False])
@pytest.mark.parametrize("dry_run", [True, False])
def test_selected_cleanup_refuses_retired_adoption_before_any_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    selector: str,
    registry_present: bool,
    dry_run: bool,
) -> None:
    """Purge authority does not come from a manual adoption record or a degraded pane."""

    manifest = _write_retired_runtime_manifest(tmp_path)
    record = (
        _registry_record(
            manifest_path=manifest.with_name("stale-pointer.json"),
            session_root=manifest.parent,
            session_name="retired-session",
            lifecycle_state="active",
        )
        if registry_present
        else None
    )
    monkeypatch.setattr(
        runtime_cleanup, "_resolve_local_cleanup_registry_record", lambda **_: record
    )
    monkeypatch.setattr(runtime_cleanup, "_find_registry_record_for_session_root", lambda _: record)
    monkeypatch.setattr(runtime_cleanup, "_raise_if_external_cleanup_selector", lambda **_: None)
    monkeypatch.setattr(
        runtime_cleanup, "_resolve_effective_runtime_root", lambda _: tmp_path / "runtime"
    )

    def unexpected_effect(*args: object, **kwargs: object) -> None:
        pytest.fail("Retired cleanup attempted liveness probing or mutation")

    for name in (
        "_tmux_session_presence",
        "probe_tmux_backed_authority",
        "kill_tmux_session",
        "remove_path",
        "publish_managed_agent_record",
        "remove_managed_agent_record",
    ):
        monkeypatch.setattr(runtime_cleanup, name, unexpected_effect)

    saved = manifest.read_bytes()
    values = {
        "agent_id": "agent-joined",
        "agent_name": "joined-agent",
        "manifest_path": manifest,
        "session_root": manifest.parent,
    }
    with pytest.raises(RetiredJoinedSessionError, match="owning Houmao release"):
        runtime_cleanup.cleanup_managed_session(
            **{name: value if name == selector else None for name, value in values.items()},
            dry_run=dry_run,
            purge_registry=True,
        )
    assert manifest.read_bytes() == saved


@pytest.mark.parametrize("cleanup", ["logs", "mailbox"])
def test_selected_cleanup_preserves_retired_session_subdirectories(
    tmp_path: Path,
    cleanup: str,
) -> None:
    """Logs and mailbox cleanup refuse the retired selector before using it."""

    manifest = _write_retired_runtime_manifest(tmp_path)
    child = manifest.parent / "mailbox-secrets" / "credential.json"
    child.parent.mkdir()
    child.write_text("{}\n")
    command = {
        "logs": runtime_cleanup.cleanup_managed_session_logs,
        "mailbox": runtime_cleanup.cleanup_managed_session_mailbox,
    }[cleanup]
    with pytest.raises(RetiredJoinedSessionError):
        command(
            agent_id=None, agent_name=None, manifest_path=manifest, session_root=None, dry_run=False
        )
    assert child.read_text() == "{}\n"


@pytest.mark.parametrize("dry_run", [True, False])
def test_bulk_cleanup_preserves_retired_envelope_and_referenced_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dry_run: bool,
) -> None:
    """Retired references protect build and mailbox artifacts without blocking native cleanup."""

    runtime_root = tmp_path / "runtime"
    native_manifest = _write_runtime_manifest(
        tmp_path, session_id="native-stopped", tmux_session_name="native-stopped"
    )
    retired_manifest = _write_retired_runtime_manifest(tmp_path)
    retired_paths = gateway_paths_from_session_root(session_root=retired_manifest.parent)
    native_paths = gateway_paths_from_session_root(session_root=native_manifest.parent)
    for path in (retired_paths.diagnostic_log_path, native_paths.diagnostic_log_path):
        path.parent.mkdir(parents=True)
        path.write_text("log\n")
    credential_root = runtime_root / "mailbox-credentials" / "stalwart"
    credential_root.mkdir(parents=True)
    retired_credential = credential_root / "retired-mailbox.json"
    native_orphan_credential = credential_root / "orphan-mailbox.json"
    for path in (retired_credential, native_orphan_credential):
        path.write_text("{}\n")
    retired_home = runtime_root / "homes" / "home-1"
    native_orphan_home = runtime_root / "homes" / "orphan-home"
    native_orphan_home.mkdir()
    retired_brain_manifest = runtime_root / "manifests" / "brain-1.yaml"

    def tmux_presence(session_name: str | None, socket_path: str | None) -> bool:
        assert session_name == "native-stopped"
        return False

    monkeypatch.setattr(runtime_cleanup, "_tmux_session_presence", tmux_presence)
    action_key = "planned_actions" if dry_run else "applied_actions"
    for command, protected, disposable in (
        (
            runtime_cleanup.cleanup_runtime_logs,
            (retired_manifest.parent,),
            (native_paths.diagnostic_log_path,),
        ),
        (
            runtime_cleanup.cleanup_runtime_builds,
            (retired_home, retired_brain_manifest),
            (native_orphan_home,),
        ),
        (
            runtime_cleanup.cleanup_runtime_mailbox_credentials,
            (retired_credential,),
            (native_orphan_credential,),
        ),
        (
            runtime_cleanup.cleanup_runtime_sessions,
            (retired_manifest.parent,),
            (native_manifest.parent,),
        ),
    ):
        report = command(runtime_root=runtime_root, older_than_seconds=0, dry_run=dry_run)
        assert {action["path"] for action in report["preserved_actions"]} >= set(
            map(str, protected)
        )
        assert {action["path"] for action in report[action_key]} >= set(map(str, disposable))
        assert all(path.exists() for path in protected)
        assert all(path.exists() is dry_run for path in disposable)
    assert retired_manifest.is_file()
    assert retired_paths.diagnostic_log_path.read_text() == "log\n"


@pytest.mark.parametrize("dry_run", [True, False])
def test_registry_cleanup_preserves_expired_retired_adoption_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dry_run: bool,
) -> None:
    """An expired lease cannot authorize deletion of retired discovery pointers."""

    retired_manifest = _write_retired_runtime_manifest(tmp_path)
    retired_record = _registry_record(
        manifest_path=retired_manifest.with_name("stale-pointer.json"),
        session_root=retired_manifest.parent,
        session_name="retired-session",
        lifecycle_state="active",
    )
    native_record = _registry_record(
        manifest_path=tmp_path / "missing-native-manifest.json",
        session_root=None,
        agent_id="native-ordinary",
        agent_name="native-ordinary",
        lifecycle_state="active",
    )
    env = {"HOUMAO_GLOBAL_REGISTRY_DIR": str(tmp_path / "registry")}
    retired_path = registry_storage.record_path_for_agent_id(retired_record.agent_id, env=env)
    native_path = registry_storage.record_path_for_agent_id(native_record.agent_id, env=env)
    for path, record in ((retired_path, retired_record), (native_path, native_record)):
        path.parent.mkdir(parents=True)
        path.write_text(record.model_dump_json())
    saved = retired_path.read_bytes()

    def unexpected_probe(*args: object, **kwargs: object) -> None:
        pytest.fail("Expired registry cleanup probed tmux")

    monkeypatch.setattr(registry_storage, "_record_tmux_session_exists", unexpected_probe)
    report = registry_storage.cleanup_stale_managed_agent_records(
        env=env,
        now=datetime.now(UTC) + timedelta(days=1),
        dry_run=dry_run,
    )
    assert report.preserved_agent_ids == (retired_record.agent_id,)
    assert any("Manual tmux adoption is retired" in action.reason for action in report.actions)
    assert retired_path.read_bytes() == saved
    assert native_path.exists() is dry_run


def test_admin_cleanup_help_mentions_grouped_registry_and_runtime_commands() -> None:
    result = CliRunner().invoke(cli, ["admin", "cleanup", "--help"])

    assert result.exit_code == 0
    assert "registry" in result.output
    assert "runtime" in result.output


def test_admin_cleanup_runtime_help_mentions_runtime_subcommands() -> None:
    result = CliRunner().invoke(cli, ["admin", "cleanup", "runtime", "--help"])

    assert result.exit_code == 0
    assert "sessions" in result.output
    assert "builds" in result.output
    assert "logs" in result.output
    assert "mailbox-credentials" in result.output


def test_admin_cleanup_runtime_sessions_help_mentions_project_aware_runtime_root() -> None:
    result = CliRunner().invoke(cli, ["admin", "cleanup", "runtime", "sessions", "--help"])

    assert result.exit_code == 0
    assert "this command uses the active project runtime" in result.output
    assert "HOUMAO_GLOBAL_RUNTIME_DIR" in result.output


def test_admin_cleanup_registry_help_mentions_no_tmux_check() -> None:
    result = CliRunner().invoke(cli, ["admin", "cleanup", "registry", "--help"])

    assert result.exit_code == 0
    assert "--no-tmux-check" in result.output
    assert "--probe-local-tmux" not in result.output


def test_admin_help_does_not_list_cleanup_registry_alias() -> None:
    result = CliRunner().invoke(cli, ["admin", "--help"])

    assert result.exit_code == 0
    assert "cleanup" in result.output
    assert "cleanup-registry" not in result.output


def test_admin_cleanup_registry_alias_reports_migration_hint() -> None:
    result = CliRunner().invoke(cli, ["admin", "cleanup-registry"])

    assert result.exit_code == 2
    assert "No such command 'cleanup-registry'" in result.output
    assert "houmao-mgr admin cleanup registry" in result.output


def test_admin_cleanup_registry_probes_tmux_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}
    registry_root = (tmp_path / "registry").resolve()
    expected_action = RegistryCleanupAction(
        agent_id="live-agent",
        path=(registry_root / "live_agents" / "live-agent").resolve(),
        outcome="preserved",
        reason="local tmux liveness probe confirmed the owning session",
    )

    def _fake_cleanup(**kwargs: object) -> SimpleNamespace:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            registry_root=registry_root,
            removed_agent_ids=(),
            preserved_agent_ids=("live-agent",),
            failed_agent_ids=(),
            planned_agent_ids=(),
            actions=(expected_action,),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.admin.cleanup_stale_live_agent_records", _fake_cleanup
    )

    result = CliRunner().invoke(
        cli,
        ["--print-json", "admin", "cleanup", "registry", "--grace-seconds", "0"],
    )

    assert result.exit_code == 0, result.output
    assert captured_kwargs["probe_local_tmux"] is True
    payload = json.loads(result.output)
    assert payload["probe_local_tmux"] is True
    assert payload["resolution"]["probe_local_tmux"] is True


def test_admin_cleanup_registry_plain_output_lists_action_lines(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}
    registry_root = (tmp_path / "registry").resolve()
    planned_action = RegistryCleanupAction(
        agent_id="dead-agent",
        path=(registry_root / "live_agents" / "dead-agent").resolve(),
        outcome="planned",
        reason="local tmux liveness probe did not find the owning session",
    )
    preserved_action = RegistryCleanupAction(
        agent_id="live-agent",
        path=(registry_root / "live_agents" / "live-agent").resolve(),
        outcome="preserved",
        reason="local tmux liveness probe confirmed the owning session",
    )

    def _fake_cleanup(**kwargs: object) -> SimpleNamespace:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            registry_root=registry_root,
            removed_agent_ids=(),
            preserved_agent_ids=("live-agent",),
            failed_agent_ids=(),
            planned_agent_ids=("dead-agent",),
            actions=(planned_action, preserved_action),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.admin.cleanup_stale_live_agent_records", _fake_cleanup
    )

    result = CliRunner().invoke(
        cli,
        ["--print-plain", "admin", "cleanup", "registry", "--grace-seconds", "0", "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert captured_kwargs["probe_local_tmux"] is True
    assert "Cleanup Plan:" in result.output
    assert "Planned Actions (1):" in result.output
    assert str(planned_action.path) in result.output
    assert planned_action.reason in result.output
    assert "Preserved Actions (" in result.output
    assert str(preserved_action.path) in result.output
    assert preserved_action.reason in result.output
    assert "[1 items]" not in result.output
    assert "{...}" not in result.output


def test_agents_cleanup_help_mentions_session_logs_and_mailbox() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-joined", "cleanup", "--help"],
    )

    assert result.exit_code == 0
    assert "session" in result.output
    assert "logs" in result.output
    assert "mailbox" in result.output
    assert "local managed-session cleanup" in result.output.lower()


def test_top_level_mailbox_help_mentions_cleanup_command() -> None:
    result = CliRunner().invoke(cli, ["mailbox", "--help"])

    assert result.exit_code == 0
    assert "cleanup" in result.output


def test_current_session_cleanup_resolution_reuses_manifest_first_tmux_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)

    monkeypatch.setattr(gateway_commands, "_try_current_tmux_session_name", lambda: "join-sess")
    monkeypatch.setattr(
        gateway_commands,
        "_resolve_current_session_manifest",
        lambda *, session_name: (
            SimpleNamespace(manifest_path=manifest_path)
            if session_name == "join-sess"
            else (_ for _ in ()).throw(AssertionError("unexpected session name"))
        ),
    )

    target = runtime_cleanup.resolve_managed_session_cleanup_target(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=None,
    )

    assert target.manifest_path == manifest_path
    assert target.session_root == manifest_path.parent
    assert target.resolution == {"authority": "current_session", "value": "join-sess"}


def test_current_session_cleanup_resolution_falls_back_to_registry_session_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    stale_manifest_path = (session_root / "missing-manifest.json").resolve()
    record = _registry_record(
        manifest_path=stale_manifest_path,
        session_root=session_root,
    )

    monkeypatch.setattr(gateway_commands, "_try_current_tmux_session_name", lambda: "join-sess")
    monkeypatch.setattr(
        gateway_commands,
        "_resolve_current_session_manifest",
        lambda *, session_name: (
            (_ for _ in ()).throw(click.ClickException("stale manifest"))
            if session_name == "join-sess"
            else (_ for _ in ()).throw(AssertionError("unexpected session name"))
        ),
    )
    monkeypatch.setattr(
        gateway_commands,
        "_read_current_session_agent_id",
        lambda *, session_name: (
            "agent-joined"
            if session_name == "join-sess"
            else (_ for _ in ()).throw(AssertionError("unexpected session name"))
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )

    target = runtime_cleanup.resolve_managed_session_cleanup_target(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=None,
    )

    assert target.resolution == {"authority": "current_session", "value": "join-sess"}
    assert target.session_root == session_root
    assert target.payload is None
    assert target.parse_error is not None


def test_managed_session_cleanup_uses_registry_session_root_when_manifest_pointer_is_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    stale_manifest_path = (tmp_path / "gone" / "manifest.json").resolve()
    record = _registry_record(
        manifest_path=stale_manifest_path,
        session_root=session_root,
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )

    target = runtime_cleanup.resolve_managed_session_cleanup_target(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
    )

    assert target.resolution == {"authority": "agent_id", "value": "agent-joined"}
    assert target.session_root == session_root
    assert target.payload is None
    assert target.parse_error is not None


def test_managed_session_cleanup_prefers_registry_record_over_runtime_scan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    scan_manifest = _write_runtime_manifest(
        tmp_path, runtime_root=runtime_root, session_id="session-scan"
    )
    registry_manifest = _write_runtime_manifest(
        tmp_path,
        runtime_root=runtime_root,
        session_id="session-registry",
        tmux_session_name="join-sess-registry",
    )
    record = _registry_record(
        manifest_path=registry_manifest,
        session_root=registry_manifest.parent,
        session_name="join-sess-registry",
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_effective_runtime_root",
        lambda runtime_root: runtime_root or (tmp_path / "runtime").resolve(),
    )

    target = runtime_cleanup.resolve_managed_session_cleanup_target(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
    )

    assert target.session_root == registry_manifest.parent.resolve()
    assert target.manifest_path == registry_manifest.resolve()
    assert target.session_root != scan_manifest.parent.resolve()


def test_managed_session_cleanup_recovers_stopped_session_by_agent_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    manifest_path = _write_runtime_manifest(tmp_path, runtime_root=runtime_root)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: None,
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_effective_runtime_root",
        lambda runtime_root: (tmp_path / "runtime").resolve(),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=True,
    )

    assert payload["resolution"] == {"authority": "agent_id", "value": "agent-joined"}
    assert payload["scope"]["manifest_path"] == str(manifest_path)
    assert payload["scope"]["session_root"] == str(manifest_path.parent)
    assert {action["artifact_kind"] for action in payload["planned_actions"]} == {"session_root"}


def test_managed_session_cleanup_recovers_stopped_session_by_agent_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    manifest_path = _write_runtime_manifest(tmp_path, runtime_root=runtime_root)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: None,
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_effective_runtime_root",
        lambda runtime_root: (tmp_path / "runtime").resolve(),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name="joined-agent",
        manifest_path=None,
        session_root=None,
        dry_run=True,
    )

    assert payload["resolution"] == {"authority": "agent_name", "value": "joined-agent"}
    assert payload["scope"]["manifest_path"] == str(manifest_path)
    assert payload["scope"]["session_root"] == str(manifest_path.parent)


def test_managed_session_cleanup_unlinks_session_root_symlink_without_touching_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    external_runtime_root = (tmp_path / "external-runtime").resolve()
    manifest_path = _write_runtime_manifest(tmp_path, runtime_root=external_runtime_root)
    session_symlink = runtime_root / "sessions" / "codex_headless" / "session-1"
    session_symlink.parent.mkdir(parents=True, exist_ok=True)
    session_symlink.symlink_to(manifest_path.parent, target_is_directory=True)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_effective_runtime_root",
        lambda runtime_root: (tmp_path / "runtime").resolve(),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_symlink,
        dry_run=False,
    )

    assert payload["applied_actions"][0]["artifact_kind"] == "session_root"
    assert payload["applied_actions"][0]["path"] == str(session_symlink)
    assert not session_symlink.exists()
    assert manifest_path.parent.exists()


def test_managed_session_cleanup_registry_name_ambiguity_lists_lifecycle_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first_manifest = _write_runtime_manifest(tmp_path, session_id="session-1")
    second_manifest = _write_runtime_manifest(
        tmp_path,
        session_id="session-2",
        tmux_session_name="join-sess-2",
    )
    first_record = _registry_record(
        manifest_path=first_manifest,
        session_root=first_manifest.parent,
        agent_id="agent-1",
        agent_name="reviewer",
        lifecycle_state="stopped",
    )
    second_record = _registry_record(
        manifest_path=second_manifest,
        session_root=second_manifest.parent,
        agent_id="agent-2",
        agent_name="reviewer",
        session_name="join-sess-2",
        lifecycle_state="retired",
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "resolve_cleanup_managed_agent_records_by_name",
        lambda agent_name: (first_record, second_record),
    )

    with pytest.raises(runtime_cleanup.CleanupResolutionError) as exc_info:
        runtime_cleanup.resolve_managed_session_cleanup_target(
            agent_id=None,
            agent_name="reviewer",
            manifest_path=None,
            session_root=None,
        )

    message = str(exc_info.value)
    assert "ambiguous" in message
    assert "agent-1" in message
    assert "agent-2" in message
    assert "lifecycle_state=stopped" in message
    assert "lifecycle_state=retired" in message
    assert str(first_manifest) in message
    assert str(second_manifest.parent.resolve()) in message


def test_managed_session_cleanup_stopped_selector_ambiguity_lists_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    first_manifest = _write_runtime_manifest(
        tmp_path,
        runtime_root=runtime_root,
        session_id="session-1",
    )
    second_manifest = _write_runtime_manifest(
        tmp_path,
        runtime_root=runtime_root,
        session_id="session-2",
        tmux_session_name="join-sess-2",
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: None,
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_effective_runtime_root",
        lambda runtime_root: (tmp_path / "runtime").resolve(),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )

    with pytest.raises(runtime_cleanup.CleanupResolutionError) as exc_info:
        runtime_cleanup.resolve_managed_session_cleanup_target(
            agent_id=None,
            agent_name="joined-agent",
            manifest_path=None,
            session_root=None,
        )

    message = str(exc_info.value)
    assert "ambiguous" in message
    assert str(first_manifest) in message
    assert str(second_manifest) in message
    assert "session_root" in message


def test_managed_session_cleanup_stopped_selector_no_match_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    _write_runtime_manifest(tmp_path, runtime_root=runtime_root)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: None,
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_effective_runtime_root",
        lambda runtime_root: (tmp_path / "runtime").resolve(),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )

    with pytest.raises(runtime_cleanup.CleanupResolutionError) as exc_info:
        runtime_cleanup.resolve_managed_session_cleanup_target(
            agent_id="missing-agent",
            agent_name=None,
            manifest_path=None,
            session_root=None,
        )

    message = str(exc_info.value)
    assert "no matching stopped session" in message
    assert "--manifest-path" in message
    assert "--session-root" in message


def test_managed_session_cleanup_dry_run_supports_explicit_manifest_path_without_job_dir(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=manifest_path,
        session_root=None,
        dry_run=True,
    )

    planned_paths = {action["path"] for action in payload["planned_actions"]}
    assert str(manifest_path.parent.resolve()) in planned_paths
    assert not any(action["artifact_kind"] == "job_dir" for action in payload["planned_actions"])
    assert payload["resolution"]["authority"] == "manifest_path"


def test_managed_session_cleanup_preserves_agent_memory_dir(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    memory_root = (tmp_path / ".houmao" / "memory" / "agents" / "agent-joined").resolve()
    page_path = memory_root / "pages" / "notes.md"
    page_path.write_text("durable\n", encoding="utf-8")

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=manifest_path,
        session_root=None,
        dry_run=False,
    )

    assert memory_root.exists()
    assert page_path.is_file()
    affected_paths = {
        action["path"]
        for action in (
            payload["planned_actions"]
            + payload["applied_actions"]
            + payload["blocked_actions"]
            + payload["preserved_actions"]
        )
    }
    assert str(memory_root) not in affected_paths


def test_managed_session_cleanup_missing_manifest_removes_session_root_and_ignores_job_dir(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    job_dir = (tmp_path / ".houmao" / "jobs" / "session-1").resolve()
    manifest_path.unlink()

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_root,
        dry_run=False,
    )

    assert not session_root.exists()
    assert not job_dir.exists()
    assert {action["artifact_kind"] for action in payload["applied_actions"]} == {"session_root"}
    assert not any(action["artifact_kind"] == "job_dir" for action in payload["preserved_actions"])


def test_managed_session_cleanup_malformed_manifest_removes_session_root_and_ignores_job_dir(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    manifest_path.write_text("{not-json\n", encoding="utf-8")

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_root,
        dry_run=True,
    )

    assert {action["artifact_kind"] for action in payload["planned_actions"]} == {"session_root"}
    assert not any(action["artifact_kind"] == "job_dir" for action in payload["preserved_actions"])


def test_managed_session_cleanup_blocks_live_session_removal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    monkeypatch.setattr(
        runtime_cleanup,
        "tmux_session_exists",
        lambda *, session_name, allow_missing_server: session_name == "join-sess",
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=manifest_path,
        session_root=None,
        dry_run=False,
    )

    assert payload["applied_actions"] == []
    blocked_kinds = {action["artifact_kind"] for action in payload["blocked_actions"]}
    assert blocked_kinds == {"session_root"}


def test_managed_session_cleanup_retires_stopped_registry_record_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="stopped",
    )
    captured: dict[str, ManagedAgentRegistryRecordV3] = {}
    monkeypatch.setattr(runtime_cleanup, "load_managed_agent_record_by_agent_id", lambda _: record)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "publish_managed_agent_record",
        lambda updated_record, **kwargs: captured.setdefault("record", updated_record),
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=False,
    )

    assert not session_root.exists()
    assert {action["artifact_kind"] for action in payload["applied_actions"]} == {
        "managed_agent_registry_record",
        "session_root",
    }
    assert payload["summary"]["registry_lifecycle_action"] == "retire"
    assert captured["record"].lifecycle.state == "retired"
    assert captured["record"].lifecycle.relaunchable is False


def test_managed_session_cleanup_purges_registry_record_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="stopped",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(runtime_cleanup, "load_managed_agent_record_by_agent_id", lambda _: record)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "remove_managed_agent_record",
        lambda agent_id, generation_id=None: (
            captured.update({"agent_id": agent_id, "generation_id": generation_id}) or True
        ),
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=False,
        purge_registry=True,
    )

    assert not session_root.exists()
    assert payload["summary"]["registry_lifecycle_action"] == "purge"
    assert {action["proposed_action"] for action in payload["applied_actions"]} == {
        "remove",
        "purge",
    }
    assert captured == {"agent_id": "agent-joined", "generation_id": "generation-1"}


def test_managed_session_cleanup_dry_run_reports_registry_lifecycle_action(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="stopped",
    )
    monkeypatch.setattr(runtime_cleanup, "load_managed_agent_record_by_agent_id", lambda _: record)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "publish_managed_agent_record",
        lambda updated_record: (_ for _ in ()).throw(AssertionError("unexpected publish")),
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "remove_managed_agent_record",
        lambda agent_id, generation_id=None: (_ for _ in ()).throw(
            AssertionError("unexpected purge")
        ),
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=True,
    )

    assert session_root.exists()
    assert payload["summary"]["registry_lifecycle_action"] == "retire"
    assert {action["artifact_kind"] for action in payload["planned_actions"]} == {
        "managed_agent_registry_record",
        "session_root",
    }


def test_managed_session_cleanup_blocks_active_registry_record_even_without_live_tmux(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="active",
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "publish_managed_agent_record",
        lambda updated_record: (_ for _ in ()).throw(AssertionError("unexpected retire")),
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=False,
    )

    assert session_root.exists()
    assert payload["applied_actions"] == []
    assert {action["artifact_kind"] for action in payload["blocked_actions"]} == {"session_root"}
    assert payload["summary"]["registry_lifecycle_action"] is None


@pytest.mark.parametrize("dry_run", [True, False])
@pytest.mark.parametrize("generation_changes", [True, False])
def test_managed_session_cleanup_purge_registry_fences_stale_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dry_run: bool,
    generation_changes: bool,
) -> None:
    """Explicit purge requires verified absence and an unchanged owner generation."""

    from houmao.agents.realm_controller.backends.tmux_runtime import (
        TmuxBackedAuthorityHealth,
    )

    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="active",
    )
    current = record.model_copy(update={"generation_id": "next"}) if generation_changes else record
    monkeypatch.setattr(runtime_cleanup, "load_managed_agent_record_by_agent_id", lambda _: current)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "probe_tmux_backed_authority",
        lambda **kwargs: TmuxBackedAuthorityHealth(
            state="stale_missing_session",
            session_exists=False,
            primary_window_exists=False,
            primary_pane_exists=False,
        ),
    )
    cleanup_calls: list[str] = []
    monkeypatch.setattr(
        runtime_cleanup,
        "kill_tmux_session",
        lambda *, session_name: cleanup_calls.append(session_name),
    )
    purge_calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        runtime_cleanup,
        "remove_managed_agent_record",
        lambda agent_id, *, generation_id=None: (
            purge_calls.append((agent_id, generation_id)),
            True,
        )[1],
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=dry_run,
        purge_registry=True,
    )

    assert cleanup_calls == []
    assert session_root.exists() is (dry_run or generation_changes)
    if generation_changes:
        assert payload["planned_actions"] == []
        assert payload["applied_actions"] == []
        assert "generation" in payload["blocked_actions"][0]["details"]["inspection_error"]
    else:
        actions = payload["planned_actions" if dry_run else "applied_actions"]
        assert {row["artifact_kind"] for row in actions} == {
            "session_root",
            "managed_agent_registry_record",
        }
        assert payload["blocked_actions"] == []
    assert purge_calls == (
        [] if dry_run or generation_changes else [(record.agent_id, record.generation_id)]
    )


@pytest.mark.parametrize(
    ("dry_run", "kill_succeeds", "owned"),
    [(True, False, True), (False, True, True), (False, False, True), (False, True, False)],
)
def test_managed_session_cleanup_purge_registry_checks_degraded_remnant_teardown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    dry_run: bool,
    kill_succeeds: bool,
    owned: bool,
) -> None:
    """Purge a surviving degraded session only after checked teardown succeeds."""

    from houmao.agents.realm_controller.backends.tmux_runtime import (
        TmuxBackedAuthorityHealth,
    )

    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="active",
    )
    monkeypatch.setattr(runtime_cleanup, "load_managed_agent_record_by_agent_id", lambda _: record)

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: True
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "probe_tmux_backed_authority",
        lambda **kwargs: TmuxBackedAuthorityHealth(
            state="degraded_missing_primary",
            session_exists=True,
            primary_window_exists=False,
            primary_pane_exists=False,
            session_id="$7",
        ),
    )
    cleanup_calls: list[str] = []
    owner_socket = current_tmux_socket_path()

    def _read_marker(*, session_name: str, session_id: str, variable_name: str) -> str:
        assert session_name == "join-sess" and session_id == "$7"
        assert current_tmux_socket_path() == owner_socket
        return {
            "HOUMAO_AGENT_ID": record.agent_id if owned else "other-agent",
            "HOUMAO_MANIFEST_PATH": str(manifest_path),
        }[variable_name]

    monkeypatch.setattr(
        "houmao.agents.realm_controller.terminal_recovery.read_tmux_session_environment_value",
        _read_marker,
    )

    def _kill(*, session_name: str, session_id: str) -> None:
        assert current_tmux_socket_path() == owner_socket
        assert session_id == "$7"
        cleanup_calls.append(session_name)
        if not kill_succeeds:
            raise TmuxCommandError("tmux kill-session exited with status 23", returncode=23)

    monkeypatch.setattr(runtime_cleanup, "kill_tmux_session", _kill)
    purged: list[str] = []
    monkeypatch.setattr(
        runtime_cleanup,
        "remove_managed_agent_record",
        lambda agent_id, *, generation_id=None: purged.append(agent_id) or True,
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=dry_run,
        purge_registry=True,
    )

    if dry_run:
        assert manifest_path.exists()
        assert cleanup_calls == [] and purged == []
        assert {action["artifact_kind"] for action in payload["planned_actions"]} == {
            "session_root",
            "managed_agent_registry_record",
        }
        return
    if not owned:
        assert manifest_path.exists()
        assert cleanup_calls == [] and purged == []
        assert (
            "managed identity differs"
            in payload["blocked_actions"][0]["details"]["inspection_error"]
        )
        return
    assert cleanup_calls == ["join-sess"]
    if kill_succeeds:
        assert not session_root.exists()
        assert purged == [record.agent_id]
        applied_kinds = {action["artifact_kind"] for action in payload["applied_actions"]}
        assert applied_kinds == {"session_root", "managed_agent_registry_record"}
    else:
        assert session_root.exists()
        assert purged == []
        assert payload["applied_actions"] == []
        blocked = payload["blocked_actions"][0]
        assert "teardown" in blocked["reason"]
        assert "exited with status 23" in blocked["details"]["tmux_error"]


@pytest.mark.parametrize("lifecycle_state", ["active", "stopped"])
@pytest.mark.parametrize("failure", ["", "Permission denied", "timeout", "pane recheck"])
def test_managed_session_cleanup_preserves_artifacts_when_owner_probe_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lifecycle_state: str, failure: str
) -> None:
    """A failed owner query cannot authorize file or registry removal."""

    manifest_path = _write_runtime_manifest(tmp_path)
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=manifest_path.parent,
        lifecycle_state=lifecycle_state,
    )
    owner_socket = current_tmux_socket_path()
    assert owner_socket is not None
    calls: list[tuple[str, ...]] = []

    def _failed_probe(
        self: TmuxServer, args: Sequence[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        assert self.socket_path == owner_socket
        calls.append(tuple(args))
        if failure == "timeout":
            raise TimeoutExpired(args, 1)
        if failure == "pane recheck" and args[0] == "list-panes":
            return TmuxCommandResult(tuple(args), 1, "", "can't find session: join-sess")
        if failure == "pane recheck" and len(calls) > 1:
            return TmuxCommandResult(tuple(args), 0, "join-sess\n", "")
        return TmuxCommandResult(tuple(args), 23, "", failure)

    def _unexpected_mutation(*args: object, **kwargs: object) -> None:
        pytest.fail("An unavailable owner observation cannot authorize cleanup")

    monkeypatch.setattr(TmuxServer, "command", _failed_probe)
    monkeypatch.setattr(
        runtime_cleanup, "_resolve_local_cleanup_registry_record", lambda **_: record
    )
    monkeypatch.setattr(runtime_cleanup, "remove_managed_agent_record", _unexpected_mutation)
    monkeypatch.setattr(runtime_cleanup, "publish_managed_agent_record", _unexpected_mutation)

    with tmux_server_scope(Path(owner_socket).with_name("enclosing.sock")):
        payload = runtime_cleanup.cleanup_managed_session(
            agent_id=record.agent_id,
            agent_name=None,
            manifest_path=None,
            session_root=None,
            dry_run=False,
            purge_registry=True,
        )

    assert manifest_path.is_file()
    assert [call[0] for call in calls] == (
        ["list-panes", "list-sessions"]
        if lifecycle_state == "active" and failure == "pane recheck"
        else ["list-panes"]
        if lifecycle_state == "active"
        else ["list-sessions"]
    )
    assert payload["applied_actions"] == []
    assert "could not be verified" in payload["blocked_actions"][0]["reason"]


def test_managed_session_cleanup_without_purge_still_blocks_broken_active(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Without --purge-registry, broken active records still block cleanup."""

    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
        lifecycle_state="active",
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "_resolve_local_cleanup_registry_record",
        lambda *, agent_id, agent_name: (
            record if agent_id == "agent-joined" and agent_name is None else None
        ),
    )
    monkeypatch.setattr(
        runtime_cleanup, "tmux_session_exists", lambda *, session_name, allow_missing_server: False
    )
    probe_calls: list[str] = []
    monkeypatch.setattr(
        runtime_cleanup,
        "probe_tmux_backed_authority",
        lambda *, session_name: probe_calls.append(session_name),
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id="agent-joined",
        agent_name=None,
        manifest_path=None,
        session_root=None,
        dry_run=False,
        purge_registry=False,
    )

    assert probe_calls == []
    assert session_root.exists()
    assert {action["artifact_kind"] for action in payload["blocked_actions"]} == {"session_root"}


def test_managed_session_cleanup_explicit_session_root_blocks_live_removal_via_registry_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    manifest_path.unlink()
    record = _registry_record(
        manifest_path=manifest_path,
        session_root=session_root,
    )

    monkeypatch.setattr(
        runtime_cleanup,
        "_list_registry_records",
        lambda lifecycle_state="active": [record],
    )
    monkeypatch.setattr(
        runtime_cleanup,
        "tmux_session_exists",
        lambda *, session_name, allow_missing_server: session_name == "join-sess",
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_root,
        dry_run=False,
    )

    assert session_root.exists()
    assert payload["applied_actions"] == []
    assert {action["artifact_kind"] for action in payload["blocked_actions"]} == {"session_root"}


def test_agents_cleanup_session_command_forwards_purge_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.cleanup.cleanup_managed_session",
        lambda **kwargs: (
            captured.update(kwargs)
            or {
                "dry_run": True,
                "scope": {},
                "resolution": {},
                "planned_actions": [],
                "applied_actions": [],
                "blocked_actions": [],
                "preserved_actions": [],
                "summary": {},
            }
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "single",
            "--agent-id",
            "agent-joined",
            "cleanup",
            "session",
            "--dry-run",
            "--purge-registry",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agent_id"] == "agent-joined"
    assert captured["dry_run"] is True
    assert captured["purge_registry"] is True


def test_managed_session_logs_missing_manifest_still_cleans_remaining_artifacts(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    paths = gateway_paths_from_session_root(session_root=session_root)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = (paths.logs_dir / "gateway.log").resolve()
    log_path.write_text("log\n", encoding="utf-8")
    paths.pid_path.parent.mkdir(parents=True, exist_ok=True)
    paths.pid_path.write_text("123\n", encoding="utf-8")
    manifest_path.unlink()

    payload = runtime_cleanup.cleanup_managed_session_logs(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_root,
        dry_run=False,
    )

    assert not log_path.exists()
    assert not paths.pid_path.exists()
    assert {action["artifact_kind"] for action in payload["applied_actions"]} == {
        "runtime_log_file",
        "runtime_run_artifact",
    }


def test_managed_session_logs_cleanup_removes_gateway_diagnostics_but_preserves_state(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    paths = gateway_paths_from_session_root(session_root=session_root)
    paths.diagnostic_logs_dir.mkdir(parents=True, exist_ok=True)
    paths.diagnostic_log_path.write_text('{"event":"gateway.test"}\n', encoding="utf-8")
    paths.queue_path.parent.mkdir(parents=True, exist_ok=True)
    paths.queue_path.write_text("durable queue placeholder\n", encoding="utf-8")
    paths.state_path.write_text("{}\n", encoding="utf-8")
    paths.events_path.write_text("{}\n", encoding="utf-8")

    payload = runtime_cleanup.cleanup_managed_session_logs(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_root,
        dry_run=False,
    )

    assert not paths.diagnostic_log_path.exists()
    assert paths.queue_path.exists()
    assert paths.state_path.exists()
    assert paths.events_path.exists()
    assert any(
        action["artifact_kind"] == "runtime_log_file"
        and action["path"] == str(paths.diagnostic_log_path)
        for action in payload["applied_actions"]
    )
    assert {
        action["path"]
        for action in payload["preserved_actions"]
        if action["artifact_kind"] == "durable_gateway_state"
    } >= {str(paths.queue_path), str(paths.state_path), str(paths.events_path)}


def test_managed_session_mailbox_missing_manifest_removes_session_local_secrets(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    session_root = manifest_path.parent.resolve()
    secret_dir = (session_root / "mailbox-secrets").resolve()
    secret_dir.mkdir(parents=True, exist_ok=True)
    (secret_dir / "cred.json").write_text("{}\n", encoding="utf-8")
    manifest_path.unlink()

    payload = runtime_cleanup.cleanup_managed_session_mailbox(
        agent_id=None,
        agent_name=None,
        manifest_path=None,
        session_root=session_root,
        dry_run=False,
    )

    assert not secret_dir.exists()
    assert {action["artifact_kind"] for action in payload["applied_actions"]} == {
        "session_mailbox_secrets"
    }


def test_runtime_build_cleanup_dry_run_reports_unreferenced_manifest_home_pair(
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    home_path = (runtime_root / "homes" / "home-1").resolve()
    manifest_path = (runtime_root / "manifests" / "home-1.yaml").resolve()
    home_path.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "runtime": {"home_path": str(home_path)},
                "credentials": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = runtime_cleanup.cleanup_runtime_builds(
        runtime_root=runtime_root,
        older_than_seconds=0,
        dry_run=True,
    )

    planned_paths = {action["path"] for action in payload["planned_actions"]}
    assert planned_paths == {str(manifest_path), str(home_path)}


def test_cleanup_runtime_builds_defaults_to_project_overlay_runtime_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    monkeypatch.chdir(repo_root)

    payload = runtime_cleanup.cleanup_runtime_builds(
        runtime_root=None,
        older_than_seconds=0,
        dry_run=True,
    )

    assert payload["scope"]["runtime_root"] == str((repo_root / ".houmao" / "runtime").resolve())
    assert (
        payload["resolution"]["runtime_root_detail"]
        == "Selected the active project runtime root from the current project overlay."
    )
    assert (repo_root / ".houmao" / "houmao-config.toml").exists()


def test_cleanup_runtime_builds_explicit_runtime_root_wins_over_project_overlay_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    explicit_runtime_root = (tmp_path / "shared-runtime").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    explicit_runtime_root.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    monkeypatch.chdir(repo_root)

    payload = runtime_cleanup.cleanup_runtime_builds(
        runtime_root=explicit_runtime_root,
        older_than_seconds=0,
        dry_run=True,
    )

    assert payload["scope"]["runtime_root"] == str(explicit_runtime_root)
    assert (
        payload["resolution"]["runtime_root_detail"]
        == "Selected runtime root from the explicit `--runtime-root` override."
    )
    assert (repo_root / ".houmao" / "houmao-config.toml").exists()


def test_mailbox_cleanup_dry_run_reports_inactive_registration_and_preserves_messages(
    tmp_path: Path,
) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")
    register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address="HOUMAO-cleanup@agents.localhost",
            owner_principal_id="HOUMAO-cleanup",
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path("HOUMAO-cleanup@agents.localhost"),
        ),
    )
    deregister_mailbox(
        paths.root,
        DeregisterMailboxRequest(
            mode="deactivate",
            address="HOUMAO-cleanup@agents.localhost",
        ),
    )
    message_path = (paths.messages_dir / "keep.md").resolve()
    message_path.write_text("keep\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "mailbox",
            "cleanup",
            "--mailbox-root",
            str(paths.root),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert any(
        action["artifact_kind"] == "mailbox_registration" for action in payload["planned_actions"]
    )
    assert any(
        action["artifact_kind"] == "canonical_messages" for action in payload["preserved_actions"]
    )
    assert message_path.exists()


def test_mailbox_cleanup_removes_inactive_registration_and_keeps_messages(
    tmp_path: Path,
) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")
    address = "HOUMAO-cleanup@agents.localhost"
    register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=address,
            owner_principal_id="HOUMAO-cleanup",
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(address),
        ),
    )
    deregister_mailbox(
        paths.root,
        DeregisterMailboxRequest(
            mode="deactivate",
            address=address,
        ),
    )
    message_path = (paths.messages_dir / "keep.md").resolve()
    message_path.write_text("keep\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "mailbox",
            "cleanup",
            "--mailbox-root",
            str(paths.root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert message_path.exists()
    assert not paths.mailbox_entry_path(address).exists()
    with sqlite3.connect(paths.sqlite_path) as connection:
        remaining = connection.execute(
            "SELECT COUNT(*) FROM mailbox_registrations WHERE address = ?",
            (address,),
        ).fetchone()[0]
    assert remaining == 0


def test_mailbox_cleanup_plain_output_lists_action_lines(tmp_path: Path) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")
    address = "HOUMAO-cleanup@agents.localhost"
    registration = register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=address,
            owner_principal_id="HOUMAO-cleanup",
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(address),
        ),
    )
    deregister_mailbox(
        paths.root,
        DeregisterMailboxRequest(
            mode="deactivate",
            address=address,
        ),
    )
    (paths.messages_dir / "keep.md").write_text("keep\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "--print-plain",
            "mailbox",
            "cleanup",
            "--mailbox-root",
            str(paths.root),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Cleanup Plan:" in result.output
    assert "Planned Actions (1):" in result.output
    assert str(paths.root / "history" / registration["active_registration_id"]) in result.output
    assert "inactive mailbox registration is no longer active and is eligible for cleanup" in (
        result.output
    )
    assert "Preserved Actions (" in result.output
    assert str(paths.messages_dir.resolve()) in result.output
    assert "[1 items]" not in result.output
    assert "{...}" not in result.output


def test_mailbox_cleanup_fancy_output_lists_action_lines(tmp_path: Path) -> None:
    paths = bootstrap_filesystem_mailbox(tmp_path / "mailbox")
    address = "HOUMAO-cleanup@agents.localhost"
    register_mailbox(
        paths.root,
        RegisterMailboxRequest(
            mode="safe",
            address=address,
            owner_principal_id="HOUMAO-cleanup",
            mailbox_kind="in_root",
            mailbox_path=paths.mailbox_entry_path(address),
        ),
    )
    deregister_mailbox(
        paths.root,
        DeregisterMailboxRequest(
            mode="deactivate",
            address=address,
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-fancy",
            "mailbox",
            "cleanup",
            "--mailbox-root",
            str(paths.root),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Planned Actions" in result.output
    assert "mailbox_registration" in result.output
    assert "Preserved Actions" in result.output
    assert "canonical_messages" in result.output

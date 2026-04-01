from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import houmao.srv_ctrl.commands.agents.gateway as gateway_commands
import houmao.srv_ctrl.commands.runtime_cleanup as runtime_cleanup
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.mailbox import bootstrap_filesystem_mailbox
from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    RegisterMailboxRequest,
    deregister_mailbox,
    register_mailbox,
)
from houmao.agents.realm_controller.registry_storage import RegistryCleanupAction
from houmao.project.overlay import bootstrap_project_overlay
from houmao.srv_ctrl.commands.main import cli


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
        metadata={"session_origin": "joined_tmux"},
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
    job_dir = (tmp_path / ".houmao" / "jobs" / session_id).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
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
            session_id=session_id,
            agent_def_dir=agent_def_dir,
            job_dir=job_dir,
        )
    )
    write_session_manifest(manifest_path, payload)
    return manifest_path


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
    assert "Preserved Actions (1):" in result.output
    assert str(preserved_action.path) in result.output
    assert preserved_action.reason in result.output
    assert "[1 items]" not in result.output
    assert "{...}" not in result.output


def test_agents_cleanup_help_mentions_session_logs_and_mailbox() -> None:
    result = CliRunner().invoke(cli, ["agents", "cleanup", "--help"])

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


def test_managed_session_cleanup_dry_run_supports_explicit_manifest_path_and_job_dir(
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=manifest_path,
        session_root=None,
        include_job_dir=True,
        dry_run=True,
    )

    planned_paths = {action["path"] for action in payload["planned_actions"]}
    assert str(manifest_path.parent.resolve()) in planned_paths
    assert str((tmp_path / ".houmao" / "jobs" / "session-1").resolve()) in planned_paths
    assert payload["resolution"]["authority"] == "manifest_path"


def test_managed_session_cleanup_blocks_live_session_removal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = _write_runtime_manifest(tmp_path)
    monkeypatch.setattr(
        runtime_cleanup,
        "tmux_session_exists",
        lambda *, session_name: session_name == "join-sess",
    )

    payload = runtime_cleanup.cleanup_managed_session(
        agent_id=None,
        agent_name=None,
        manifest_path=manifest_path,
        session_root=None,
        include_job_dir=True,
        dry_run=False,
    )

    assert payload["applied_actions"] == []
    blocked_kinds = {action["artifact_kind"] for action in payload["blocked_actions"]}
    assert blocked_kinds == {"session_root", "job_dir"}


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
    assert str(paths.mailbox_entry_path(address)) in result.output
    assert "inactive mailbox registration is no longer active and is eligible for cleanup" in (
        result.output
    )
    assert "Preserved Actions (1):" in result.output
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

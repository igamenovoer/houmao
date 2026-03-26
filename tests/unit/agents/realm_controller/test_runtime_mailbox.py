from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.boundary_models import SessionManifestAgentLaunchAuthorityV1
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings
from houmao.mailbox.filesystem import MailboxBootstrapError
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_role(agent_def_dir: Path) -> None:
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt")


def _seed_brain_manifest(
    tmp_path: Path,
    *,
    tool: str = "codex",
    mailbox_block: str | None = None,
) -> Path:
    if tool == "claude":
        env_var = "ANTHROPIC_API_KEY"
        home_env_var = "CLAUDE_CONFIG_DIR"
    else:
        env_var = "OPENAI_API_KEY"
        home_env_var = "CODEX_HOME"

    env_file = tmp_path / "vars.env"
    env_file.write_text(f"{env_var}=secret\n", encoding="utf-8")
    manifest_path = tmp_path / f"{tool}-brain.yaml"

    lines = [
        "schema_version: 2",
        "inputs:",
        f"  tool: {tool}",
        "runtime:",
        f"  launch_executable: {tool}",
        "  launch_home_selector:",
        f"    env_var: {home_env_var}",
        f"    value: {tmp_path / 'home'}",
        "  launch_contract:",
        "    adapter_defaults:",
        "      args: []",
        "      tool_params: {}",
        "    requested_overrides:",
        "      recipe: null",
        "      direct: null",
        "    tool_metadata:",
        "      tool_params: {}",
        "credentials:",
        "  env_contract:",
        f"    source_file: {env_file}",
        "    allowlisted_env_vars:",
        f"      - {env_var}",
    ]
    if mailbox_block is not None:
        lines.extend(["mailbox:", *mailbox_block.splitlines()])

    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def test_start_runtime_session_bootstraps_and_persists_mailbox_binding(
    monkeypatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(
        tmp_path,
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: AGENTSYS-research",
                "  address: AGENTSYS-research@agents.localhost",
                "  filesystem_root: shared-mail",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_app_server",
        working_directory=tmp_path,
    )

    mailbox = controller.launch_plan.mailbox
    assert mailbox is not None
    assert mailbox.filesystem_root == (runtime_root / "shared-mail").resolve()
    assert (mailbox.filesystem_root / "protocol-version.txt").is_file()
    assert (mailbox.filesystem_root / "index.sqlite").is_file()
    assert (mailbox.filesystem_root / "rules/scripts/requirements.txt").is_file()
    assert (mailbox.filesystem_root / "mailboxes/AGENTSYS-research@agents.localhost/inbox").is_dir()
    assert (
        mailbox.filesystem_root
        / "mailboxes"
        / "AGENTSYS-research@agents.localhost"
        / "mailbox.sqlite"
    ).is_file()

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailbox"]["principal_id"] == "AGENTSYS-research"
    assert persisted["launch_plan"]["mailbox"]["filesystem_root"] == str(mailbox.filesystem_root)


def test_start_runtime_session_mailbox_root_override_wins(monkeypatch, tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(
        tmp_path,
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: AGENTSYS-research",
                "  address: AGENTSYS-research@agents.localhost",
                "  filesystem_root: shared-mail",
            ]
        ),
    )
    override_root = tmp_path / "override-mail"

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_app_server",
        working_directory=tmp_path,
        mailbox_root=override_root,
    )

    assert controller.launch_plan.mailbox is not None
    assert controller.launch_plan.mailbox.filesystem_root == override_root.resolve()
    assert (override_root / "protocol-version.txt").is_file()
    assert not (runtime_root / "shared-mail" / "protocol-version.txt").exists()


def test_start_runtime_session_bootstraps_second_mailbox_agent_on_initialized_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    runtime_root = tmp_path / "runtime"
    shared_root = tmp_path / "shared-mail"
    (tmp_path / "sender").mkdir(parents=True, exist_ok=True)
    (tmp_path / "receiver").mkdir(parents=True, exist_ok=True)
    sender_manifest = _seed_brain_manifest(
        tmp_path / "sender",
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: AGENTSYS-mailbox-sender",
                "  address: AGENTSYS-mailbox-sender@agents.localhost",
                f"  filesystem_root: {shared_root}",
            ]
        ),
    )
    receiver_manifest = _seed_brain_manifest(
        tmp_path / "receiver",
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: AGENTSYS-mailbox-receiver",
                "  address: AGENTSYS-mailbox-receiver@agents.localhost",
                f"  filesystem_root: {shared_root}",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    sender = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=sender_manifest,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_app_server",
        working_directory=tmp_path,
    )
    receiver = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=receiver_manifest,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_app_server",
        working_directory=tmp_path,
    )

    assert sender.launch_plan.mailbox is not None
    assert receiver.launch_plan.mailbox is not None
    assert sender.launch_plan.mailbox.filesystem_root == shared_root.resolve()
    assert receiver.launch_plan.mailbox.filesystem_root == shared_root.resolve()
    assert (
        shared_root / "mailboxes" / "AGENTSYS-mailbox-sender@agents.localhost" / "inbox"
    ).is_dir()
    assert (
        shared_root / "mailboxes" / "AGENTSYS-mailbox-receiver@agents.localhost" / "inbox"
    ).is_dir()


def test_resume_runtime_session_restores_persisted_mailbox_binding(
    monkeypatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    persisted_root = tmp_path / "persisted-mail"
    brain_manifest_path = _seed_brain_manifest(tmp_path, tool="claude")

    manifest = load_brain_manifest(brain_manifest_path)
    role = load_role_package(agent_def_dir, "r")
    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="claude_headless",
            working_directory=tmp_path,
            mailbox=FilesystemMailboxResolvedConfig(
                transport="filesystem",
                principal_id="AGENTSYS-research",
                address="AGENTSYS-research@agents.localhost",
                filesystem_root=persisted_root.resolve(),
                bindings_version="2026-03-12T05:00:00.000001Z",
            ),
        )
    )
    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            agent_name="AGENTSYS-research",
            agent_id=derive_agent_id_from_name("AGENTSYS-research"),
            tmux_session_name="AGENTSYS-research",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "AGENTSYS-research",
            },
        )
    )
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, Any] = {}

    def _fake_create_backend_session(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        _fake_create_backend_session,
    )

    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert controller.launch_plan.mailbox is not None
    assert controller.launch_plan.mailbox.filesystem_root == persisted_root.resolve()
    assert captured["launch_plan"].mailbox.filesystem_root == persisted_root.resolve()


def test_mailbox_env_bindings_remain_strict_for_unregistered_address_on_initialized_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    shared_root = tmp_path / "shared-mail"
    (tmp_path / "sender").mkdir(parents=True, exist_ok=True)
    sender_manifest = _seed_brain_manifest(
        tmp_path / "sender",
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: AGENTSYS-mailbox-sender",
                "  address: AGENTSYS-mailbox-sender@agents.localhost",
                f"  filesystem_root: {shared_root}",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=sender_manifest,
        role_name="r",
        runtime_root=tmp_path / "runtime",
        backend="codex_app_server",
        working_directory=tmp_path,
    )

    with pytest.raises(
        MailboxBootstrapError,
        match="no active mailbox registration exists",
    ):
        mailbox_env_bindings(
            FilesystemMailboxResolvedConfig(
                transport="filesystem",
                principal_id="AGENTSYS-mailbox-receiver",
                address="AGENTSYS-mailbox-receiver@agents.localhost",
                filesystem_root=shared_root.resolve(),
                bindings_version="2026-03-16T12:00:00Z",
            )
        )


def test_refresh_mailbox_bindings_updates_launch_plan_backend_and_manifest(tmp_path: Path) -> None:
    old_root = tmp_path / "mail-old"
    new_root = tmp_path / "mail-new"
    old_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=old_root.resolve(),
        bindings_version="2026-03-12T05:00:00.000001Z",
    )
    launch_plan = LaunchPlan(
        backend="codex_app_server",
        tool="codex",
        executable="codex",
        args=["app-server"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env=mailbox_env_bindings(old_mailbox),
        env_var_names=sorted(mailbox_env_bindings(old_mailbox).keys()),
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="r",
            prompt="Role prompt",
        ),
        metadata={},
        mailbox=old_mailbox,
    )
    manifest_path = tmp_path / "session.json"

    captured: dict[str, LaunchPlan] = {}

    class _FakeBackend:
        def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
            captured["launch_plan"] = launch_plan

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name="r",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        backend_session=_FakeBackend(),  # type: ignore[arg-type]
    )
    controller.persist_manifest()

    refreshed = controller.refresh_mailbox_bindings(filesystem_root=new_root)

    assert refreshed.filesystem_root == new_root.resolve()
    assert controller.launch_plan.mailbox == refreshed
    assert controller.launch_plan.env["AGENTSYS_MAILBOX_FS_ROOT"] == str(new_root.resolve())
    assert controller.launch_plan.env["AGENTSYS_MAILBOX_FS_MAILBOX_DIR"] == str(
        new_root.resolve() / "mailboxes" / "AGENTSYS-research@agents.localhost"
    )
    assert controller.launch_plan.env["AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH"] == str(
        new_root.resolve() / "mailboxes" / "AGENTSYS-research@agents.localhost" / "mailbox.sqlite"
    )
    assert captured["launch_plan"].mailbox == refreshed
    assert refreshed.bindings_version != old_mailbox.bindings_version
    assert (new_root / "protocol-version.txt").is_file()

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailbox"]["filesystem_root"] == str(new_root.resolve())


def _controller_for_mailbox_mutation(
    *,
    tmp_path: Path,
    backend: str,
    mailbox: FilesystemMailboxResolvedConfig | None,
    metadata: dict[str, object] | None = None,
) -> tuple[RuntimeSessionController, dict[str, LaunchPlan]]:
    """Build one runtime controller suitable for mailbox mutation tests."""

    env = mailbox_env_bindings(mailbox) if mailbox is not None else {}
    env_var_names = sorted(env.keys())
    launch_plan = LaunchPlan(
        backend=backend,
        tool="codex",
        executable="codex",
        args=["exec", "--json"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env=env,
        env_var_names=env_var_names,
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="r",
            prompt="Role prompt",
        ),
        metadata=dict(metadata or {}),
        mailbox=mailbox,
    )
    manifest_path = tmp_path / "session.json"
    captured: dict[str, LaunchPlan] = {}

    class _FakeBackend:
        def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
            captured["launch_plan"] = launch_plan

    controller = RuntimeSessionController(
        launch_plan=launch_plan,
        role_name="r",
        brain_manifest_path=tmp_path / "brain.yaml",
        manifest_path=manifest_path,
        backend_session=_FakeBackend(),  # type: ignore[arg-type]
        agent_identity="AGENTSYS-research",
        agent_id=derive_agent_id_from_name("AGENTSYS-research"),
        tmux_session_name="AGENTSYS-research",
    )
    controller.persist_manifest()
    return controller, captured


def test_register_filesystem_mailbox_updates_headless_launch_plan_and_manifest(
    tmp_path: Path,
) -> None:
    controller, captured = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="codex_headless",
        mailbox=None,
    )
    mailbox_root = tmp_path / "shared-mail"

    result = controller.register_filesystem_mailbox(
        mailbox_root=mailbox_root,
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
    )

    assert result.activation_state == "active"
    assert result.mailbox is not None
    assert controller.launch_plan.mailbox == result.mailbox
    assert controller.launch_plan.mailbox.filesystem_root == mailbox_root.resolve()
    assert controller.mailbox_activation_state() == "active"
    assert captured["launch_plan"].mailbox == result.mailbox
    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailbox"]["filesystem_root"] == str(mailbox_root.resolve())


def test_register_filesystem_mailbox_marks_local_interactive_session_pending_relaunch(
    tmp_path: Path,
) -> None:
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="local_interactive",
        mailbox=None,
    )

    result = controller.register_filesystem_mailbox(
        mailbox_root=tmp_path / "shared-mail",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
    )

    assert result.activation_state == "pending_relaunch"
    assert controller.launch_plan.mailbox is not None
    assert controller.mailbox_activation_state() == "pending_relaunch"
    assert controller.launch_plan.metadata["mailbox_live_enabled"] is False


def test_unregister_filesystem_mailbox_marks_local_interactive_session_pending_relaunch(
    tmp_path: Path,
) -> None:
    existing_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=(tmp_path / "shared-mail").resolve(),
        bindings_version="2026-03-26T00:00:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        existing_mailbox.filesystem_root,
        principal=MailboxPrincipal(
            principal_id=existing_mailbox.principal_id,
            address=existing_mailbox.address,
        ),
    )
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="local_interactive",
        mailbox=existing_mailbox,
    )

    result = controller.unregister_filesystem_mailbox()

    assert result.activation_state == "pending_relaunch"
    assert controller.launch_plan.mailbox is None
    assert controller.mailbox_activation_state() == "pending_relaunch"
    assert controller.launch_plan.metadata["mailbox_live_enabled"] is True
    assert (
        controller.launch_plan.metadata["mailbox_live_bindings_version"]
        == existing_mailbox.bindings_version
    )


def test_relaunch_syncs_pending_local_interactive_mailbox_activation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    existing_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root=(tmp_path / "shared-mail").resolve(),
        bindings_version="2026-03-26T00:00:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        existing_mailbox.filesystem_root,
        principal=MailboxPrincipal(
            principal_id=existing_mailbox.principal_id,
            address=existing_mailbox.address,
        ),
    )
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="local_interactive",
        mailbox=existing_mailbox,
        metadata={
            "mailbox_live_enabled": False,
        },
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._backend_requires_provider_start_relaunch",
        lambda backend: False,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._relaunch_backend_session",
        lambda controller: SimpleNamespace(status="ok", action="relaunch", detail="relaunched"),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_pair_launch_registration",
        lambda controller: None,
    )

    result = controller.relaunch()

    assert result.status == "ok"
    assert controller.mailbox_activation_state() == "active"
    assert controller.launch_plan.metadata["mailbox_live_enabled"] is True
    assert (
        controller.launch_plan.metadata["mailbox_live_bindings_version"]
        == existing_mailbox.bindings_version
    )


def test_late_mailbox_registration_rejects_joined_sessions_without_relaunch_posture(
    tmp_path: Path,
) -> None:
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="local_interactive",
        mailbox=None,
    )
    controller.agent_launch_authority = SessionManifestAgentLaunchAuthorityV1(
        backend="local_interactive",
        tool="codex",
        tmux_session_name="AGENTSYS-research",
        working_directory=str(tmp_path),
        session_origin="joined_tmux",
        posture_kind="unavailable",
    )

    assert controller.mailbox_activation_state() == "unsupported_joined_session"
    with pytest.raises(SessionManifestError, match="Late mailbox registration is unavailable"):
        controller.register_filesystem_mailbox(
            mailbox_root=tmp_path / "shared-mail",
            principal_id="AGENTSYS-research",
            address="AGENTSYS-research@agents.localhost",
        )

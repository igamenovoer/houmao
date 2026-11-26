from __future__ import annotations

import json
from dataclasses import replace

import yaml
import shutil
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxesResolvedConfig,
    MailboxSlotConfig,
)
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings
from houmao.mailbox.filesystem import MailboxBootstrapError
from houmao.mailbox import (
    MailboxPrincipal,
    bootstrap_filesystem_mailbox,
    load_active_mailbox_registration,
)
from houmao.mailbox.registry_config import associate_registry_store
from houmao.owned_paths import resolve_registry_root
from houmao.project.overlay import resolve_project_aware_mailbox_root
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from houmao.project.overlay import bootstrap_project_overlay


@pytest.fixture(autouse=True)
def _isolate_and_cleanup_shared_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[None]:
    """Keep runtime mailbox tests from publishing records into the user registry."""
    registry_root = (tmp_path / "registry").resolve()
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    yield
    shutil.rmtree(registry_root, ignore_errors=True)


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
    env_records: dict[str, str] | None = None,
) -> Path:
    if tool == "claude":
        env_var = "ANTHROPIC_API_KEY"
        home_env_var = "CLAUDE_CONFIG_DIR"
    else:
        env_var = "OPENAI_API_KEY"
        home_env_var = "CODEX_HOME"

    home_path = tmp_path / "home"
    home_path.mkdir(parents=True, exist_ok=True)
    if tool == "codex":
        (home_path / "auth.json").write_text('{"session_id":"test-session"}\n', encoding="utf-8")
    env_file = tmp_path / "vars.env"
    env_file.write_text(f"{env_var}=secret\n", encoding="utf-8")
    manifest_path = tmp_path / f"{tool}-brain.yaml"

    lines = [
        "schema_version: 3",
        "inputs:",
        f"  tool: {tool}",
        "  skills: []",
        "  setup: default",
        "  auth: default",
        "  adapter_path: /tmp/tool-adapter.yaml",
        "  preset_path: null",
        "runtime:",
        f"  runtime_root: {tmp_path}",
        "  home_id: test-home",
        f"  home_path: {home_path}",
        f"  launch_helper: {home_path / 'launch.sh'}",
        f"  launch_executable: {tool}",
        "  launch_home_selector:",
        f"    env_var: {home_env_var}",
        f"    value: {home_path}",
        "  launch_contract:",
        "    adapter_defaults:",
        "      args: []",
        "      tool_params: {}",
        "    requested_overrides:",
        "      preset: null",
        "      direct: null",
        "    tool_metadata:",
        "      tool_params: {}",
        "    construction_provenance:",
        "      adapter_path: /tmp/tool-adapter.yaml",
        "      preset_path: null",
        "      preset_overrides_present: false",
        "      direct_overrides_present: false",
    ]
    if env_records:
        lines.extend(["    env_records:"])
        for name, value in env_records.items():
            lines.append(f"      {name}: {json.dumps(value)}")
    lines.extend(
        [
            "credentials:",
            f"  auth_path: {tmp_path / 'auth'}",
            "  projected_files: []",
            "  env_contract:",
            f"    source_file: {env_file}",
            "    allowlisted_env_vars:",
            f"      - {env_var}",
        ]
    )
    if mailbox_block is not None:
        declaration = yaml.safe_load(mailbox_block)
        declaration.pop("principal_id", None)
        lines.extend(
            yaml.safe_dump(
                {"mailboxes": {"offline": declaration, "online": None}}, sort_keys=False
            ).splitlines()
        )

    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest_path


def _offline_binding(**kwargs: Any) -> FilesystemMailboxResolvedConfig:
    """Construct explicit fixture ownership under deterministic caller-selected identity."""

    owner = derive_agent_id_from_name(kwargs.pop("principal_id"))
    return FilesystemMailboxResolvedConfig(
        agent_id=owner, principal_id=owner, binding_id="unprepared", **kwargs
    )


def _offline_mailboxes(binding: FilesystemMailboxResolvedConfig | None) -> MailboxesResolvedConfig:
    """Use confirmed registration scope when constructing an existing-agent fixture."""

    if binding is None:
        return MailboxesResolvedConfig()
    associate_registry_store(resolve_registry_root(), binding.filesystem_root)
    bootstrap_filesystem_mailbox(
        binding.filesystem_root,
        principal=MailboxPrincipal(principal_id=binding.agent_id, address=binding.address),
    )
    registration = load_active_mailbox_registration(
        binding.filesystem_root, address=binding.address
    )
    binding = replace(
        binding, binding_id=registration.registration_id, registry_root=resolve_registry_root()
    )
    return MailboxesResolvedConfig(
        offline=MailboxSlotConfig(revision=binding.bindings_version, binding=binding)
    )


def _start_configured_session(**kwargs: Any) -> RuntimeSessionController:
    """Initialize the isolated selected registry before exercising the real launch path."""

    brain = load_brain_manifest(kwargs["brain_manifest_path"])
    declaration = brain.get("mailboxes", {}).get("offline")
    root = kwargs.get("mailbox_root")
    if root is None and declaration is not None:
        root = Path(declaration["filesystem_root"])
        if not root.is_absolute():
            root = kwargs["runtime_root"] / root
    if root is not None:
        associate_registry_store(resolve_registry_root(), root)
    return start_runtime_session(**kwargs)


def _join_configured_mailbox(controller: RuntimeSessionController, **kwargs: Any) -> Any:
    """Explicitly configure one local authority before exercising late attachment."""

    root = kwargs.get("mailbox_root")
    if root is None:
        root = resolve_project_aware_mailbox_root(cwd=controller.launch_plan.working_directory)
    associate_registry_store(resolve_registry_root(), root)
    if "principal_id" in kwargs:
        kwargs["principal_id"] = controller.agent_id
    return controller.register_filesystem_mailbox(**kwargs)


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
                "  principal_id: HOUMAO-research",
                "  address: HOUMAO-research@agents.localhost",
                "  filesystem_root: shared-mail",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    controller = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
    )

    mailbox = controller.launch_plan.mailboxes.offline.binding
    assert mailbox is not None
    assert mailbox.filesystem_root == (runtime_root / "shared-mail").resolve()
    assert (mailbox.filesystem_root / "protocol-version.txt").is_file()
    assert (mailbox.filesystem_root / "index.sqlite").is_file()
    assert (mailbox.filesystem_root / "rules/scripts/requirements.txt").is_file()
    assert (mailbox.filesystem_root / "mailboxes/HOUMAO-research@agents.localhost/inbox").is_dir()
    assert (
        mailbox.filesystem_root
        / "mailboxes"
        / "HOUMAO-research@agents.localhost"
        / "mailbox.sqlite"
    ).is_file()

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert (
        persisted["launch_plan"]["mailboxes"]["offline"]["binding"]["principal_id"]
        == controller.agent_id
    )
    assert persisted["launch_plan"]["mailboxes"]["offline"]["binding"]["filesystem_root"] == str(
        mailbox.filesystem_root
    )


def test_start_runtime_session_mailbox_root_override_wins(monkeypatch, tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(
        tmp_path,
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: HOUMAO-research",
                "  address: HOUMAO-research@agents.localhost",
                "  filesystem_root: shared-mail",
            ]
        ),
    )
    override_root = tmp_path / "override-mail"

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    controller = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
        mailbox_root=override_root,
    )

    assert controller.launch_plan.mailboxes.offline.binding is not None
    assert (
        controller.launch_plan.mailboxes.offline.binding.filesystem_root == override_root.resolve()
    )
    assert (override_root / "protocol-version.txt").is_file()
    assert not (runtime_root / "shared-mail" / "protocol-version.txt").exists()


def test_start_and_resume_runtime_session_preserve_symlink_mailbox_binding(
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
                "  principal_id: HOUMAO-research",
                "  address: HOUMAO-research@agents.localhost",
                "  filesystem_root: shared-mail",
            ]
        ),
    )
    private_mailbox_dir = (tmp_path / "private-mailboxes" / "repo-research-1").resolve()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )
    # tmux-backed backends publish gateway capability on resume; the tmux
    # environment write is unrelated to mailbox binding preservation.
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.tmux_session_exists_shared",
        lambda **_: False,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **_: None,
    )

    controller = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
        mailbox_account_dir=private_mailbox_dir,
    )

    mailbox = controller.launch_plan.mailboxes.offline.binding
    assert isinstance(mailbox, FilesystemMailboxResolvedConfig)
    assert mailbox.filesystem_root == (runtime_root / "shared-mail").resolve()
    assert mailbox.mailbox_kind == "symlink"
    assert mailbox.mailbox_path == private_mailbox_dir
    assert (mailbox.filesystem_root / "mailboxes" / mailbox.address).is_symlink()
    assert (
        mailbox.filesystem_root / "mailboxes" / mailbox.address
    ).resolve() == private_mailbox_dir
    assert "HOUMAO_MAILBOX_FS_MAILBOX_DIR" not in controller.launch_plan.env

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailboxes"]["offline"]["binding"]["mailbox_kind"] == "symlink"
    assert persisted["launch_plan"]["mailboxes"]["offline"]["binding"]["mailbox_path"] == str(
        private_mailbox_dir
    )

    captured: dict[str, Any] = {}

    def _fake_resume_backend_session(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        _fake_resume_backend_session,
    )
    resumed = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=controller.manifest_path,
    )

    assert isinstance(
        resumed.launch_plan.mailboxes.offline.binding, FilesystemMailboxResolvedConfig
    )
    assert resumed.launch_plan.mailboxes.offline.binding.mailbox_kind == "symlink"
    assert resumed.launch_plan.mailboxes.offline.binding.mailbox_path == private_mailbox_dir
    assert "HOUMAO_MAILBOX_FS_MAILBOX_DIR" not in resumed.launch_plan.env
    assert isinstance(
        captured["launch_plan"].mailboxes.offline.binding, FilesystemMailboxResolvedConfig
    )
    assert captured["launch_plan"].mailboxes.offline.binding.mailbox_kind == "symlink"
    assert captured["launch_plan"].mailboxes.offline.binding.mailbox_path == private_mailbox_dir


def test_start_runtime_session_rejects_private_mailbox_inside_shared_root(
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
                "  principal_id: HOUMAO-research",
                "  address: HOUMAO-research@agents.localhost",
                "  filesystem_root: shared-mail",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    with pytest.raises(
        SessionManifestError,
        match="outside the shared mailbox root",
    ):
        _start_configured_session(
            agent_def_dir=agent_def_dir,
            brain_manifest_path=brain_manifest_path,
            role_name="r",
            runtime_root=runtime_root,
            backend="codex_headless",
            working_directory=tmp_path,
            mailbox_account_dir=(runtime_root / "shared-mail" / "private" / "repo-research-1"),
        )


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
                "  principal_id: HOUMAO-mailbox-sender",
                "  address: HOUMAO-mailbox-sender@agents.localhost",
                f"  filesystem_root: {shared_root}",
            ]
        ),
    )
    receiver_manifest = _seed_brain_manifest(
        tmp_path / "receiver",
        mailbox_block="\n".join(
            [
                "  transport: filesystem",
                "  principal_id: HOUMAO-mailbox-receiver",
                "  address: HOUMAO-mailbox-receiver@agents.localhost",
                f"  filesystem_root: {shared_root}",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    sender = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=sender_manifest,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
    )
    receiver = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=receiver_manifest,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
    )

    assert sender.launch_plan.mailboxes.offline.binding is not None
    assert receiver.launch_plan.mailboxes.offline.binding is not None
    assert sender.launch_plan.mailboxes.offline.binding.filesystem_root == shared_root.resolve()
    assert receiver.launch_plan.mailboxes.offline.binding.filesystem_root == shared_root.resolve()
    assert (shared_root / "mailboxes" / "HOUMAO-mailbox-sender@agents.localhost" / "inbox").is_dir()
    assert (
        shared_root / "mailboxes" / "HOUMAO-mailbox-receiver@agents.localhost" / "inbox"
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
            mailboxes=_offline_mailboxes(
                _offline_binding(
                    transport="filesystem",
                    principal_id="HOUMAO-research",
                    address="HOUMAO-research@agents.localhost",
                    filesystem_root=persisted_root.resolve(),
                    bindings_version="2026-03-12T05:00:00.000001Z",
                )
            ),
        )
    )
    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=brain_manifest_path,
            agent_name="HOUMAO-research",
            agent_id=derive_agent_id_from_name("HOUMAO-research"),
            tmux_session_name="HOUMAO-research",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-research",
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

    assert controller.launch_plan.mailboxes.offline.binding is not None
    assert (
        controller.launch_plan.mailboxes.offline.binding.filesystem_root == persisted_root.resolve()
    )
    assert (
        captured["launch_plan"].mailboxes.offline.binding.filesystem_root
        == persisted_root.resolve()
    )


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
                "  principal_id: HOUMAO-mailbox-sender",
                "  address: HOUMAO-mailbox-sender@agents.localhost",
                f"  filesystem_root: {shared_root}",
            ]
        ),
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=sender_manifest,
        role_name="r",
        runtime_root=tmp_path / "runtime",
        backend="codex_headless",
        working_directory=tmp_path,
    )

    with pytest.raises(
        MailboxBootstrapError,
        match="no active mailbox registration exists",
    ):
        mailbox_env_bindings(
            _offline_binding(
                transport="filesystem",
                principal_id="HOUMAO-mailbox-receiver",
                address="HOUMAO-mailbox-receiver@agents.localhost",
                filesystem_root=shared_root.resolve(),
                bindings_version="2026-03-16T12:00:00Z",
            )
        )


def test_refresh_mailbox_bindings_updates_revision_in_configured_store(tmp_path: Path) -> None:
    old_root = tmp_path / "mail-old"
    new_root = old_root
    old_mailbox = _offline_binding(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
        filesystem_root=old_root.resolve(),
        bindings_version="2026-03-12T05:00:00.000001Z",
    )
    launch_plan = LaunchPlan(
        backend="codex_headless",
        tool="codex",
        executable="codex",
        args=["app-server"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "sk-secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="r",
            prompt="Role prompt",
        ),
        metadata={},
        mailboxes=_offline_mailboxes(old_mailbox),
    )
    manifest_path = default_manifest_path(tmp_path, "codex_headless", "fixture-session")

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
        agent_identity="HOUMAO-research",
        agent_id=derive_agent_id_from_name("HOUMAO-research"),
        tmux_session_name="HOUMAO-research",
    )
    controller.persist_manifest()

    refreshed = controller.refresh_mailbox_bindings(filesystem_root=new_root)

    assert refreshed.filesystem_root == new_root.resolve()
    assert controller.launch_plan.mailboxes.offline.binding == refreshed
    assert controller.launch_plan.env == {"OPENAI_API_KEY": "sk-secret"}
    assert "HOUMAO_MAILBOX_FS_ROOT" not in controller.launch_plan.env
    assert captured["launch_plan"].mailboxes.offline.binding == refreshed
    assert refreshed.bindings_version != old_mailbox.bindings_version
    assert (new_root / "protocol-version.txt").is_file()

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailboxes"]["offline"]["binding"]["filesystem_root"] == str(
        new_root.resolve()
    )


def _controller_for_mailbox_mutation(
    *,
    tmp_path: Path,
    backend: str,
    mailbox: FilesystemMailboxResolvedConfig | None,
    metadata: dict[str, object] | None = None,
) -> tuple[RuntimeSessionController, dict[str, LaunchPlan]]:
    """Build one runtime controller suitable for mailbox mutation tests."""

    launch_plan = LaunchPlan(
        backend=backend,
        tool="codex",
        executable="codex",
        args=["exec", "--json"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "sk-secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="r",
            prompt="Role prompt",
        ),
        metadata=dict(metadata or {}),
        mailboxes=_offline_mailboxes(mailbox),
    )
    manifest_path = default_manifest_path(tmp_path, "codex_headless", "fixture-session")
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
        agent_identity="HOUMAO-research",
        agent_id=derive_agent_id_from_name("HOUMAO-research"),
        tmux_session_name="HOUMAO-research",
    )
    controller.persist_manifest()
    return controller, captured


def test_register_filesystem_mailbox_updates_headless_launch_plan_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    controller, captured = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="codex_headless",
        mailbox=None,
    )
    mailbox_root = tmp_path / "shared-mail"

    result = _join_configured_mailbox(
        controller,
        mailbox_root=mailbox_root,
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
    )

    assert result.activation_state == "active"
    assert result.mailbox is not None
    assert controller.launch_plan.mailboxes.offline.binding == result.mailbox
    assert (
        controller.launch_plan.mailboxes.offline.binding.filesystem_root == mailbox_root.resolve()
    )
    assert controller.mailbox_activation_state() == "active"
    assert captured["launch_plan"].mailboxes.offline.binding == result.mailbox
    assert "HOUMAO_MAILBOX_FS_ROOT" not in controller.launch_plan.env
    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailboxes"]["offline"]["binding"]["filesystem_root"] == str(
        mailbox_root.resolve()
    )


def test_register_filesystem_mailbox_marks_local_interactive_session_active(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="codex_headless",
        mailbox=None,
    )

    result = _join_configured_mailbox(
        controller,
        mailbox_root=tmp_path / "shared-mail",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
    )

    assert result.activation_state == "active"
    assert controller.launch_plan.mailboxes.offline.binding is not None
    assert controller.mailbox_activation_state() == "active"
    assert "mailbox_live_enabled" not in controller.launch_plan.metadata
    assert "mailbox_live_bindings_version" not in controller.launch_plan.metadata


def test_register_filesystem_mailbox_defaults_to_project_overlay_root(
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    bootstrap_project_overlay(repo_root)
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=repo_root,
        backend="codex_headless",
        mailbox=None,
    )

    result = _join_configured_mailbox(
        controller,
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
    )

    assert result.mailbox is not None
    assert result.mailbox.filesystem_root == (repo_root / ".houmao" / "mailbox").resolve()


def test_register_filesystem_mailbox_derives_ordinary_houmao_address_when_omitted(
    tmp_path: Path,
) -> None:
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path,
        backend="codex_headless",
        mailbox=None,
    )

    result = _join_configured_mailbox(
        controller,
        mailbox_root=tmp_path / "shared-mail",
    )

    assert result.mailbox is not None
    assert result.mailbox.principal_id == controller.agent_id
    assert result.mailbox.address == "research@houmao.localhost"


def test_unregister_filesystem_mailbox_clears_local_interactive_mailbox_binding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    existing_mailbox = _offline_binding(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
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
        backend="codex_headless",
        mailbox=existing_mailbox,
    )

    result = controller.unregister_filesystem_mailbox()

    assert result.activation_state == "active"
    assert controller.launch_plan.mailboxes.offline.binding is None
    assert controller.mailbox_activation_state() is None
    assert "mailbox_live_enabled" not in controller.launch_plan.metadata
    assert "mailbox_live_bindings_version" not in controller.launch_plan.metadata


def test_relaunch_keeps_local_interactive_mailbox_active_without_live_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    existing_mailbox = _offline_binding(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
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
        backend="codex_headless",
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
        lambda controller, **_kwargs: SimpleNamespace(
            status="ok",
            action="relaunch",
            detail="relaunched",
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_pair_launch_registration",
        lambda controller: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_backend_launch_plan",
        lambda *, backend_session, launch_plan: None,
    )

    result = controller.relaunch()

    assert result.status == "ok"
    assert controller.mailbox_activation_state() == "active"
    assert "mailbox_live_enabled" not in controller.launch_plan.metadata
    assert "mailbox_live_bindings_version" not in controller.launch_plan.metadata


def test_relaunch_drops_one_off_env_overrides_and_keeps_persistent_env_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(
        tmp_path,
        env_records={"FEATURE_FLAG_X": "1"},
    )
    monkeypatch.setenv("UNDECLARED_MANAGER_VALUE", "ambient")

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    controller = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
        tmux_session_name="HOUMAO-research",
        project_overlay_dir=tmp_path / "selected-overlay",
        shared_runtime_root=runtime_root,
        shared_mailbox_root=tmp_path / "shared-mail",
        launch_env_overrides={
            "FEATURE_FLAG_X": "2",
            "SESSION_ONLY": "2",
        },
    )
    controller.tmux_session_name = "HOUMAO-research"
    controller.persist_manifest(refresh_registry=False)

    assert controller.launch_plan.env["FEATURE_FLAG_X"] == "2"
    assert controller.launch_plan.env["SESSION_ONLY"] == "2"
    assert controller.launch_plan.transient_env_var_names == frozenset(
        {"FEATURE_FLAG_X", "SESSION_ONLY"}
    )
    assert controller.launch_plan.public_env is not None
    assert controller.launch_plan.public_env["SESSION_ONLY"] == "2"
    assert "UNDECLARED_MANAGER_VALUE" not in controller.launch_plan.env
    assert controller.launch_plan.public_env["HOUMAO_PROJECT_OVERLAY_DIR"] == str(
        tmp_path / "selected-overlay"
    )

    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert "FEATURE_FLAG_X" in persisted["launch_plan"]["env_var_names"]
    assert "SESSION_ONLY" not in persisted["launch_plan"]["env_var_names"]

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._relaunch_backend_session",
        lambda controller, **_kwargs: SimpleNamespace(
            status="ok",
            action="relaunch",
            detail="relaunched",
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_pair_launch_registration",
        lambda controller: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_backend_launch_plan",
        lambda *, backend_session, launch_plan: None,
    )

    monkeypatch.setenv("HOUMAO_GLOBAL_RUNTIME_DIR", str(tmp_path / "other-runtime"))
    monkeypatch.setenv("HOUMAO_GLOBAL_MAILBOX_DIR", str(tmp_path / "other-mail"))
    monkeypatch.setenv("HOUMAO_PROJECT_OVERLAY_DIR", str(tmp_path / "other-overlay"))
    monkeypatch.chdir(agent_def_dir)
    result = controller.relaunch()

    assert result.status == "ok"
    assert controller.launch_plan.env["FEATURE_FLAG_X"] == "1"
    assert "SESSION_ONLY" not in controller.launch_plan.env
    assert controller.launch_plan.transient_env_var_names == frozenset()
    assert controller.launch_plan.public_env is not None
    assert controller.launch_plan.public_env["FEATURE_FLAG_X"] == "1"
    assert controller.launch_plan.public_env["HOUMAO_GLOBAL_RUNTIME_DIR"] == str(runtime_root)
    assert controller.launch_plan.public_env["HOUMAO_GLOBAL_MAILBOX_DIR"] == str(
        tmp_path / "shared-mail"
    )
    assert "SESSION_ONLY" in controller.launch_plan.previous_public_env_var_names


def test_relaunch_of_older_manifest_recomputes_default_managed_header(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    _seed_role(agent_def_dir)
    runtime_root = tmp_path / "runtime"
    brain_manifest_path = _seed_brain_manifest(tmp_path)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: object(),
    )

    controller = _start_configured_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=brain_manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_headless",
        working_directory=tmp_path,
        agent_name="alice",
        tmux_session_name="HOUMAO-alice",
    )
    controller.tmux_session_name = "HOUMAO-alice"
    controller.persist_manifest(refresh_registry=False)

    assert controller.launch_plan.role_injection.prompt == "Role prompt"

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._relaunch_backend_session",
        lambda controller, **_kwargs: SimpleNamespace(
            status="ok",
            action="relaunch",
            detail="relaunched",
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_pair_launch_registration",
        lambda controller: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._refresh_backend_launch_plan",
        lambda *, backend_session, launch_plan: None,
    )

    result = controller.relaunch()

    assert result.status == "ok"
    assert controller.launch_plan.role_injection.prompt.startswith(
        '<houmao_system_prompt version="1">'
    )
    assert "<managed_header>" in controller.launch_plan.role_injection.prompt
    assert "Agent name: alice" in controller.launch_plan.role_injection.prompt
    assert (
        "<role_prompt>\nRole prompt\n</role_prompt>" in controller.launch_plan.role_injection.prompt
    )


def test_refresh_cannot_move_offline_registration_to_another_store(tmp_path: Path) -> None:
    """Refresh preserves selected registry authority rather than creating another store."""

    root = tmp_path / "shared-mail"
    binding = _offline_binding(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="research@houmao.localhost",
        filesystem_root=root,
        bindings_version="initial",
    )
    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path, backend="codex_headless", mailbox=binding
    )
    before = controller.launch_plan.mailboxes
    with pytest.raises(SessionManifestError, match="configured|registry|store"):
        controller.refresh_mailbox_bindings(filesystem_root=tmp_path / "other-store")
    assert controller.launch_plan.mailboxes == before
    assert not (tmp_path / "other-store").exists()


def test_controller_persistence_refreshes_cached_backend_binding(tmp_path: Path) -> None:
    """An older controller preserves externally committed slots in disk and backend cache."""

    from houmao.agents.realm_controller.manifest import (
        load_session_manifest,
        mutate_session_mailbox_binding,
    )

    controller, captured = _controller_for_mailbox_mutation(
        tmp_path=tmp_path, backend="codex_headless", mailbox=None
    )
    old_revision = controller.launch_plan.mailboxes.offline.revision
    binding = _offline_mailboxes(
        _offline_binding(
            transport="filesystem",
            principal_id="HOUMAO-research",
            address="research@houmao.localhost",
            filesystem_root=tmp_path / "shared-mail",
            bindings_version="prepared",
        )
    ).offline.binding
    current = load_session_manifest(controller.manifest_path).payload
    external = mutate_session_mailbox_binding(
        controller.manifest_path,
        channel="offline",
        expected_revision=old_revision,
        binding=binding,
        agent_id=controller.agent_id,
        session_id=current["runtime"]["session_id"],
    )
    assert controller.launch_plan.mailboxes.offline.binding is None
    from houmao.agents.mailbox_runtime_models import StalwartMailboxResolvedConfig

    online = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id=controller.agent_id,
        agent_id=controller.agent_id,
        binding_id="online-account-a",
        address="research@example.test",
        bindings_version="prepared",
        jmap_url="http://127.0.0.1:10080/.well-known/jmap",
        management_url="http://127.0.0.1:10080/api",
        login_identity="online-login",
        credential_ref="missing-private-account",
    )
    external = mutate_session_mailbox_binding(
        controller.manifest_path,
        channel="online",
        expected_revision=external.payload["launch_plan"]["mailboxes"]["online"]["revision"],
        binding=online,
        agent_id=controller.agent_id,
        session_id=current["runtime"]["session_id"],
    )
    controller.persist_manifest(refresh_registry=False)
    expected = external.payload["launch_plan"]["mailboxes"]
    assert controller.launch_plan.mailboxes.redacted_payload() == expected
    assert captured["launch_plan"].mailboxes.redacted_payload() == expected
    assert (
        load_session_manifest(controller.manifest_path).payload["launch_plan"]["mailboxes"]
        == expected
    )


def test_projection_failure_reports_committed_revision_and_reconciles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery failure leaves the confirmed registration available for idempotent retry."""

    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path, backend="codex_headless", mailbox=None
    )
    controller.registry_generation_id = "fixture-generation"
    controller.persist_manifest(refresh_registry=False)
    original_refresh = controller.refresh_shared_registry_record

    def unavailable_projection() -> None:
        """Model a failed registry projection after the binding file committed."""

        raise SessionManifestError("projection unavailable")

    monkeypatch.setattr(controller, "refresh_shared_registry_record", unavailable_projection)
    result = _join_configured_mailbox(
        controller, mailbox_root=tmp_path / "shared-mail", address="research@houmao.localhost"
    )
    assert result.mailbox is not None
    confirmed_revision = controller.launch_plan.mailboxes.offline.revision
    assert result.mailbox.bindings_version == confirmed_revision
    warnings = controller.consume_operation_warnings()
    assert len(warnings) == 1
    assert f"committed at revision {confirmed_revision}" in warnings[0]
    assert "projection refresh failed" in warnings[0]
    assert "reconcile" in warnings[0]
    registration = load_active_mailbox_registration(
        tmp_path / "shared-mail", address=result.mailbox.address
    )
    assert registration.registration_id == result.mailbox.binding_id
    monkeypatch.setattr(controller, "refresh_shared_registry_record", original_refresh)
    retry = _join_configured_mailbox(
        controller, mailbox_root=tmp_path / "shared-mail", address="research@houmao.localhost"
    )
    assert retry.mailbox is not None
    assert retry.mailbox.binding_id == result.mailbox.binding_id
    assert retry.mailbox.agent_id == controller.agent_id
    assert retry.shared_lifecycle_result["reused_existing"] is True
    assert controller.consume_operation_warnings() == ()
    from houmao.agents.realm_controller.registry_storage import (
        load_managed_agent_record_by_agent_id,
    )

    projected = load_managed_agent_record_by_agent_id(controller.agent_id)
    assert projected is not None
    assert projected.mailboxes.offline.binding is not None
    assert projected.mailboxes.offline.binding.binding_id == retry.mailbox.binding_id
    assert projected.mailboxes.offline.revision == retry.mailbox.bindings_version
    assert projected.agent_id == controller.agent_id
    monkeypatch.setattr(controller, "refresh_shared_registry_record", unavailable_projection)
    released = controller.unregister_filesystem_mailbox()
    assert released.mailbox is None
    release_warning = controller.consume_operation_warnings()
    assert len(release_warning) == 1
    assert controller.launch_plan.mailboxes.offline.revision in release_warning[0]
    assert "released offline slot" in release_warning[0]
    assert "retry join" not in release_warning[0]


def test_retry_leave_after_reassignment_preserves_the_next_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lost local leave publication cannot release another owner's later registration."""

    from houmao.agents.realm_controller import runtime as runtime_module
    from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox

    controller, _ = _controller_for_mailbox_mutation(
        tmp_path=tmp_path, backend="codex_headless", mailbox=None
    )
    joined = _join_configured_mailbox(
        controller, mailbox_root=tmp_path / "shared-mail", address="research@houmao.localhost"
    )
    assert joined.mailbox is not None
    original_commit = runtime_module.mutate_session_mailbox_binding

    def lose_local_publication(*args: Any, **kwargs: Any) -> Any:
        """Model a failed local write after the registry confirmed explicit release."""

        raise OSError("injected local publication failure")

    monkeypatch.setattr(runtime_module, "mutate_session_mailbox_binding", lose_local_publication)
    with pytest.raises((OSError, SessionManifestError)):
        controller.unregister_filesystem_mailbox()
    monkeypatch.setattr(runtime_module, "mutate_session_mailbox_binding", original_commit)
    replacement = register_mailbox(
        tmp_path / "shared-mail",
        RegisterMailboxRequest(
            mode="safe",
            owner_principal_id="next-agent",
            address=joined.mailbox.address,
            mailbox_kind="in_root",
            mailbox_path=tmp_path / "shared-mail/mailboxes" / joined.mailbox.address,
        ),
    )
    assert replacement["active_registration_id"] != joined.mailbox.binding_id
    result = controller.unregister_filesystem_mailbox()
    assert result.mailbox is None
    assert result.shared_lifecycle_result["action"] == "already_released"
    current = load_active_mailbox_registration(
        tmp_path / "shared-mail", address=joined.mailbox.address
    )
    assert current.owner_principal_id == "next-agent"
    assert current.registration_id == replacement["active_registration_id"]
    assert controller.launch_plan.mailboxes.offline.binding is None

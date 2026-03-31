from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.mailbox_runtime_support import (
    install_runtime_mailbox_system_skills_for_tool,
    mailbox_env_bindings,
    mailbox_skills_destination_for_tool,
    publish_tmux_live_mailbox_projection,
    resolve_live_mailbox_binding_from_agent_identity,
    resolve_live_mailbox_binding_from_manifest_path,
    resolve_live_mailbox_binding,
)
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.gateway_models import GatewayCurrentInstanceV1
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    write_gateway_current_instance,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    RegistryGatewayV1,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
)
from houmao.agents.realm_controller.registry_storage import publish_live_agent_record
from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox


def _build_filesystem_mailbox(tmp_path: Path) -> FilesystemMailboxResolvedConfig:
    mailbox_root = tmp_path / "mailbox"
    durable_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-26T18:10:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(
            principal_id=durable_mailbox.principal_id,
            address=durable_mailbox.address,
        ),
    )
    return durable_mailbox


def _build_symlink_filesystem_mailbox(tmp_path: Path) -> FilesystemMailboxResolvedConfig:
    mailbox_root = tmp_path / "mailbox"
    private_mailbox = (tmp_path / "private-mailboxes" / "HOUMAO-research").resolve()
    durable_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-26T18:10:00.000001Z",
        mailbox_kind="symlink",
        mailbox_path=private_mailbox,
    )
    bootstrap_filesystem_mailbox(mailbox_root)
    register_mailbox(
        mailbox_root,
        RegisterMailboxRequest(
            mode="safe",
            address=durable_mailbox.address,
            owner_principal_id=durable_mailbox.principal_id,
            mailbox_kind="symlink",
            mailbox_path=private_mailbox,
        ),
    )
    return durable_mailbox


def _seed_manifest_with_mailbox(
    tmp_path: Path,
    *,
    mailbox: FilesystemMailboxResolvedConfig,
    agent_name: str = "gpu",
) -> Path:
    launch_plan = LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=["-p"],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="r",
            prompt="Role prompt",
        ),
        metadata={},
        mailbox=mailbox,
    )
    manifest_path = default_manifest_path(tmp_path, "claude_headless", "claude-headless-1")
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name=agent_name,
            agent_id=derive_agent_id_from_name(agent_name),
            tmux_session_name=f"HOUMAO-{agent_name}",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 0,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": f"HOUMAO-{agent_name}",
            },
        )
    )
    write_session_manifest(manifest_path, payload)
    return manifest_path


def _seed_gateway_current_instance(manifest_path: Path, *, port: int = 43123) -> Path:
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    write_gateway_current_instance(
        paths.current_instance_path,
        GatewayCurrentInstanceV1(
            pid=4242,
            host="127.0.0.1",
            port=port,
            managed_agent_instance_epoch=1,
        ),
    )
    return paths.state_path


def _healthy_gateway_client_factory(endpoint_log: list[str]):
    def _factory(endpoint):
        endpoint_log.append(f"http://{endpoint.host}:{endpoint.port}")
        return SimpleNamespace(health=lambda: SimpleNamespace(protocol_version="v1"))

    return _factory


def test_resolve_live_mailbox_binding_uses_targeted_filesystem_projection(
    tmp_path: Path,
) -> None:
    durable_mailbox = _build_filesystem_mailbox(tmp_path)
    resolution = resolve_live_mailbox_binding(durable_mailbox=durable_mailbox)

    payload = resolution.payload()

    assert resolution.source == "manifest_binding"
    assert resolution.mailbox == durable_mailbox
    assert "env" not in payload
    assert payload["mailbox"]["filesystem"]["root"] == str(durable_mailbox.filesystem_root)
    assert payload["mailbox"]["filesystem"]["mailbox_path"] == str(
        durable_mailbox.mailbox_path
    )


def test_resolve_live_mailbox_binding_preserves_symlink_filesystem_projection(
    tmp_path: Path,
) -> None:
    durable_mailbox = _build_symlink_filesystem_mailbox(tmp_path)
    resolution = resolve_live_mailbox_binding(durable_mailbox=durable_mailbox)

    payload = resolution.payload()

    assert resolution.source == "manifest_binding"
    assert resolution.mailbox == durable_mailbox
    assert payload["mailbox"]["filesystem"]["mailbox_kind"] == "symlink"
    assert payload["mailbox"]["filesystem"]["mailbox_path"] == str(
        durable_mailbox.mailbox_path
    )


def test_resolve_live_mailbox_binding_rejects_missing_active_registration(tmp_path: Path) -> None:
    durable_mailbox = _build_filesystem_mailbox(tmp_path)
    unregistered_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id=durable_mailbox.principal_id,
        address="HOUMAO-missing@agents.localhost",
        filesystem_root=durable_mailbox.filesystem_root,
        bindings_version=durable_mailbox.bindings_version,
    )

    with pytest.raises(ValueError, match="no active mailbox registration exists"):
        resolve_live_mailbox_binding(durable_mailbox=unregistered_mailbox)


def test_publish_tmux_live_mailbox_projection_refreshes_current_bindings(tmp_path: Path) -> None:
    old_root = tmp_path / "mail-old"
    new_root = tmp_path / "mail-new"
    previous_mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
        filesystem_root=old_root.resolve(),
        bindings_version="2026-03-26T18:10:00.000001Z",
    )
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
        filesystem_root=new_root.resolve(),
        bindings_version="2026-03-26T18:20:00.000001Z",
    )
    bootstrap_filesystem_mailbox(
        new_root,
        principal=MailboxPrincipal(
            principal_id=mailbox.principal_id,
            address=mailbox.address,
        ),
    )
    set_calls: list[tuple[str, dict[str, str]]] = []
    unset_calls: list[tuple[str, list[str]]] = []

    publish_tmux_live_mailbox_projection(
        session_name="HOUMAO-research",
        previous_mailbox=previous_mailbox,
        mailbox=mailbox,
        set_env=lambda session_name, env_vars: set_calls.append((session_name, dict(env_vars))),
        unset_env=lambda session_name, variable_names: unset_calls.append(
            (session_name, list(variable_names))
        ),
    )

    assert set_calls
    assert set_calls[-1][0] == "HOUMAO-research"
    assert set_calls[-1][1]["HOUMAO_MAILBOX_FS_ROOT"] == str(new_root.resolve())
    assert set_calls[-1][1]["HOUMAO_MAILBOX_BINDINGS_VERSION"] == mailbox.bindings_version
    assert unset_calls == []


def test_publish_tmux_live_mailbox_projection_clears_stale_transport_vars(tmp_path: Path) -> None:
    credential_file = tmp_path / "mailbox-secret.json"
    credential_file.write_text('{"password":"secret"}\n', encoding="utf-8")
    previous_mailbox = StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
        jmap_url="http://stalwart.local/jmap",
        management_url="http://stalwart.local/api",
        login_identity="HOUMAO-research@agents.localhost",
        credential_ref="cred-1",
        bindings_version="2026-03-26T18:10:00.000001Z",
        credential_file=credential_file,
    )
    set_calls: list[tuple[str, dict[str, str]]] = []
    unset_calls: list[tuple[str, list[str]]] = []

    publish_tmux_live_mailbox_projection(
        session_name="HOUMAO-research",
        previous_mailbox=previous_mailbox,
        mailbox=None,
        set_env=lambda session_name, env_vars: set_calls.append((session_name, dict(env_vars))),
        unset_env=lambda session_name, variable_names: unset_calls.append(
            (session_name, list(variable_names))
        ),
    )

    assert set_calls == []
    assert unset_calls == [
        (
            "HOUMAO-research",
            [
                "HOUMAO_MAILBOX_ADDRESS",
                "HOUMAO_MAILBOX_BINDINGS_VERSION",
                "HOUMAO_MAILBOX_EMAIL_CREDENTIAL_FILE",
                "HOUMAO_MAILBOX_EMAIL_CREDENTIAL_REF",
                "HOUMAO_MAILBOX_EMAIL_JMAP_URL",
                "HOUMAO_MAILBOX_EMAIL_LOGIN_IDENTITY",
                "HOUMAO_MAILBOX_EMAIL_MANAGEMENT_URL",
                "HOUMAO_MAILBOX_PRINCIPAL_ID",
                "HOUMAO_MAILBOX_TRANSPORT",
            ],
        )
    ]


def test_resolve_live_mailbox_binding_from_manifest_path_uses_manifest_binding_and_current_instance_gateway(
    tmp_path: Path,
) -> None:
    mailbox = _build_filesystem_mailbox(tmp_path)
    manifest_path = _seed_manifest_with_mailbox(tmp_path, mailbox=mailbox)
    state_path = _seed_gateway_current_instance(manifest_path)
    endpoint_log: list[str] = []

    resolution = resolve_live_mailbox_binding_from_manifest_path(
        manifest_path=manifest_path,
        source="auto",
        process_env_reader=lambda _: None,
        tmux_env_reader=lambda _: None,
        gateway_client_factory=_healthy_gateway_client_factory(endpoint_log),
    )

    payload = resolution.payload()

    assert resolution.source == "manifest_binding"
    assert resolution.mailbox == mailbox
    assert resolution.gateway is not None
    assert resolution.gateway.source == "current_instance_record"
    assert resolution.gateway.base_url == "http://127.0.0.1:43123"
    assert resolution.gateway.state_path == state_path.resolve()
    assert payload["mailbox"]["filesystem"]["inbox_path"].endswith(
        "HOUMAO-research@agents.localhost/inbox"
    )
    assert endpoint_log == ["http://127.0.0.1:43123"]


def test_resolve_live_mailbox_binding_from_agent_identity_uses_registry_manifest_and_current_instance(
    tmp_path: Path,
) -> None:
    mailbox = _build_filesystem_mailbox(tmp_path)
    manifest_path = _seed_manifest_with_mailbox(tmp_path, mailbox=mailbox, agent_name="gpu")
    state_path = _seed_gateway_current_instance(manifest_path, port=43124)
    registry_root = tmp_path / "registry"
    published_at = datetime.now(UTC)
    publish_live_agent_record(
        LiveAgentRegistryRecordV2(
            agent_name="gpu",
            agent_id=derive_agent_id_from_name("gpu"),
            generation_id="gen-1",
            published_at=published_at.isoformat().replace("+00:00", "Z"),
            lease_expires_at=(published_at + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
            runtime=RegistryRuntimeV1(
                manifest_path=str(manifest_path),
                session_root=str(manifest_path.parent),
                agent_def_dir=str(tmp_path / "repo"),
            ),
            terminal=RegistryTerminalV1(session_name="HOUMAO-gpu"),
            gateway=RegistryGatewayV1(
                host="127.0.0.1",
                port=49999,
                state_path=str(tmp_path / "stale-state.json"),
                protocol_version="v1",
            ),
        ),
        env={"HOUMAO_GLOBAL_REGISTRY_DIR": str(registry_root)},
        now=published_at,
    )
    endpoint_log: list[str] = []

    resolution = resolve_live_mailbox_binding_from_agent_identity(
        agent_identity="gpu",
        env={"HOUMAO_GLOBAL_REGISTRY_DIR": str(registry_root)},
        process_env_reader=lambda _: None,
        tmux_env_reader=mailbox_env_bindings(mailbox).get,
        gateway_client_factory=_healthy_gateway_client_factory(endpoint_log),
    )

    assert resolution.source == "manifest_binding"
    assert resolution.mailbox == mailbox
    assert resolution.gateway is not None
    assert resolution.gateway.source == "current_instance_record"
    assert resolution.gateway.base_url == "http://127.0.0.1:43124"
    assert resolution.gateway.state_path == state_path.resolve()
    assert endpoint_log == ["http://127.0.0.1:43124"]


def test_install_runtime_mailbox_system_skills_for_tool_projects_gateway_and_transport_docs(
    tmp_path: Path,
) -> None:
    home_path = tmp_path / "codex-home"

    references = install_runtime_mailbox_system_skills_for_tool(tool="codex", home_path=home_path)

    mailbox_root = home_path / mailbox_skills_destination_for_tool("codex") / "mailbox"
    assert set(references) == {
        "mailbox/houmao-email-via-agent-gateway",
        "mailbox/houmao-email-via-filesystem",
        "mailbox/houmao-email-via-stalwart",
    }
    assert (mailbox_root / "houmao-email-via-agent-gateway/SKILL.md").is_file()
    assert (mailbox_root / "houmao-email-via-agent-gateway/actions/check.md").is_file()
    assert (mailbox_root / "houmao-email-via-agent-gateway/actions/reply.md").is_file()
    assert (mailbox_root / "houmao-email-via-agent-gateway/references/curl-examples.md").is_file()
    assert (mailbox_root / "houmao-email-via-filesystem/SKILL.md").is_file()
    assert (mailbox_root / "houmao-email-via-stalwart/SKILL.md").is_file()


def test_install_runtime_mailbox_system_skills_for_tool_respects_tool_skill_destination(
    tmp_path: Path,
) -> None:
    home_path = tmp_path / "gemini-home"

    install_runtime_mailbox_system_skills_for_tool(tool="gemini", home_path=home_path)

    assert (
        home_path
        / mailbox_skills_destination_for_tool("gemini")
        / "mailbox/houmao-email-via-agent-gateway/SKILL.md"
    ).is_file()

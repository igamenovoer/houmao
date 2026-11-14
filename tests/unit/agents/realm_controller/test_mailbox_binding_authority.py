"""Dual mailbox snapshots and competing-process manifest authority checks."""

from __future__ import annotations

import multiprocessing
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import pytest

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxesResolvedConfig,
    MailboxSlotConfig,
    RemoteRegistryMailboxResolvedConfig,
    StalwartMailboxResolvedConfig,
)
from houmao.agents.mailbox_runtime_support import (
    mailboxes_resolved_config_from_payload,
    safe_registry_mailboxes_projection,
)
from houmao.agents.realm_controller.boundary_models import MailboxesPayloadV1
from houmao.agents.realm_controller.manifest import (
    MailboxBindingConflict,
    SessionManifestRequest,
    build_session_manifest_payload,
    load_session_manifest,
    mutate_session_mailbox_binding,
    write_session_manifest,
    update_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan


def _offline(
    root: Path, *, owner: str = "agent-a", binding_id: str = "registration-a"
) -> FilesystemMailboxResolvedConfig:
    """Build a local snapshot without preparing a backing store."""

    return FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id=owner,
        agent_id=owner,
        binding_id=binding_id,
        address="alice@houmao.localhost",
        filesystem_root=root,
        bindings_version="backend-initial",
    )


def _online(*, owner: str = "agent-a") -> StalwartMailboxResolvedConfig:
    """Build an online snapshot with a deliberately unavailable credential reference."""

    return StalwartMailboxResolvedConfig(
        transport="stalwart",
        principal_id=owner,
        agent_id=owner,
        binding_id="online-a",
        address="alice@example.test",
        jmap_url="http://127.0.0.1/jmap/session",
        management_url="http://127.0.0.1/api",
        login_identity="login-alice",
        credential_ref="private/account-a",
        bindings_version="backend-initial",
    )


def _manifest(
    root: Path, *, backend: Literal["local_interactive", "claude_headless"] = "local_interactive"
) -> Path:
    """Persist a valid isolated session with both empty slot authorities."""

    plan = LaunchPlan(
        backend=backend,
        tool="claude",
        executable="claude",
        args=[],
        working_directory=root,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=root / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt", role_name="worker", prompt="Work."
        ),
    )
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="worker",
            brain_manifest_path=root / "brain.yaml",
            agent_name="HOUMAO-alice",
            agent_id="agent-a",
            tmux_session_name="HOUMAO-alice",
            session_id="session-a",
            backend_state={"working_directory": str(root)},
        )
    )
    path = root / "manifest.json"
    write_session_manifest(path, payload)
    return path


def _race_update(path: str, channel: str, revision: str, barrier: Any, outcomes: Any) -> None:
    """Race one prepared snapshot after both processes reach the admission barrier."""

    binding = _offline(Path(path).parent / "mail") if channel == "offline" else _online()
    barrier.wait(timeout=10)
    try:
        mutate_session_mailbox_binding(
            Path(path),
            channel=channel,
            expected_revision=revision,
            binding=binding,
            agent_id="agent-a",
            session_id="session-a",
        )
    except MailboxBindingConflict:
        outcomes.put("conflict")
    else:
        outcomes.put("committed")


@pytest.mark.parametrize(
    "offline,online,expected",
    [
        (False, False, None),
        (True, False, {"channel": "offline", "address": "alice@houmao.localhost"}),
        (False, True, {"channel": "online", "address": "alice@example.test"}),
        (True, True, {"channel": "online", "address": "alice@example.test"}),
    ],
)
def test_canonical_identity_uses_configured_presence(
    tmp_path: Path, offline: bool, online: bool, expected: dict[str, str] | None
) -> None:
    config = MailboxesResolvedConfig(
        offline=MailboxSlotConfig(binding=_offline(tmp_path) if offline else None),
        online=MailboxSlotConfig(binding=_online() if online else None),
    )
    assert config.canonical_mail_identity == expected
    assert mailboxes_resolved_config_from_payload(config.redacted_payload()) == config
    MailboxesPayloadV1.model_validate(config.redacted_payload())
    if online:
        assert config.online.binding is not None
        assert config.online.binding.credential_file is None
        assert config.canonical_mail_identity == expected


def test_slots_reject_mixed_owners_or_wrong_channel(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="same agent"):
        MailboxesResolvedConfig(
            offline=MailboxSlotConfig(binding=_offline(tmp_path)),
            online=MailboxSlotConfig(binding=_online(owner="agent-b")),
        )
    with pytest.raises(ValueError, match="offline slot"):
        MailboxesResolvedConfig(offline=MailboxSlotConfig(binding=_online()))
    with pytest.raises(ValueError, match="online slot"):
        MailboxesResolvedConfig(online=MailboxSlotConfig(binding=_offline(tmp_path)))


def test_registry_projection_excludes_secret_resolution_inputs(tmp_path: Path) -> None:
    config = MailboxesResolvedConfig(
        offline=MailboxSlotConfig(binding=_offline(tmp_path / "private-store")),
        online=MailboxSlotConfig(binding=replace(_online(), credential_file=tmp_path / "password")),
    )
    projection = repr(safe_registry_mailboxes_projection(config))
    for private in (
        "credential_ref",
        "credential_file",
        "login_identity",
        "management_url",
        "private-store",
        "password",
    ):
        assert private not in projection


def test_remote_binding_has_no_registry_filesystem_path() -> None:
    binding = RemoteRegistryMailboxResolvedConfig(
        transport="registry",
        agent_id="agent-a",
        binding_id="reg-a",
        principal_id="agent-a",
        address="alice@houmao.localhost",
        bindings_version="initial",
        registry_url="https://registry.example.test",
        credential_ref="/private/member-token",
    )
    config = MailboxesResolvedConfig(offline=MailboxSlotConfig(binding=binding))
    assert config.offline.binding is not None
    assert "filesystem_root" not in config.offline.binding.redacted_payload()


def test_stale_writer_and_detach_do_not_resurrect_bindings(tmp_path: Path) -> None:
    path = _manifest(tmp_path)
    stale = load_session_manifest(path).payload
    revision = stale["launch_plan"]["mailboxes"]["offline"]["revision"]
    joined = mutate_session_mailbox_binding(
        path,
        channel="offline",
        expected_revision=revision,
        binding=_offline(tmp_path / "mail"),
        agent_id="agent-a",
        session_id="session-a",
    )
    slot = joined.payload["launch_plan"]["mailboxes"]["offline"]
    stale["backend_state"]["turn_index"] = 10
    committed = write_session_manifest(path, stale)
    assert committed.payload["launch_plan"]["mailboxes"]["offline"] == slot
    detached = mutate_session_mailbox_binding(
        path,
        channel="offline",
        expected_revision=slot["revision"],
        binding=None,
        agent_id="agent-a",
        session_id="session-a",
    )
    assert detached.payload["launch_plan"]["mailboxes"]["offline"]["binding"] is None
    assert detached.payload["launch_plan"]["mailboxes"]["offline"]["revision"] != revision
    with pytest.raises(MailboxBindingConflict):
        mutate_session_mailbox_binding(
            path,
            channel="offline",
            expected_revision=revision,
            binding=_offline(tmp_path / "mail"),
            agent_id="agent-a",
            session_id="session-a",
        )


@pytest.mark.parametrize(
    "channels,expected",
    [
        (("offline", "offline"), ["committed", "conflict"]),
        (("offline", "online"), ["committed", "committed"]),
    ],
)
def test_process_mutations_are_serialized(
    tmp_path: Path, channels: tuple[str, str], expected: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _manifest(tmp_path)
    payload = load_session_manifest(path).payload
    # Spawn imports this pytest namespace module afresh, so include its repository root.
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4]))
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    outcomes = context.Queue()
    processes = [
        context.Process(
            target=_race_update,
            args=(
                str(path),
                channel,
                payload["launch_plan"]["mailboxes"][channel]["revision"],
                barrier,
                outcomes,
            ),
        )
        for channel in channels
    ]
    for process in processes:
        process.start()
    try:
        for process in processes:
            process.join(timeout=20)
            assert process.exitcode == 0
        assert sorted(outcomes.get(timeout=2) for _ in processes) == expected
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        outcomes.close()


def test_interrupted_atomic_replace_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _manifest(tmp_path)
    before = path.read_bytes()
    payload = load_session_manifest(path).payload

    def fail_replace(source: object, destination: object) -> None:
        """Model a failure before the atomic filesystem commit."""

        raise OSError("injected replacement failure")

    monkeypatch.setattr("houmao.agents.realm_controller.manifest.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        write_session_manifest(path, payload)
    assert path.read_bytes() == before
    assert [item.name for item in tmp_path.glob(".manifest.json.*")] == [".manifest.json.lock"]


def test_health_failures_preserve_both_configured_identities(tmp_path: Path) -> None:
    """Unavailable stores remain visible without choosing another channel."""

    from houmao.agents.mailbox_runtime_support import LiveMailboxesBindingResolution

    config = MailboxesResolvedConfig(
        offline=MailboxSlotConfig(binding=_offline(tmp_path / "missing-store")),
        online=MailboxSlotConfig(binding=_online()),
    )
    payload = LiveMailboxesBindingResolution(mailboxes=config).payload()
    assert payload["mailboxes"]["offline"]["availability"] == "unavailable"
    assert payload["mailboxes"]["online"]["availability"] == "unavailable"
    assert payload["canonical_mail_identity"] == {
        "channel": "online",
        "address": "alice@example.test",
    }


def test_loading_current_slots_never_allocates_revisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read preserves empty-slot tombstones without generating identity."""

    config = MailboxesResolvedConfig(offline=MailboxSlotConfig(binding=_offline(tmp_path)))
    payload = config.redacted_payload()

    def unexpected_uuid() -> None:
        """Fail any generation attempted while reconstructing a snapshot."""

        raise AssertionError("snapshot read must not allocate a revision")

    monkeypatch.setattr("houmao.agents.mailbox_runtime_models.uuid4", unexpected_uuid)
    assert mailboxes_resolved_config_from_payload(payload) == config


def test_wrong_persisted_channel_is_rejected(tmp_path: Path) -> None:
    """Backend type cannot silently override a caller's swapped channel field."""

    payload = MailboxesResolvedConfig(
        offline=MailboxSlotConfig(binding=_offline(tmp_path))
    ).redacted_payload()
    payload["offline"]["binding"]["channel"] = "online"
    with pytest.raises(ValueError, match="channel"):
        mailboxes_resolved_config_from_payload(payload)


def test_launch_prepares_both_slots_for_one_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Launch-time provisioning keeps independent offline and online registrations."""

    from types import SimpleNamespace
    from houmao.agents.mailbox_runtime_models import (
        FilesystemMailboxDeclarativeConfig,
        MailboxesDeclarativeConfig,
        StalwartMailboxDeclarativeConfig,
    )
    from houmao.agents.mailbox_runtime_support import resolve_effective_mailboxes_config
    from houmao.mailbox.registry_config import associate_registry_store

    registry_root = tmp_path / "registry"
    mailbox_root = tmp_path / "offline-mail"
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    associate_registry_store(registry_root, mailbox_root)
    provisioning_calls: list[dict[str, Any]] = []

    def ensure_online(**kwargs: Any) -> Any:
        """Model successful startup provisioning without external credentials."""

        provisioning_calls.append(kwargs)
        return SimpleNamespace(
            jmap_url=kwargs["jmap_url"],
            management_url=kwargs["management_url"],
            login_identity=kwargs["login_identity"],
            credential_ref="private-online-ref",
            credential_file=tmp_path / "private-online.json",
        )

    monkeypatch.setattr(
        "houmao.agents.mailbox_runtime_support.ensure_stalwart_mailbox", ensure_online
    )
    mailboxes = resolve_effective_mailboxes_config(
        declared_config=MailboxesDeclarativeConfig(
            offline=FilesystemMailboxDeclarativeConfig(
                transport="filesystem",
                address="alice@houmao.localhost",
                filesystem_root=str(mailbox_root),
            ),
            online=StalwartMailboxDeclarativeConfig(
                transport="stalwart",
                address="alice@example.test",
                jmap_url="http://127.0.0.1:10080/.well-known/jmap",
                management_url="http://127.0.0.1:10080/api",
            ),
        ),
        agent_id="agent-a",
        runtime_root=tmp_path / "runtime",
        tool="claude",
        role_name="worker",
        manifest_path_hint=tmp_path / "runtime/sessions/claude_headless/session-a/manifest.json",
    )
    assert mailboxes.offline.binding is not None
    assert mailboxes.online.binding is not None
    assert mailboxes.offline.binding.agent_id == mailboxes.online.binding.agent_id == "agent-a"
    assert mailboxes.offline.binding.binding_id != mailboxes.online.binding.binding_id
    assert mailboxes.offline.binding.principal_id == "agent-a"
    assert mailboxes.online.binding.principal_id == "agent-a"
    assert mailboxes.canonical_mail_identity == {
        "channel": "online",
        "address": "alice@example.test",
    }
    assert len(provisioning_calls) == 1
    assert "credential_file" not in mailboxes.online.binding.redacted_payload()


def test_stale_runtime_write_preserves_server_owned_authority(tmp_path: Path) -> None:
    """Endpoint ownership is merged under the same lock as mailbox preservation."""

    path = _manifest(tmp_path, backend="claude_headless")
    stale = load_session_manifest(path).payload
    authority = stale["gateway_authority"]
    for endpoint in authority.values():
        endpoint["api_base_url"] = "http://127.0.0.1:9012"
        endpoint["managed_agent_ref"] = "new-server-target"
    update_session_manifest(path, {"gateway_authority": authority})
    for endpoint in stale["gateway_authority"].values():
        endpoint["api_base_url"] = "http://127.0.0.1:9001"
        endpoint["managed_agent_ref"] = "stale-server-target"
    stale["backend_state"]["turn_index"] = 9
    committed = write_session_manifest(path, stale).payload
    assert committed["backend_state"]["turn_index"] == 9
    for endpoint in committed["gateway_authority"].values():
        assert endpoint["api_base_url"] == "http://127.0.0.1:9012"
        assert endpoint["managed_agent_ref"] == "new-server-target"


def test_binding_decode_does_not_materialize_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable provider cannot prevent another channel's snapshot mutation."""

    config = MailboxesResolvedConfig(
        offline=MailboxSlotConfig(binding=_offline(tmp_path / "missing-store")),
        online=MailboxSlotConfig(binding=_online()),
    )

    def forbidden_materialization(**kwargs: Any) -> Path:
        """Fail any secret copying during a read-only binding decode."""

        raise AssertionError("decoding bindings must not materialize credentials")

    monkeypatch.setattr(
        "houmao.mailbox.stalwart.materialize_stalwart_session_credential", forbidden_materialization
    )
    decoded = mailboxes_resolved_config_from_payload(
        config.redacted_payload(),
        manifest_path=tmp_path / "runtime/sessions/claude_headless/session-a/manifest.json",
    )
    assert decoded.canonical_mail_identity == config.canonical_mail_identity
    assert decoded.online.binding is not None
    assert decoded.online.binding.credential_file is not None
    assert not decoded.online.binding.credential_file.exists()
    assert not (tmp_path / "runtime").exists()


def test_server_publication_preserves_newer_runtime_endpoint_fields(tmp_path: Path) -> None:
    """A server projection merges only its owned fields into the current authority."""

    from houmao.agents.realm_controller.manifest import update_session_server_gateway_authority

    path = _manifest(tmp_path, backend="claude_headless")
    stale = load_session_manifest(path).payload
    updated = load_session_manifest(path).payload
    for endpoint in updated["gateway_authority"].values():
        endpoint["terminal_id"] = "new-runtime-terminal"
        endpoint["profile_name"] = "new-runtime-profile"
    write_session_manifest(path, updated)
    result = update_session_server_gateway_authority(
        path,
        agent_id=stale["agent_id"],
        session_id=stale["runtime"]["session_id"],
        api_base_url="http://127.0.0.1:9012",
        managed_agent_ref="current-server-target",
    )
    for endpoint in result.payload["gateway_authority"].values():
        assert endpoint["terminal_id"] == "new-runtime-terminal"
        assert endpoint["profile_name"] == "new-runtime-profile"
        assert endpoint["api_base_url"] == "http://127.0.0.1:9012"
        assert endpoint["managed_agent_ref"] == "current-server-target"


def test_credential_revision_preserves_online_binding_and_offline_slot(tmp_path: Path) -> None:
    """Foundation slot updates distinguish account identity from credential configuration."""

    path = _manifest(tmp_path)
    initial = load_session_manifest(path).payload
    offline = mutate_session_mailbox_binding(
        path,
        channel="offline",
        expected_revision=initial["launch_plan"]["mailboxes"]["offline"]["revision"],
        binding=_offline(tmp_path / "mail"),
        agent_id="agent-a",
        session_id="session-a",
    )
    online = mutate_session_mailbox_binding(
        path,
        channel="online",
        expected_revision=offline.payload["launch_plan"]["mailboxes"]["online"]["revision"],
        binding=_online(),
        agent_id="agent-a",
        session_id="session-a",
    )
    prior = online.payload["launch_plan"]["mailboxes"]
    changed = mutate_session_mailbox_binding(
        path,
        channel="online",
        expected_revision=prior["online"]["revision"],
        binding=replace(_online(), credential_ref="private/rotated-account-a"),
        agent_id="agent-a",
        session_id="session-a",
    ).payload["launch_plan"]["mailboxes"]
    assert changed["offline"] == prior["offline"]
    assert changed["online"]["revision"] != prior["online"]["revision"]
    assert changed["online"]["binding"]["binding_id"] == prior["online"]["binding"]["binding_id"]
    assert changed["online"]["binding"]["agent_id"] == "agent-a"
    assert changed["online"]["binding"]["credential_ref"] == "private/rotated-account-a"
    assert mailboxes_resolved_config_from_payload(changed).canonical_mail_identity == {
        "channel": "online",
        "address": "alice@example.test",
    }

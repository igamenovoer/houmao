"""Exercise manager reads with a selected record and no terminal access."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import click
from click.testing import CliRunner
import pytest

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_models import (
    GatewayCurrentInstanceV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    write_gateway_current_instance,
    write_gateway_status,
)
from houmao.agents.realm_controller.headless_snapshots import headless_turn_artifacts_root
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    mutate_session_mailbox_binding,
)
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryMailboxesV1,
)
from houmao.agents.realm_controller.registry_storage import (
    load_managed_agent_record_by_agent_id,
    publish_managed_agent_record,
)
from houmao.execution.locators import ExecutorAgentLocatorV1
from houmao.execution.tmux import TmuxServer
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from houmao.srv_ctrl.commands import managed_agents as manager
from houmao.srv_ctrl.commands.agents import gateway
from houmao.srv_ctrl.commands.main import cli
from tests.unit.srv_ctrl.commands.test_self_manifest import _publish_manifest


@pytest.fixture
def selected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, ManagedAgentRegistryRecordV3]:
    """Publish a valid selected owner while denying all terminal and resume I/O."""

    path = _publish_manifest(tmp_path, "claude_headless")
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    monkeypatch.setenv("TMUX", f"{tmp_path / 'caller.sock'},1234,0")
    monkeypatch.setenv("TMUX_PANE", "%1")
    for owner, method in (
        (TmuxServer, "command"),
        (manager, "resume_runtime_session"),
        (manager, "_probe_local_tmux_authority_for_record"),
        (manager, "require_supported_houmao_pair"),
    ):
        monkeypatch.setattr(owner, method, Mock(side_effect=AssertionError(f"Unexpected {method}")))
    record = load_managed_agent_record_by_agent_id("agent-id")
    assert record is not None
    return path, record


def _invoke(*args: str, alias: bool = False) -> click.testing.Result:
    """Invoke the public selected-agent CLI with the synthetic owner."""

    selector = ["--target-tmux-session", "owner-session"] if alias else ["--agent-id", "agent-id"]
    return CliRunner().invoke(cli, ["--print-json", "agents", "single", *selector, *args])


def _write_status(path: Path, *, attached: bool) -> GatewayStatusV1:
    """Save the gateway's published lifecycle evidence."""

    paths = gateway_paths_from_manifest_path(path)
    assert paths is not None
    status = GatewayStatusV1(
        attach_identity="agent-id",
        backend="claude_headless",
        tmux_session_name="owner-session",
        gateway_health="healthy" if attached else "not_attached",
        managed_agent_connectivity="connected" if attached else "unavailable",
        managed_agent_recovery="idle",
        request_admission="open" if attached else "blocked_unavailable",
        terminal_surface_eligibility="ready" if attached else "unknown",
        active_execution="idle",
        queue_depth=0,
        gateway_host="127.0.0.1" if attached else None,
        gateway_port=43123 if attached else None,
        managed_agent_instance_epoch=1 if attached else 0,
        managed_agent_instance_id="body" if attached else None,
    )
    write_gateway_status(paths.state_path, status)
    return status


def _write_instance(
    path: Path, record: ManagedAgentRegistryRecordV3, *, generation: str
) -> GatewayCurrentInstanceV1:
    """Save the owner and listener identity for one gateway instance."""

    paths = gateway_paths_from_manifest_path(path)
    assert paths is not None and record.execution_binding is not None
    descriptor = GatewayEndpointDescriptor.model_validate(
        {
            "protocol": "v1",
            "target": {
                "owner": {
                    "agent_id": record.agent_id,
                    "context_id": record.execution_binding.context_id,
                },
                "incarnation": generation,
            },
            "presence_id": "gateway-instance",
            "advertised_url": None,
            "admin_mode": "open",
        }
    )
    instance = GatewayCurrentInstanceV1(
        pid=123,
        host="127.0.0.1",
        port=43123,
        managed_agent_instance_id="body",
        managed_agent_instance_epoch=1,
        endpoint_descriptor=descriptor,
    )
    write_gateway_current_instance(paths.current_instance_path, instance)
    return instance


@pytest.mark.parametrize("by_name", [False, True])
def test_selection_opens_manifest_only_for_authoritative_read(
    selected: tuple[Path, ManagedAgentRegistryRecordV3], by_name: bool
) -> None:
    """Keep a peer selected even if the caller's enclosing session differs."""

    path, record = selected
    target = manager.resolve_managed_agent_target(
        agent_id=None if by_name else record.agent_id,
        agent_name=record.agent_name if by_name else None,
        port=None,
    )
    assert target.controller is None and target.record == record
    assert target.identity.agent_id == record.agent_id
    authority = manager.read_selected_manifest(target)
    assert (
        authority.manifest_path == path
        and authority.payload.registry_generation_id == record.generation_id
    )
    path.unlink()
    with pytest.raises(manager.ManifestAuthorityUnavailable, match="agent-id.*unavailable"):
        manager.read_selected_manifest(target)


def test_gateway_alias_uses_fresh_registry_and_rejects_ambiguity(
    selected: tuple[Path, ManagedAgentRegistryRecordV3], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolve an alias on the peer's socket and offer exact IDs for duplicate aliases."""

    path, record = selected
    _write_status(path, attached=False)
    result = _invoke("gateway", "status", alias=True)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["gateway_health"] == "not_attached"
    duplicate = record.model_copy(update={"agent_id": "other-agent", "agent_name": "other-name"})
    monkeypatch.setattr(
        gateway,
        "resolve_live_agent_records_by_terminal_session_name",
        lambda _: (record, duplicate),
    )
    result = _invoke("gateway", "status", alias=True)
    assert result.exit_code != 0
    assert "agent_id=agent-id" in result.output
    assert "agent_id=other-agent" in result.output
    assert "Retry with `--agent-id <id>`" in result.output
    result = _invoke("gateway", "status", "--pair-port", "9999", alias=True)
    assert result.exit_code != 0 and "--pair-port" in result.output


@pytest.mark.parametrize("condition", ["matching", "stale", "wrong_listener", "unreachable"])
def test_gateway_and_mail_verify_current_owner_evidence(
    selected: tuple[Path, ManagedAgentRegistryRecordV3],
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
) -> None:
    """Use a live instance only when the endpoint and saved generation agree."""

    path, record = selected
    status = _write_status(path, attached=True)
    generation = "old-generation" if condition == "stale" else record.generation_id
    instance = _write_instance(path, record, generation=generation)
    descriptor = instance.endpoint_descriptor
    assert descriptor is not None
    if condition == "wrong_listener":
        descriptor = descriptor.model_copy(update={"presence_id": "different-process"})
    describe = Mock(return_value=descriptor)
    if condition == "unreachable":
        describe.side_effect = GatewayHttpError(
            method="GET", url="http://127.0.0.1:43123/v1/endpoint", detail="unreachable"
        )
    monkeypatch.setattr(
        manager,
        "GatewayClient",
        lambda **_: SimpleNamespace(describe_endpoint=describe, status=lambda: status),
    )
    monkeypatch.setattr(
        manager, "owner_gateway_client_binding", lambda *_, **__: (None, record.generation_id)
    )
    result = _invoke("mail", "resolve-live")
    assert result.exit_code == 0, result.output
    mail = json.loads(result.output)
    assert mail["source"] == "manifest_binding"
    assert mail["gateway_available"] is (condition == "matching")
    result = _invoke("gateway", "status")
    if condition == "matching":
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["gateway_health"] == "healthy"
    else:
        assert result.exit_code != 0
        assert "Gateway status unavailable for `agent-id`" in result.output
    if condition == "stale":
        describe.assert_not_called()


def test_mail_discovery_retains_redacted_contact_without_manifest(
    tmp_path: Path, selected: tuple[Path, ManagedAgentRegistryRecordV3]
) -> None:
    """Use manifest slots when readable and only published contact after their loss."""

    path, record = selected
    binding = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        agent_id=record.agent_id,
        principal_id=record.agent_id,
        binding_id="offline-contact",
        address="agent@agents.localhost",
        filesystem_root=tmp_path / "private-mail",
        bindings_version="offline-configured",
    )
    revision = load_session_manifest(path).payload["launch_plan"]["mailboxes"]["offline"][
        "revision"
    ]
    mutate_session_mailbox_binding(
        path,
        channel="offline",
        expected_revision=revision,
        binding=binding,
        agent_id=record.agent_id,
        session_id="session-id",
    )
    mailboxes = RegistryMailboxesV1.model_validate(
        {
            "offline": {
                "revision": "offline-configured",
                "binding": {
                    "agent_id": record.agent_id,
                    "channel": "offline",
                    "binding_id": binding.binding_id,
                    "address": binding.address,
                    "transport": "filesystem",
                    "availability": "configured",
                },
            },
            "online": {"revision": "online-empty", "binding": None},
        }
    )
    publish_managed_agent_record(
        record.model_copy(
            update={
                "mailboxes": mailboxes,
                "canonical_mail_identity": mailboxes.canonical_mail_identity,
            }
        )
    )
    result = _invoke("mail", "resolve-live")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["source"] == "manifest_binding"
    path.unlink()
    result = _invoke("mail", "resolve-live")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["source"] == "registry_projection"
    assert payload["gateway"] is None
    slot = payload["mailboxes"]["offline"]
    assert slot["availability"] == "unverified" and slot["binding"]["address"] == binding.address
    assert "private-mail" not in result.output


def test_saved_turn_reads_stay_confined_and_require_the_selected_generation(
    tmp_path: Path, selected: tuple[Path, ManagedAgentRegistryRecordV3]
) -> None:
    """Read a saved headless turn and reject escaped artifacts or stale authority."""

    path, _ = selected
    turn = headless_turn_artifacts_root(path) / "turn-0001"
    turn.mkdir(parents=True)
    stdout = '{"type":"result","subtype":"success","result":"saved answer"}\n'
    (turn / "stdout.jsonl").write_text(stdout, encoding="utf-8")
    (turn / "stderr.log").write_text("saved diagnostic\n", encoding="utf-8")
    (turn / "exitcode").write_text("0\n", encoding="utf-8")

    result = _invoke("turn", "status", turn.name)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "completed"
    result = _invoke("turn", "events", turn.name)
    assert result.exit_code == 0, result.output
    assert "saved answer" in result.output
    assert _invoke("turn", "stdout", turn.name).output == stdout
    assert _invoke("turn", "stderr", turn.name).output == "saved diagnostic\n"
    outside = tmp_path / "outside.txt"
    outside.write_text("outside authority", encoding="utf-8")
    (turn / "stdout.jsonl").unlink()
    (turn / "stdout.jsonl").symlink_to(outside)
    result = _invoke("turn", "stdout", turn.name)
    assert result.exit_code != 0 and "runtime-owned" in result.output
    assert "outside authority" not in result.output
    result = _invoke("turn", "status", f"../{turn.name}")
    assert result.exit_code != 0 and "not found" in result.output

    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["registry_generation_id"] = "replacement-generation"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    for args in (("turn", "status", turn.name), ("mail", "resolve-live"), ("gateway", "status")):
        result = _invoke(*args)
        assert result.exit_code != 0 and "Cannot verify saved runtime authority" in result.output


def test_visible_executor_contact_needs_no_live_owner_route(
    selected: tuple[Path, ManagedAgentRegistryRecordV3], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use a consistent published record when the finite owner route is unavailable."""

    _, record = selected
    binding = record.execution_binding
    assert binding is not None
    locator = ExecutorAgentLocatorV1(
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        tool=record.identity.tool,
        mode=record.mode,
        backend=record.identity.backend,
        profile_name=binding.profile_name,
        binding=binding,
    )
    monkeypatch.setattr(manager, "resolve_executor_locator", lambda **_: locator)
    monkeypatch.setattr(
        manager,
        "_execute_executor_operation",
        Mock(side_effect=AssertionError("published contact does not require delegation")),
    )
    result = _invoke("mail", "resolve-live")
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["managed_agent"]["mode"] == "executor"
    assert payload["source"] == "registry_projection"
    assert payload["gateway"] is None

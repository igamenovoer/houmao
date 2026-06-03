from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.gateway_models import GatewayStatusV1
from houmao.agents.realm_controller.registry_models import (
    ExternalManagedAgentRegistryRecordV1,
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import (
    DEFAULT_REGISTRY_LEASE_TTL,
    new_external_agent_id,
    publish_external_managed_agent_record,
    publish_managed_agent_record,
)
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR
from houmao.server.models import (
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTurnView,
    HoumaoManagedAgentMailStatusResponse,
)
from houmao.srv_ctrl.commands.main import cli
from houmao.srv_ctrl.commands.managed_agents import (
    gateway_status,
    mail_status,
    managed_agent_state_payload,
    prompt_managed_agent,
    resolve_managed_agent_target,
    stop_managed_agent,
)
from houmao.srv_ctrl.commands.runtime_cleanup import (
    CleanupResolutionError,
    cleanup_managed_session,
)


def _identity() -> HoumaoManagedAgentIdentity:
    """Return one remote managed-agent identity for external tests."""

    return HoumaoManagedAgentIdentity(
        tracked_agent_id="remote-tracked",
        transport="headless",
        tool="codex",
        agent_name="remote-worker",
        agent_id="remote-agent-id",
        lifecycle_state="active",
    )


def _external_record(*, local_name: str = "remote-a") -> ExternalManagedAgentRegistryRecordV1:
    """Return one external registry record."""

    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    return ExternalManagedAgentRegistryRecordV1(
        local_name=local_name,
        external_agent_id=new_external_agent_id(),
        generation_id="external-generation-1",
        pair_api_base_url="http://127.0.0.1:9899",
        remote_agent_ref="remote-ref",
        gateway_expected=True,
        created_at_utc=timestamp,
        updated_at_utc=timestamp,
        verified_at_utc=timestamp,
        cached_identity=_identity(),
    )


def _local_record(*, agent_name: str) -> ManagedAgentRegistryRecordV3:
    """Return one active local lifecycle registry record."""

    published_at = datetime.now(UTC)
    return ManagedAgentRegistryRecordV3(
        agent_name=agent_name,
        agent_id=derive_agent_id_from_name(agent_name),
        generation_id="local-generation-1",
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=True,
            state_updated_at=published_at.isoformat(timespec="seconds"),
        ),
        identity=RegistryIdentityV1(backend="houmao_server_rest", tool="codex"),
        runtime=RegistryRuntimeV1(
            manifest_path="/tmp/runtime/session/manifest.json",
            session_root="/tmp/runtime/session",
            agent_def_dir="/tmp/agents",
        ),
        terminal=RegistryTerminalV2(
            current_session_name=agent_name,
            last_session_name=agent_name,
        ),
        liveness=RegistryLivenessV1(
            published_at=published_at.isoformat(timespec="seconds"),
            lease_expires_at=(published_at + DEFAULT_REGISTRY_LEASE_TTL).isoformat(
                timespec="seconds"
            ),
        ),
    )


def _state_response(identity: HoumaoManagedAgentIdentity) -> HoumaoManagedAgentStateResponse:
    """Return one remote state payload."""

    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available",
        turn=HoumaoManagedAgentTurnView(phase="ready"),
        last_turn=HoumaoManagedAgentLastTurnView(result="none"),
    )


def _gateway_status() -> GatewayStatusV1:
    """Return one healthy remote gateway status."""

    return GatewayStatusV1(
        attach_identity="remote-ref",
        backend="codex_headless",
        tmux_session_name="remote-tmux",
        gateway_health="healthy",
        managed_agent_connectivity="connected",
        managed_agent_recovery="idle",
        request_admission="open",
        terminal_surface_eligibility="ready",
        active_execution="idle",
        queue_depth=0,
        gateway_host="127.0.0.1",
        gateway_port=9901,
        managed_agent_instance_epoch=1,
    )


class _FakePairClient:
    """Minimal pair client for external-routing unit tests."""

    pair_authority_kind = "houmao-passive-server"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.identity = _identity()

    def get_managed_agent(self, agent_ref: str) -> HoumaoManagedAgentIdentity:
        self.calls.append(("get", (agent_ref,)))
        return self.identity

    def get_managed_agent_state(self, agent_ref: str) -> HoumaoManagedAgentStateResponse:
        self.calls.append(("state", (agent_ref,)))
        return _state_response(self.identity)

    def submit_managed_agent_request(
        self,
        agent_ref: str,
        request_model: object,
    ) -> HoumaoManagedAgentRequestAcceptedResponse:
        self.calls.append(("submit", (agent_ref, request_model)))
        return HoumaoManagedAgentRequestAcceptedResponse(
            success=True,
            tracked_agent_id="remote-tracked",
            request_id="req-1",
            request_kind="submit_prompt",
            disposition="accepted",
            detail="accepted",
        )

    def get_managed_agent_gateway_status(self, agent_ref: str) -> GatewayStatusV1:
        self.calls.append(("gateway_status", (agent_ref,)))
        return _gateway_status()

    def get_managed_agent_mail_status(
        self,
        agent_ref: str,
    ) -> HoumaoManagedAgentMailStatusResponse:
        self.calls.append(("mail_status", (agent_ref,)))
        return HoumaoManagedAgentMailStatusResponse(
            transport="filesystem",
            principal_id="remote-ref",
            address="remote-ref@agents.localhost",
            bindings_version="2026-05-29T00:00:00Z",
        )


def test_external_target_routes_state_prompt_gateway_and_mail_to_remote_pair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(registry_root))
    record = publish_external_managed_agent_record(_external_record(local_name="remote-a"))
    fake_client = _FakePairClient()
    captured_base_urls: list[str] = []

    def _fake_require_pair(*, base_url: str, **kwargs: object) -> _FakePairClient:
        del kwargs
        captured_base_urls.append(base_url)
        return fake_client

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        _fake_require_pair,
    )

    target = resolve_managed_agent_target(agent_id=None, agent_name="remote-a", port=None)
    state = managed_agent_state_payload(target)
    prompt_result = prompt_managed_agent(target, prompt="hello")
    status = gateway_status(target)
    mail_result = mail_status(target)

    assert target.mode == "external"
    assert target.agent_ref == "remote-ref"
    assert target.external_record == record
    assert captured_base_urls == ["http://127.0.0.1:9899"]
    assert state.tracked_agent_id == record.external_agent_id
    assert state.identity.agent_name == "remote-a"
    assert state.identity.remote_pair_api_base_url == "http://127.0.0.1:9899"
    assert prompt_result.request_kind == "submit_prompt"
    assert status.attach_identity == "remote-ref"
    assert mail_result["execution_path"] == "gateway_backed"
    assert [name for name, _ in fake_client.calls] == [
        "state",
        "submit",
        "gateway_status",
        "mail_status",
    ]


def test_external_target_rejects_local_lifecycle_operations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_external_managed_agent_record(_external_record(local_name="remote-a"))
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: _FakePairClient(),
    )
    target = resolve_managed_agent_target(agent_id=None, agent_name="remote-a", port=None)

    with pytest.raises(click.ClickException) as exc_info:
        stop_managed_agent(target)

    detail = str(exc_info.value)
    assert "external communication-only" in detail
    assert "http://127.0.0.1:9899" in detail
    assert "remote-ref" in detail
    assert "agents single ... prompt" in detail


def test_external_cleanup_selector_is_rejected_before_local_scan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_external_managed_agent_record(_external_record(local_name="remote-a"))

    with pytest.raises(CleanupResolutionError) as exc_info:
        cleanup_managed_session(
            agent_id=None,
            agent_name="remote-a",
            manifest_path=None,
            session_root=None,
            dry_run=True,
            purge_registry=False,
        )

    assert "external communication-only" in str(exc_info.value)
    assert "agents external remove" in str(exc_info.value)


def test_external_resolution_preserves_local_lifecycle_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_external_managed_agent_record(_external_record(local_name="same-name"))
    publish_managed_agent_record(_local_record(agent_name="same-name"))

    with pytest.raises(click.ClickException, match="retired backend `houmao_server_rest`"):
        resolve_managed_agent_target(agent_id=None, agent_name="same-name", port=None)


def test_external_resolution_does_not_intercept_explicit_port(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, str(tmp_path / "registry"))
    publish_external_managed_agent_record(_external_record(local_name="remote-a"))
    fake_client = _FakePairClient()
    captured: dict[str, object] = {}

    def _fake_require_pair(*, base_url: str, **kwargs: object) -> _FakePairClient:
        del kwargs
        captured["base_url"] = base_url
        return fake_client

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        _fake_require_pair,
    )

    target = resolve_managed_agent_target(agent_id=None, agent_name="remote-a", port=9911)

    assert target.mode == "server"
    assert target.external_record is None
    assert captured["base_url"] == "http://127.0.0.1:9911"
    assert fake_client.calls == [("get", ("remote-a",))]


def test_external_cli_register_wires_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_register(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"action": "registered", "external_agent": {"local_name": kwargs["local_name"]}}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.external.register_external_managed_agent",
        _fake_register,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "external",
            "register",
            "--name",
            "remote-a",
            "--api-base-url",
            "http://127.0.0.1:9899",
            "--agent-ref",
            "remote-ref",
            "--gateway-enabled",
            "--replace",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {
        "local_name": "remote-a",
        "api_base_url": "http://127.0.0.1:9899",
        "agent_ref": "remote-ref",
        "gateway_expected": True,
        "replace": True,
    }
    assert json.loads(result.output)["action"] == "registered"


@pytest.mark.parametrize(
    ("argv", "patch_name"),
    [
        (["agents", "external", "list"], "list_external_managed_agents"),
        (
            ["agents", "external", "get", "--agent-name", "remote-a"],
            "get_external_managed_agent",
        ),
        (
            ["agents", "external", "verify", "--agent-name", "remote-a"],
            "verify_external_managed_agent",
        ),
        (
            ["agents", "external", "remove", "--agent-name", "remote-a"],
            "remove_external_managed_agent",
        ),
    ],
)
def test_external_cli_list_get_verify_remove_wiring(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    patch_name: str,
) -> None:
    captured: dict[str, object] = {}

    def _fake_command(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"external_agent": {"local_name": "remote-a"}}

    def _fake_list() -> dict[str, object]:
        captured["listed"] = True
        return {"external_agents": [{"local_name": "remote-a"}]}

    monkeypatch.setattr(
        f"houmao.srv_ctrl.commands.agents.external.{patch_name}",
        _fake_list if patch_name == "list_external_managed_agents" else _fake_command,
    )

    result = CliRunner().invoke(cli, ["--print-json", *argv])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload
    if patch_name == "list_external_managed_agents":
        assert captured == {"listed": True}
    else:
        assert captured == {"agent_id": None, "agent_name": "remote-a"}

"""Exercise shared native settings and stale cancellation on the DSH service adapter."""

from __future__ import annotations

from concurrent.futures import Future
import json
from pathlib import Path
import time
from typing import Any
from unittest.mock import Mock

import pytest

from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dsh_acp_connection import DshAcpProtocolError
from houmao.agents.realm_controller.backends.dsh_acp_service import DshAcpServiceProvider
from houmao.agents.realm_controller.backends import dsh_acp_service
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
    ServiceOwnerConfig,
    ServicePromptResult,
)


def _model_options(current: str) -> list[dict[str, Any]]:
    """Advertise the same opaque IDs and provider grouping as native DSH ACP."""

    return [
        {
            "id": "model",
            "type": "select",
            "currentValue": json.dumps(["route", current]),
            "options": [
                {
                    "group": "route",
                    "options": [
                        {"value": json.dumps(["route", value])}
                        for value in ("default", "alternate")
                    ],
                }
            ],
        }
    ]


@pytest.fixture
def provider(tmp_path: Path) -> DshAcpServiceProvider:
    """Construct a service ready for deterministic protocol sequences."""

    selected = DshAcpServiceProvider(
        ServiceOwnerConfig(
            backend="dsh_acp",
            executable="unused",
            arguments=[],
            working_directory=tmp_path,
            home_path=tmp_path,
            environment={},
            metadata={},
            root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            agent_id="agent",
            runtime_session_id="runtime",
            generation_id="generation",
            service_incarnation="incarnation",
        )
    )
    selected.m_connection = Mock(healthy=True)
    selected.m_session_id = "native"
    selected.m_route = "route"
    selected.m_options = _model_options("default")
    return selected


@pytest.mark.parametrize("failure", [None, "set", "restore", "unresolved_set"])
def test_service_restores_session_settings_before_releasing_slot(
    provider: DshAcpServiceProvider,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
) -> None:
    """Original settings survive a rejected set or a correlated cancelled prompt."""

    settings_calls: list[str] = []

    def request(method: str, parameters: dict[str, Any]) -> Future[dict[str, Any]]:
        """Simulate a native set that can fail after reaching the provider."""

        assert method == "session/set_config_option"
        assert parameters["sessionId"] == "native"
        value = json.loads(parameters["value"])[1]
        settings_calls.append(value)
        future: Future[dict[str, Any]] = Future()
        if failure == "unresolved_set" and value == "alternate":
            return future
        if (failure, value) in {("set", "alternate"), ("restore", "default")}:
            future.set_exception(DshAcpProtocolError("native setting reply was lost"))
        else:
            future.set_result({"configOptions": _model_options(value)})
        return future

    assert provider.m_connection is not None
    provider.m_connection.request.side_effect = request
    monkeypatch.setattr(dsh_acp_service, "_SETUP_TIMEOUT", 0.01)

    def cancelled(
        _prompt: str, _operation: ServiceOperationContext, *, already_authorized: bool
    ) -> ServicePromptResult:
        """Report real cancellation semantics while the temporary setting owns the slot."""

        assert provider.m_active_request == "first"
        assert provider.m_options == _model_options("alternate")
        assert already_authorized
        return ServicePromptResult(outcome="interrupted", native_turn_id="1")

    monkeypatch.setattr(provider, "_run_prompt", cancelled)
    operation = ServiceOperationContext("first", tmp_path / "first", Mock(), Mock(), Mock())
    result = provider.prompt(
        "controlled", execution_model=ModelConfig(name="alternate"), operation=operation
    )
    assert (
        result.outcome
        == {
            None: "interrupted",
            "set": "failed",
            "restore": "uncertain",
            "unresolved_set": "uncertain",
        }[failure]
    )
    assert settings_calls == (
        ["alternate"] if failure == "unresolved_set" else ["alternate", "default"]
    )
    assert provider.connection_ready is (failure not in {"restore", "unresolved_set"})
    if provider.connection_ready:
        assert provider.m_options == _model_options("default")
    assert provider.m_active_request is None


def test_service_cancel_never_reaches_the_next_prompt(provider: DshAcpServiceProvider) -> None:
    """A stale or settled request cannot issue a native session-scoped cancellation."""

    old: Future[dict[str, Any]] = Future()
    new: Future[dict[str, Any]] = Future()
    provider.m_active_request = "old"
    provider.m_pending = old
    old.set_result({"stopReason": "end_turn"})
    assert not provider.cancel("old")
    provider.m_active_request = "new"
    provider.m_pending = new
    assert not provider.cancel("old")
    assert provider.cancel("new")
    assert provider.cancel("new")
    assert provider.m_connection is not None
    provider.m_connection.notify.assert_called_once_with("session/cancel", {"sessionId": "native"})


def test_native_arm_rechecks_revocation_and_incarnation_at_followup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owned protocol write alone cannot admit an expired or retired native arm."""

    manifest = tmp_path / "manifest.json"
    backend = {"service_incarnation": "incarnation", "native_session_id": "native"}
    payload = {
        "backend": "dsh_acp",
        "registry_generation_id": "generation",
        "backend_state": backend,
    }
    manifest.write_text(json.dumps(payload))
    arm = tmp_path / "arm.json"
    proof = {
        "version": 1,
        "generation": "generation",
        "service_incarnation": "incarnation",
        "request_id": "request",
        "native_session_id": "native",
        "process_id": 123,
        "process_birth_token": "native-birth",
        "owner_pid": 101,
        "owner_birth_token": "owner-birth",
        "expires_at": time.time() + 15,
    }
    arm.write_text(json.dumps(proof))
    guard = tmp_path / "manifest.turn-artifacts/request/.dispatch-permission.json"
    guard.parent.mkdir(parents=True)
    permission = {
        "active": True,
        "expires_at": time.time() + 15,
        "origin_pid": 111,
        "origin_birth_token": "caller-birth",
        "registry_generation_id": "generation",
        "manifest_path": str(manifest),
        "attempt_id": "request",
    }
    guard.write_text(json.dumps(permission))
    monkeypatch.setattr(
        dsh_acp_service,
        "_dispatch_origin_birth_token",
        {101: "owner-birth", 123: "native-birth"}.get,
    )
    monkeypatch.setattr(dsh_acp_service.OwnerPromptClaim, "active", lambda _: True)
    monkeypatch.setattr(
        dsh_acp_service,
        "headless_dispatch_permission_allowed",
        lambda path: json.loads(path.read_text())["active"],
    )
    args = [str(arm), str(manifest), "generation", "incarnation", "request", "native", "123"]
    assert dsh_acp_service._verify_native_arm(args)
    guard.write_text(json.dumps({**permission, "active": False}))
    assert not dsh_acp_service._verify_native_arm(args)
    guard.write_text(json.dumps(permission))
    backend["service_incarnation"] = "replacement"
    manifest.write_text(json.dumps(payload))
    assert not dsh_acp_service._verify_native_arm(args)

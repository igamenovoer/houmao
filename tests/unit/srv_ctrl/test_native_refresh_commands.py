"""Verify scoped native-home/refresh commands and their authority boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

from click.testing import CliRunner
import click
import pytest

from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeHomeV1,
    NativeRefreshResultV1,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands import managed_agents as helpers
from houmao.srv_ctrl.commands.agents import core
from houmao.srv_ctrl.commands.main import cli


def _home() -> NativeHomeV1:
    """Use a distinct native home rather than the caller's home."""

    return NativeHomeV1(
        agent_id="agent", backend="dsh_acp", tool="dsh", home_dir="/selected/native-home"
    )


def _observation(
    freshness: str = "unknown", *, automatic: bool = False
) -> CommonPluginObservationV1:
    """Construct complete current evidence or explicit future/unknown coverage."""

    return CommonPluginObservationV1.model_validate(
        {
            "home": _home().model_dump(),
            "freshness": freshness,
            "coverage_complete": freshness == "current",
            "automatic": automatic,
            "resources": [
                {
                    "kind": kind,
                    "component": "native",
                    "freshness": freshness,
                    "complete": freshness == "current",
                    "supported": freshness == "current" or automatic,
                    "boundary": "next_turn" if automatic else "now",
                }
                for kind in ("skills", "mcp")
            ],
        }
    )


def _result(outcome: str) -> NativeRefreshResultV1:
    """Retain public diagnostics/effects on both successful and refused outcomes."""

    current = outcome in {"already_current", "refreshed"}
    method = {"already_current": "noop", "automatic": "automatic"}.get(outcome, "native_reload")
    return NativeRefreshResultV1.model_validate(
        {
            "method": method,
            "outcome": outcome,
            "observation": _observation(
                "current" if current else "unknown", automatic=outcome == "automatic"
            ).model_dump(),
            "effects": "partial" if outcome == "partial" else "absent",
            "diagnostics": ["native_diagnostic_preserved"],
        }
    )


def _target(
    tmp_path: Path, *, mode: str = "local", lifecycle: str = "active"
) -> helpers.ManagedAgentTarget:
    """Provide local authority without starting tmux or a body process."""

    identity = HoumaoManagedAgentIdentity.model_validate(
        {
            "tracked_agent_id": "agent",
            "agent_id": "agent",
            "transport": "headless",
            "tool": "dsh",
            "lifecycle_state": lifecycle,
        }
    )
    controller = cast(
        RuntimeSessionController,
        SimpleNamespace(manifest_path=tmp_path / "manifest.json", backend_session=Mock()),
    )
    return helpers.ManagedAgentTarget(
        mode=mode, agent_ref="agent", identity=identity, controller=controller
    )


@pytest.mark.parametrize("command", ["home", "refresh"])
@pytest.mark.parametrize("scope", ["single", "self"])
def test_native_commands_use_existing_scope_and_root_json(
    monkeypatch: pytest.MonkeyPatch, command: str, scope: str
) -> None:
    """Scoped commands inherit one target while JSON preserves the typed contract."""

    target = Mock()
    resolver = Mock(return_value=target)
    monkeypatch.setattr(core, "resolve_managed_agent_target", resolver)
    payload = _home() if command == "home" else _result("automatic")
    handler = Mock(return_value=payload)
    monkeypatch.setattr(
        core, "managed_agent_native_home" if command == "home" else "refresh_managed_agent", handler
    )
    selector = ["--agent-id", "agent"] if scope == "single" else []
    result = CliRunner().invoke(cli, ["--print-json", "agents", scope, *selector, command])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == payload.model_dump(mode="json")
    resolver.assert_called_once_with(
        agent_id="agent" if scope == "single" else None, agent_name=None, port=None
    )
    assert handler.call_args.args == (target,)


def test_home_plain_output_is_the_selected_native_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plain home output can be copied directly into an external editing command."""

    monkeypatch.setattr(core, "resolve_managed_agent_target", Mock())
    monkeypatch.setattr(core, "managed_agent_native_home", lambda _: _home())
    result = CliRunner().invoke(
        cli, ["--print-plain", "agents", "single", "--agent-name", "selected", "home"]
    )
    assert result.exit_code == 0
    assert result.output == "/selected/native-home\n"


@pytest.mark.parametrize("scope", ["single", "self"])
def test_help_separates_home_refresh_check_and_explicit_relaunch(scope: str) -> None:
    """An operator can find inspection and non-restarting refresh beside relaunch."""

    runner = CliRunner()
    group = runner.invoke(cli, ["agents", scope, "--help"])
    assert group.exit_code == 0
    assert all(name in group.output for name in ("home", "refresh", "relaunch"))
    selector = ["--agent-id", "selected"] if scope == "single" else []
    home = runner.invoke(cli, ["agents", scope, *selector, "home", "--help"])
    assert home.exit_code == 0 and "native home" in home.output
    refresh = runner.invoke(cli, ["agents", scope, *selector, "refresh", "--help"])
    assert refresh.exit_code == 0
    assert "--check" in refresh.output
    assert "without reload" in refresh.output
    assert "never restarts" in refresh.output


@pytest.mark.parametrize(
    "freshness,ready,expected",
    [("current", True, 0), ("current", False, 1), ("pending", True, 1), ("unknown", True, 1)],
)
def test_check_is_read_only_and_prints_evidence_before_exit(
    monkeypatch: pytest.MonkeyPatch, freshness: str, ready: bool, expected: int
) -> None:
    """Pending and unknown checks retain evidence and never invoke refresh."""

    monkeypatch.setattr(core, "resolve_managed_agent_target", Mock())
    observation = _observation(freshness)
    observation.native_ready = ready
    monkeypatch.setattr(core, "managed_agent_common_plugin_state", lambda _: observation)
    mutation = Mock(side_effect=AssertionError("check must not refresh"))
    monkeypatch.setattr(core, "refresh_managed_agent", mutation)
    result = CliRunner().invoke(cli, ["--print-json", "agents", "self", "refresh", "--check"])
    assert result.exit_code == expected
    assert json.loads(result.output) == observation.model_dump(mode="json")
    mutation.assert_not_called()


@pytest.mark.parametrize(
    "outcome,expected",
    [
        ("already_current", 0),
        ("refreshed", 0),
        ("automatic", 0),
        ("partial", 1),
        ("restart_required", 1),
        ("busy", 1),
        ("unsupported", 1),
        ("failed", 1),
        ("outcome_unknown", 1),
        ("unavailable", 1),
    ],
)
def test_refresh_exits_from_typed_outcome_without_losing_native_effects(
    monkeypatch: pytest.MonkeyPatch, outcome: str, expected: int
) -> None:
    """Typed refusal output remains available to both operators and JSON consumers."""

    monkeypatch.setattr(core, "resolve_managed_agent_target", Mock())
    payload = _result(outcome)
    action = Mock(return_value=payload)
    monkeypatch.setattr(core, "refresh_managed_agent", action)
    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "single",
            "--agent-id",
            "agent",
            "refresh",
            "--timeout-seconds",
            "7",
        ],
    )
    assert result.exit_code == expected
    assert json.loads(result.output) == payload.model_dump(mode="json")
    assert action.call_args.kwargs == {"timeout_seconds": 7.0}


@pytest.mark.parametrize(
    "limitation", ["missing_mcp", "unknown_boundary", "not_ready", "unsettled"]
)
def test_automatic_exit_requires_full_qualified_coverage(limitation: str) -> None:
    """An automatic flag alone cannot turn missing coverage or readiness into success."""

    payload = _result("automatic")
    if limitation == "missing_mcp":
        payload.observation.resources = payload.observation.resources[:1]
    elif limitation == "unknown_boundary":
        payload.observation.resources[1].boundary = "unknown"
    elif limitation == "not_ready":
        payload.observation.native_ready = False
    else:
        payload.native_settled = False
    assert not core._native_refresh_succeeded(payload)


@pytest.mark.parametrize("option", ["--force", "--restart", "--install", "--agent-id"])
def test_refresh_rejects_unavailable_authority_and_mutation_flags_before_resolution(
    monkeypatch: pytest.MonkeyPatch, option: str
) -> None:
    """The refresh surface provides neither content installation nor lifecycle authority."""

    resolver = Mock()
    monkeypatch.setattr(core, "resolve_managed_agent_target", resolver)
    result = CliRunner().invoke(cli, ["agents", "self", "refresh", option])
    assert result.exit_code == 2
    resolver.assert_not_called()


@pytest.mark.parametrize("timeout", ["0", "-1", "121", "nan", "inf"])
def test_invalid_native_deadline_fails_before_target_resolution(
    monkeypatch: pytest.MonkeyPatch, timeout: str
) -> None:
    """Invalid deadlines never reach a gateway, controller, or native process."""

    resolver = Mock()
    monkeypatch.setattr(core, "resolve_managed_agent_target", resolver)
    result = CliRunner().invoke(cli, ["agents", "self", "refresh", "--timeout-seconds", timeout])
    assert result.exit_code == 2
    resolver.assert_not_called()


@pytest.mark.parametrize("scope", ["global", "external"])
@pytest.mark.parametrize("command", ["home", "refresh"])
def test_native_commands_are_absent_from_fleet_and_external_scopes(
    scope: str, command: str
) -> None:
    """Body controls remain limited to single/self scope."""

    result = CliRunner().invoke(cli, ["agents", scope, command])
    assert result.exit_code == 2
    assert "No such command" in result.output


@pytest.mark.parametrize("selectors", [[], ["--agent-id", "agent", "--agent-name", "name"]])
def test_single_native_command_never_infers_an_agent(selectors: list[str]) -> None:
    """A selected-agent body operation requires exactly one explicit selector."""

    result = CliRunner().invoke(cli, ["agents", "single", *selectors, "home"])
    assert result.exit_code != 0


def test_self_native_home_requires_current_session_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing self binding never falls back to server or selected-agent inference."""

    current = Mock(
        side_effect=click.ClickException("Current managed-session authority is unavailable")
    )
    monkeypatch.setattr(helpers, "resolve_current_session_managed_agent_target", current)
    fallback = Mock(side_effect=AssertionError("self cannot infer another agent"))
    monkeypatch.setattr(helpers, "require_supported_houmao_pair", fallback)
    result = CliRunner().invoke(cli, ["agents", "self", "home"])
    assert result.exit_code == 1
    assert "Current managed-session authority is unavailable" in result.output
    current.assert_called_once_with(read_only=False)
    fallback.assert_not_called()


def test_detached_local_reads_and_automatic_refresh_never_mutate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local authority permits passive reads and qualified future results without attach."""

    target = _target(tmp_path)
    monkeypatch.setattr(helpers, "gateway_paths_from_manifest_path", lambda _: None)
    monkeypatch.setattr(helpers, "inspect_native_home", lambda _: _home())
    observation = _observation(automatic=True)
    monkeypatch.setattr(helpers, "observe_common_plugins", lambda _: observation)
    assert helpers.managed_agent_native_home(target) == _home()
    assert helpers.managed_agent_common_plugin_state(target) is observation
    refreshed = helpers.refresh_managed_agent(target)
    assert refreshed.outcome == "automatic"
    assert refreshed.effects == "absent"
    cast(Any, target.controller).backend_session.refresh_common_plugins.assert_not_called()


def test_detached_local_reload_returns_typed_attachment_limitation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native reload capability does not authorize bypassing gateway admission."""

    target = _target(tmp_path)
    monkeypatch.setattr(helpers, "gateway_paths_from_manifest_path", lambda _: None)
    observation = _observation()
    observation.native_reload = True
    monkeypatch.setattr(helpers, "observe_common_plugins", lambda _: observation)
    result = helpers.refresh_managed_agent(target)
    assert result.outcome == "unsupported"
    assert result.diagnostics == ["gateway_attachment_required"]
    assert result.observation is observation
    cast(Any, target.controller).backend_session.refresh_common_plugins.assert_not_called()


@pytest.mark.parametrize("operation", ["home", "check", "refresh"])
def test_attached_gateway_unavailability_never_falls_back_to_local_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """An attached authority's refusal cannot authorize another control route."""

    target = _target(tmp_path)
    monkeypatch.setattr(helpers, "gateway_paths_from_manifest_path", lambda _: Mock())
    monkeypatch.setattr(helpers, "_live_gateway_client_for_controller", lambda _: None)
    monkeypatch.setattr(
        helpers,
        "_gateway_status_for_controller",
        lambda _: SimpleNamespace(gateway_health="healthy"),
    )
    fallback = Mock(side_effect=AssertionError("no local fallback"))
    monkeypatch.setattr(helpers, "observe_common_plugins", fallback)
    monkeypatch.setattr(helpers, "inspect_native_home", fallback)
    action = {
        "home": helpers.managed_agent_native_home,
        "check": helpers.managed_agent_common_plugin_state,
        "refresh": helpers.refresh_managed_agent,
    }[operation]
    with pytest.raises(click.ClickException, match="attached gateway is unavailable"):
        action(target)
    fallback.assert_not_called()


@pytest.mark.parametrize("operation", ["home", "check", "refresh"])
@pytest.mark.parametrize("changed", ["agent_id", "home_dir", "backend", "generation"])
def test_reused_gateway_port_cannot_select_another_native_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str, changed: str
) -> None:
    """A healthy unrelated gateway cannot replace the selected local authority."""

    target = _target(tmp_path)
    expected = _home().model_copy(update={"identity": {"generation": "selected-generation"}})
    actual = expected.model_copy(
        update={
            "identity": {"generation": "other-generation"},
        }
        if changed == "generation"
        else {changed: "other"}
    )
    client = Mock(spec=GatewayClient)
    client.get_native_home.return_value = actual
    monkeypatch.setattr(helpers, "gateway_paths_from_manifest_path", lambda _: Mock())
    monkeypatch.setattr(helpers, "_live_gateway_client_for_controller", lambda _: client)
    inspect = Mock(return_value=expected)
    monkeypatch.setattr(helpers, "inspect_native_home", inspect)
    fallback = Mock(side_effect=AssertionError("no local fallback"))
    monkeypatch.setattr(helpers, "observe_common_plugins", fallback)
    action = {
        "home": helpers.managed_agent_native_home,
        "check": helpers.managed_agent_common_plugin_state,
        "refresh": helpers.refresh_managed_agent,
    }[operation]
    with pytest.raises(click.ClickException, match="different native execution"):
        action(target)
    inspect.assert_called_once_with(target.controller)
    client.get_native_home.assert_called_once_with()
    client.bind_native_home.assert_not_called()
    client.get_common_plugin_state.assert_not_called()
    client.refresh_native.assert_not_called()
    fallback.assert_not_called()


def test_attached_refresh_binds_gateway_to_verified_native_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command carries a verified execution precondition into its later POST."""

    target = _target(tmp_path)
    expected = _home()
    client = Mock(spec=GatewayClient)
    client.get_native_home.return_value = expected
    client.refresh_native.return_value = _result("automatic")
    monkeypatch.setattr(helpers, "gateway_paths_from_manifest_path", lambda _: Mock())
    monkeypatch.setattr(helpers, "_live_gateway_client_for_controller", lambda _: client)
    monkeypatch.setattr(helpers, "inspect_native_home", lambda _: expected)
    assert helpers.refresh_managed_agent(target).outcome == "automatic"
    client.bind_native_home.assert_called_once_with(expected)
    client.refresh_native.assert_called_once()


@pytest.mark.parametrize("operation", ["home", "check", "refresh"])
def test_attached_gateway_and_passive_proxy_preserve_typed_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Both owning transports return the same typed observation/outcome unchanged."""

    target = _target(tmp_path)
    client = Mock(spec=GatewayClient)
    client.get_native_home.return_value = _home()
    client.get_common_plugin_state.return_value = _observation()
    client.refresh_native.return_value = _result("restart_required")
    monkeypatch.setattr(helpers, "_native_common_gateway_client", lambda _: client)
    action = {
        "home": helpers.managed_agent_native_home,
        "check": helpers.managed_agent_common_plugin_state,
        "refresh": helpers.refresh_managed_agent,
    }[operation]
    direct = action(target)
    proxy = Mock(pair_authority_kind="houmao-passive-server")
    proxy.get_managed_agent_gateway_native_home.return_value = client.get_native_home.return_value
    proxy.get_managed_agent_gateway_common_plugin_state.return_value = (
        client.get_common_plugin_state.return_value
    )
    proxy.refresh_managed_agent_gateway_native.return_value = client.refresh_native.return_value
    remote = helpers.ManagedAgentTarget(
        mode="server", agent_ref="remote", identity=target.identity, client=proxy
    )
    assert action(remote) is direct


@pytest.mark.parametrize(
    "mode,lifecycle",
    [
        ("external", "active"),
        ("local_stale", "active"),
        ("local_degraded", "active"),
        ("local", "stopped"),
    ],
)
def test_native_reads_reject_external_stopped_and_degraded_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, lifecycle: str
) -> None:
    """An available filesystem path never substitutes for active managed authority."""

    target = _target(tmp_path, mode=mode, lifecycle=lifecycle)
    gateway = Mock()
    monkeypatch.setattr(helpers, "_native_common_gateway_client", gateway)
    for action in (
        helpers.managed_agent_native_home,
        helpers.managed_agent_common_plugin_state,
        helpers.refresh_managed_agent,
    ):
        with pytest.raises(click.ClickException):
            action(target)
    gateway.assert_not_called()

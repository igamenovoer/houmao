"""Exercise signed Web entry through the scoped manager command."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayWebEntryTicketV1
from houmao.gateway.access import GatewayClientBinding, GatewayOwner
from houmao.srv_ctrl.commands import managed_agents
from houmao.srv_ctrl.commands.main import cli

_COMMAND = ["agents", "single", "--agent-id", "agent-123", "gateway", "web-entry"]
_OWNER_URL = "http://127.0.0.1:43123"
_GENERATION = "web-generation"
_TICKET = GatewayWebEntryTicketV1(
    url=f"{_OWNER_URL}/v1/web/enter?ticket={'a' * 43}",
    expires_at_utc="2026-11-20T12:00:00+00:00",
)


@pytest.fixture
def web_target(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> SimpleNamespace:
    """Select an isolated owner-local Web record and capture transport selection."""

    current_path = tmp_path / "current-instance.json"
    manifest_path = tmp_path / "manifest.json"
    owner = GatewayOwner(agent_id="agent-123", context_id="web-owner")
    binding = GatewayClientBinding(
        base_url=_OWNER_URL,
        owner=owner,
        purpose="admin",
        private_key_path=str(tmp_path / "selected-private-key"),
    )
    record = SimpleNamespace(
        mode="web",
        agent_id=owner.agent_id,
        generation_id=_GENERATION,
        execution_binding=SimpleNamespace(context_id=owner.context_id),
        runtime=SimpleNamespace(manifest_path=str(manifest_path)),
    )
    target = SimpleNamespace(
        record=record,
        binding=binding,
        locator=None,
        client_settings=[],
        signer_calls=[],
        issue_calls=0,
        detached=False,
        proof_error=None,
    )

    def resolve_record(*, agent_id: str | None, agent_name: str | None) -> SimpleNamespace | None:
        """Resolve the exact fixture selector to the authoritative record."""

        assert (agent_id, agent_name) == (owner.agent_id, None)
        return target.record

    def load_current(path: Path) -> SimpleNamespace:
        """Return the attached endpoint or indicate detachment."""

        assert path == current_path
        if target.detached:
            raise SessionManifestError("Missing current gateway.")
        return SimpleNamespace(port=43123)

    def select_signer(path: Path, *, port: int, private: bool) -> tuple[GatewayClientBinding, str]:
        """Record signer selection and return the chosen retained binding."""

        assert path == manifest_path
        target.signer_calls.append((port, private))
        return target.binding, _GENERATION

    def fake_request() -> GatewayWebEntryTicketV1:
        """Issue one ticket with the selected admin or report its refusal."""

        target.issue_calls += 1
        if target.proof_error is not None:
            raise GatewayHttpError(
                method="POST", url=_OWNER_URL, detail=target.proof_error, status_code=401
            )
        return _TICKET

    def fake_client(**kwargs: object) -> SimpleNamespace:
        """Capture the exact transport config for the only permitted HTTP client."""

        target.client_settings.append(kwargs)
        return SimpleNamespace(issue_web_entry_ticket=fake_request)

    def unexpected(*args: object, **kwargs: object) -> None:
        """Detect any attempt to route or resume the agent for Web entry."""

        pytest.fail("Web entry should use the attached owner gateway directly")

    monkeypatch.setattr(managed_agents, "resolve_executor_locator", lambda **_: target.locator)
    monkeypatch.setattr(managed_agents, "_resolve_local_managed_agent_record", resolve_record)
    monkeypatch.setattr(managed_agents, "require_registry_mode_authority", lambda _: None)
    monkeypatch.setattr(
        managed_agents,
        "gateway_paths_from_manifest_path",
        lambda _: SimpleNamespace(current_instance_path=current_path),
    )
    monkeypatch.setattr(managed_agents, "load_gateway_current_instance", load_current)
    monkeypatch.setattr(managed_agents, "owner_gateway_client_binding", select_signer)
    monkeypatch.setattr(managed_agents, "GatewayClient", fake_client)
    monkeypatch.setattr(managed_agents, "require_supported_houmao_pair", unexpected)
    monkeypatch.setattr(managed_agents, "_execute_executor_operation", unexpected)
    monkeypatch.setattr(managed_agents, "resume_runtime_session", unexpected)
    return target


@pytest.mark.parametrize("style", ["plain", "json"])
def test_web_entry_outputs_ticket_only(web_target: SimpleNamespace, style: str) -> None:
    """Show just the bearer and expiry using the explicit pinned admin signer."""

    result = CliRunner().invoke(cli, [f"--print-{style}", *_COMMAND])
    assert result.exit_code == 0, result.output
    if style == "json":
        assert json.loads(result.output) == _TICKET.model_dump(mode="json")
    else:
        assert dict(line.split() for line in result.output.splitlines()) == _TICKET.model_dump(
            mode="json"
        )
    assert web_target.signer_calls == [(43123, False)]
    assert web_target.client_settings == [
        {
            "binding": web_target.binding,
            "target_incarnation": _GENERATION,
            "respect_proxy_env": False,
        }
    ]
    assert web_target.issue_calls == 1


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("detached", "attach it explicitly"),
        ("wrong-mode", "requires a live managed agent in Web mode"),
        ("missing-signer", "Set `admin_signer_path`"),
        ("pair-selection", "owner's execution context"),
        ("executor-selection", "owner's execution context"),
        ("nonlocal-record", "requires a local managed agent"),
    ],
)
def test_web_entry_refuses_unsupported_selection_without_fallback(
    web_target: SimpleNamespace, state: str, expected: str
) -> None:
    """Give owner-local instructions without issuing a request on an invalid route."""

    args = _COMMAND.copy()
    if state == "detached":
        web_target.detached = True
    elif state == "wrong-mode":
        web_target.record.mode = "tui"
    elif state == "missing-signer":
        web_target.binding = None
    elif state == "pair-selection":
        args.extend(["--pair-port", "9891"])
    elif state == "executor-selection":
        web_target.locator = object()
    elif state == "nonlocal-record":
        web_target.record = None

    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    assert expected in result.output
    assert web_target.client_settings == []
    assert web_target.issue_calls == 0


def test_web_entry_reports_proof_refusal_without_retry(web_target: SimpleNamespace) -> None:
    """Expose the fixed client error without a second or unsigned request."""

    web_target.proof_error = "Gateway proof was refused. Select a currently enrolled admin signer."
    result = CliRunner().invoke(cli, _COMMAND)
    assert result.exit_code == 1, result.output
    assert web_target.proof_error in result.output
    assert web_target.issue_calls == 1
    assert web_target.binding.private_key_path not in result.output


def test_web_entry_help_is_scoped_and_calls_out_bearer_handling() -> None:
    """Document the private URL in the only supported manager scope."""

    runner = CliRunner()
    help_result = runner.invoke(cli, [*_COMMAND, "--help"])
    assert help_result.exit_code == 0
    assert "bearer secret" in help_result.output
    self_result = runner.invoke(cli, ["agents", "self", "gateway", "--help"])
    assert self_result.exit_code == 0
    assert "web-entry" not in self_result.output

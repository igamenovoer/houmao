"""Exercise native Web and terminal browser entry through scoped manager commands."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_models import (
    GATEWAY_PROTOCOL_VERSION,
    GatewayWebEntryTicketV1,
)
from houmao.gateway.access import GatewayClientBinding, GatewayOwner, GatewayTarget
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.gateway.terminal_entry_contracts import (
    GatewayTerminalEntryMode,
    GatewayTerminalEntryTicketV1,
    TERMINAL_INTERACT_PATH,
    TERMINAL_VIEW_PATH,
)
from houmao.srv_ctrl.commands import managed_agents
from houmao.srv_ctrl.commands.main import cli

_COMMAND = ["agents", "single", "--agent-id", "agent-123", "gateway", "web-entry"]
_TERMINAL_COMMAND = [*_COMMAND[:-1], "terminal-entry"]
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
        purpose="caller",
        private_key_path=str(tmp_path / "selected-private-key"),
    )
    record = SimpleNamespace(
        mode="web",
        agent_id=owner.agent_id,
        generation_id=_GENERATION,
        execution_binding=SimpleNamespace(context_id=owner.context_id),
        runtime=SimpleNamespace(manifest_path=str(manifest_path)),
    )
    descriptor = GatewayEndpointDescriptor(
        protocol=GATEWAY_PROTOCOL_VERSION,
        target=GatewayTarget(owner=owner, incarnation=_GENERATION),
        presence_id="test-gateway-presence",
        advertised_url=None,
        admin_mode="keyed",
    )
    target = SimpleNamespace(
        record=record,
        binding=binding,
        descriptor=descriptor,
        retained_descriptor=descriptor,
        locator=None,
        client_settings=[],
        signer_calls=[],
        describe_calls=0,
        issue_calls=0,
        detached=False,
        descriptor_unavailable=False,
        proof_error=None,
        selector=(owner.agent_id, None),
        terminal_modes=[],
        replace_after_issue=False,
        roster_after_issue=None,
    )

    def resolve_record(*, agent_id: str | None, agent_name: str | None) -> SimpleNamespace | None:
        """Resolve the exact fixture selector to the authoritative record."""

        assert (agent_id, agent_name) == target.selector
        return target.record

    def load_current(path: Path) -> SimpleNamespace:
        """Return the attached endpoint or indicate detachment."""

        assert path == current_path
        if target.detached:
            raise SessionManifestError("Missing current gateway.")
        return SimpleNamespace(
            port=43123,
            endpoint_descriptor=target.retained_descriptor,
            protocol_version=GATEWAY_PROTOCOL_VERSION,
        )

    def select_signer(
        path: Path, *, port: int, private: bool
    ) -> tuple[GatewayClientBinding | None, str]:
        """Record signer selection and return the chosen retained binding."""

        assert path == manifest_path
        target.signer_calls.append((port, private))
        return target.binding, _GENERATION

    def describe_endpoint() -> GatewayEndpointDescriptor:
        """Return the fresh descriptor or report a failed probe."""

        target.describe_calls += 1
        if target.descriptor_unavailable:
            raise GatewayHttpError(method="GET", url=_OWNER_URL, detail="descriptor-error")
        return target.descriptor

    def fake_request() -> GatewayWebEntryTicketV1:
        """Issue one ticket using the selected authority or report a refusal."""

        target.issue_calls += 1
        if target.proof_error is not None:
            raise GatewayHttpError(
                method="POST", url=_OWNER_URL, detail=target.proof_error, status_code=401
            )
        return _TICKET

    def fake_terminal_request(*, mode: GatewayTerminalEntryMode) -> GatewayTerminalEntryTicketV1:
        """Return one browser terminal ticket for the exact requested mode."""

        target.terminal_modes.append(mode)
        if target.proof_error is not None:
            raise GatewayHttpError(
                method="POST", url=_OWNER_URL, detail=target.proof_error, status_code=403
            )
        if target.replace_after_issue:
            target.descriptor = target.descriptor.model_copy(
                update={"presence_id": "replacement-gateway"}
            )
        if target.roster_after_issue is not None:
            target.descriptor = target.descriptor.model_copy(
                update={"admin_mode": target.roster_after_issue}
            )
        return _terminal_ticket(mode)

    def fake_client(**kwargs: object) -> SimpleNamespace:
        """Capture the transport settings for the probe and ticket requests."""

        target.client_settings.append(kwargs)
        return SimpleNamespace(
            describe_endpoint=describe_endpoint,
            issue_web_entry_ticket=fake_request,
            issue_terminal_entry_ticket=fake_terminal_request,
        )

    def unexpected(*args: object, **kwargs: object) -> None:
        """Detect any attempt to route or resume the agent for Web entry."""

        pytest.fail("Web entry should use the attached owner gateway directly")

    monkeypatch.setattr(managed_agents, "resolve_executor_locator", lambda **_: target.locator)
    monkeypatch.setattr(managed_agents, "_resolve_local_managed_agent_record", resolve_record)
    monkeypatch.setattr(managed_agents, "require_registry_mode_authority", lambda _: None)
    monkeypatch.setattr(managed_agents, "validate_execution_owner", lambda _: None)
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


def _terminal_ticket(mode: GatewayTerminalEntryMode) -> GatewayTerminalEntryTicketV1:
    """Build a synthetic browser ticket for an exact local mode path."""

    path = TERMINAL_INTERACT_PATH if mode == "interact" else TERMINAL_VIEW_PATH
    return GatewayTerminalEntryTicketV1(
        url=f"{_OWNER_URL}{path}#ticket={'b' * 43}",
        mode=mode,
        expires_at_utc=_TICKET.expires_at_utc,
    )


@pytest.mark.parametrize("style", ["plain", "json"])
@pytest.mark.parametrize("open_gateway", [False, True], ids=["keyed", "open"])
def test_web_entry_outputs_ticket_only(
    web_target: SimpleNamespace, style: str, open_gateway: bool
) -> None:
    """Choose authority from the live descriptor and show only the ticket result."""

    if open_gateway:
        web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": "open"})
        web_target.binding = None

    result = CliRunner().invoke(cli, [f"--print-{style}", *_COMMAND])
    assert result.exit_code == 0, result.output
    if style == "json":
        assert json.loads(result.output) == _TICKET.model_dump(mode="json")
    else:
        assert dict(line.split() for line in result.output.splitlines()) == _TICKET.model_dump(
            mode="json"
        )
    probe = {"base_url": _OWNER_URL, "respect_proxy_env": False}
    assert web_target.signer_calls == ([] if open_gateway else [(43123, False)])
    expected = [probe]
    if not open_gateway:
        expected.append(
            {
                **probe,
                "binding": web_target.binding,
                "target_incarnation": _GENERATION,
                "target_presence_id": web_target.descriptor.presence_id,
            }
        )
    assert web_target.client_settings == expected
    assert web_target.describe_calls == 1
    assert web_target.issue_calls == 1


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("detached", "attach it explicitly"),
        ("wrong-mode", "requires a live managed agent in Web mode"),
        ("missing-signer", "Pass `--signer` or set `admin_signer_path`"),
        ("pair-selection", "owner's execution context"),
        ("executor-selection", "owner's execution context"),
        ("nonlocal-record", "requires a local managed agent"),
        ("descriptor-unavailable", "could not verify the live owner-local gateway"),
        ("policy-unavailable", "access policy is unavailable"),
        ("legacy-proof", "managed Web execution changed"),
        ("missing-retained", "managed Web execution changed"),
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
    elif state == "descriptor-unavailable":
        web_target.descriptor_unavailable = True
    elif state == "policy-unavailable":
        web_target.descriptor = web_target.descriptor.model_copy(
            update={"admin_mode": "unavailable"}
        )
    elif state == "legacy-proof":
        web_target.descriptor = web_target.descriptor.model_copy(
            update={"proof_protocol": "sshsig-v1"}
        )
    elif state == "missing-retained":
        web_target.retained_descriptor = None

    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    assert expected in result.output
    needs_probe = state in {
        "missing-signer",
        "descriptor-unavailable",
        "policy-unavailable",
        "legacy-proof",
    }
    assert web_target.describe_calls == int(needs_probe)
    assert web_target.issue_calls == 0


@pytest.mark.parametrize("field", ["agent_id", "context_id", "incarnation", "presence_id"])
def test_web_entry_refuses_mismatched_live_identity(
    web_target: SimpleNamespace, field: str
) -> None:
    """Refuse to select a signer or request a link against a replacement gateway."""

    descriptor = web_target.descriptor
    target = descriptor.target
    if field == "presence_id":
        descriptor = descriptor.model_copy(update={field: "different-gateway"})
    elif field == "incarnation":
        target = target.model_copy(update={field: "different-generation"})
    else:
        target = target.model_copy(
            update={"owner": target.owner.model_copy(update={field: "other"})}
        )
    web_target.descriptor = descriptor.model_copy(update={"target": target})

    result = CliRunner().invoke(cli, _COMMAND)
    assert result.exit_code == 1, result.output
    assert "managed Web execution changed" in result.output
    assert web_target.describe_calls == 1
    assert web_target.signer_calls == []
    assert web_target.issue_calls == 0


@pytest.mark.parametrize("open_gateway", [False, True], ids=["keyed", "open"])
def test_web_entry_reports_proof_refusal_without_retry(
    web_target: SimpleNamespace, open_gateway: bool
) -> None:
    """Report an admission refusal and finish the attempt after one POST."""

    if open_gateway:
        web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": "open"})
        web_target.proof_error = (
            "Gateway refused unsigned Web entry. Check its current access policy."
        )
    else:
        web_target.proof_error = (
            "Gateway proof was refused. Select a currently enrolled admin signer."
        )
    result = CliRunner().invoke(cli, _COMMAND)
    assert result.exit_code == 1, result.output
    assert web_target.proof_error in result.output
    assert web_target.issue_calls == 1
    assert web_target.describe_calls == 1
    assert web_target.signer_calls == ([] if open_gateway else [(43123, False)])
    assert web_target.binding.private_key_path not in result.output


def test_web_entry_selects_explicit_scoped_signer(
    web_target: SimpleNamespace, tmp_path: Path
) -> None:
    """Use the explicit web.enter signer independently of a configured admin key."""

    signer_path = tmp_path / "scoped-key"
    result = CliRunner().invoke(cli, [*_COMMAND, "--signer", str(signer_path)])
    assert result.exit_code == 0, result.output
    assert web_target.signer_calls == []
    assert web_target.issue_calls == 1
    assert web_target.client_settings[-1]["binding"].private_key_path == str(signer_path)
    assert web_target.client_settings[-1]["binding"].purpose == "caller"


def test_web_entry_help_is_scoped_and_calls_out_bearer_handling() -> None:
    """Document the private URL in the only supported manager scope."""

    runner = CliRunner()
    help_result = runner.invoke(cli, [*_COMMAND, "--help"])
    assert help_result.exit_code == 0
    assert "bearer secret" in help_result.output
    assert "unsigned requests" in help_result.output
    self_result = runner.invoke(cli, ["agents", "self", "gateway", "--help"])
    assert self_result.exit_code == 0
    assert "web-entry" not in self_result.output


@pytest.mark.parametrize("style", ["plain", "json"])
@pytest.mark.parametrize("roster", ["keyed", "open", "unavailable"])
def test_terminal_entry_views_anonymously_in_every_roster(
    web_target: SimpleNamespace, style: str, roster: str
) -> None:
    """Keep view requests unsigned and expose only the validated viewer ticket."""

    web_target.record.mode = "headless"
    web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": roster})
    web_target.selector = (None, "worker")
    args = ["agents", "single", "--agent-name", "worker", "gateway", "terminal-entry"]
    result = CliRunner().invoke(cli, [f"--print-{style}", *args])
    assert result.exit_code == 0, result.output
    actual = (
        json.loads(result.output)
        if style == "json"
        else dict(line.split() for line in result.output.splitlines())
    )
    assert actual == _terminal_ticket("view").model_dump(mode="json")
    assert web_target.describe_calls == 2
    assert web_target.signer_calls == []
    assert web_target.terminal_modes == ["view"]
    assert web_target.client_settings == [{"base_url": _OWNER_URL, "respect_proxy_env": False}]


@pytest.mark.parametrize("configured_signer", [False, True])
def test_terminal_entry_uses_unsigned_open_authority(
    web_target: SimpleNamespace, configured_signer: bool
) -> None:
    """Use the open roster without loading a key or selecting a different mode."""

    web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": "open"})
    if not configured_signer:
        web_target.binding = None
    result = CliRunner().invoke(cli, ["--print-json", *_TERMINAL_COMMAND, "--interact"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == _terminal_ticket("interact").model_dump(mode="json")
    assert web_target.terminal_modes == ["interact"]
    assert web_target.signer_calls == []
    assert web_target.describe_calls == 2
    assert web_target.client_settings == [{"base_url": _OWNER_URL, "respect_proxy_env": False}]


@pytest.mark.parametrize(
    ("roster", "explicit_signer"), [("keyed", False), ("keyed", True), ("open", True)]
)
def test_terminal_entry_interaction_binds_the_admin_signer(
    web_target: SimpleNamespace, tmp_path: Path, roster: str, explicit_signer: bool
) -> None:
    """Use a configured keyed signer or the explicit signer on either roster."""

    web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": roster})
    args = ["--print-json", *_TERMINAL_COMMAND, "--interact"]
    signer = tmp_path / "experimental-signer"
    if explicit_signer:
        args.extend(["--signer", str(signer)])
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == _terminal_ticket("interact").model_dump(mode="json")
    assert web_target.signer_calls == ([] if explicit_signer else [(43123, False)])
    assert web_target.terminal_modes == ["interact"]
    selected_settings = web_target.client_settings[-1]
    assert selected_settings["target_incarnation"] == _GENERATION
    assert selected_settings["target_presence_id"] == web_target.descriptor.presence_id
    expected_signer = str(signer) if explicit_signer else web_target.binding.private_key_path
    assert selected_settings["binding"].private_key_path == expected_signer


@pytest.mark.parametrize(
    "state",
    [
        "unavailable",
        "missing-signer",
        "revoked",
        "signed-view",
        "open-invalid-proof",
        "keyed-before-issuance",
    ],
)
def test_terminal_entry_refuses_unauthorized_interaction_without_downgrade(
    web_target: SimpleNamespace, state: str
) -> None:
    """Deny unqualified admin requests or a signer option submitted for unsigned viewing."""

    args = [*_TERMINAL_COMMAND, "--interact"]
    if state == "unavailable":
        web_target.descriptor = web_target.descriptor.model_copy(
            update={"admin_mode": "unavailable"}
        )
    elif state == "missing-signer":
        web_target.binding = None
    elif state == "revoked":
        web_target.proof_error = "Terminal interaction was refused."
    elif state == "signed-view":
        args = [*_TERMINAL_COMMAND, "--signer", web_target.binding.private_key_path]
    else:
        web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": "open"})
        web_target.proof_error = "Terminal interaction was refused after the policy changed."
        if state == "open-invalid-proof":
            args.extend(["--signer", web_target.binding.private_key_path])
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    attempted = state in {"revoked", "open-invalid-proof", "keyed-before-issuance"}
    assert web_target.terminal_modes == (["interact"] if attempted else [])
    if state in {"open-invalid-proof", "keyed-before-issuance"}:
        assert web_target.signer_calls == []
        assert web_target.describe_calls == 1
        assert len(web_target.client_settings) == (2 if state == "open-invalid-proof" else 1)
    assert "#ticket=" not in result.output
    assert web_target.issue_calls == 0


@pytest.mark.parametrize("new_roster", ["keyed", "unavailable"])
def test_terminal_entry_withholds_open_ticket_after_policy_changes(
    web_target: SimpleNamespace, new_roster: str
) -> None:
    """Discard an open ticket when the gateway loses that mode before the result is printed."""

    web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": "open"})
    web_target.roster_after_issue = new_roster
    result = CliRunner().invoke(cli, [*_TERMINAL_COMMAND, "--interact"])
    assert result.exit_code == 1, result.output
    assert "gateway admin policy changed" in result.output
    assert "#ticket=" not in result.output
    assert web_target.signer_calls == []
    assert web_target.terminal_modes == ["interact"]
    assert web_target.describe_calls == 2


@pytest.mark.parametrize("mode", ["view", "interact"])
@pytest.mark.parametrize("state", ["detached", "replaced", "replaced-after-issue"])
def test_terminal_entry_uses_the_existing_verified_gateway(
    web_target: SimpleNamespace, state: str, mode: str
) -> None:
    """Reject absent or changed gateways before disclosing a browser ticket."""

    if state == "detached":
        web_target.detached = True
    elif state == "replaced":
        web_target.descriptor = web_target.descriptor.model_copy(
            update={"presence_id": "replacement-gateway"}
        )
    else:
        web_target.replace_after_issue = True
    args = _TERMINAL_COMMAND
    if mode == "interact":
        web_target.descriptor = web_target.descriptor.model_copy(update={"admin_mode": "open"})
        args = [*args, "--interact"]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    expected = "attach it explicitly" if state == "detached" else "execution changed"
    assert expected in result.output
    assert "#ticket=" not in result.output
    assert web_target.terminal_modes == ([mode] if state == "replaced-after-issue" else [])


def test_terminal_entry_help_announces_unsigned_view_and_bearer_secret() -> None:
    """Register the command only for selected agents and document the options."""

    runner = CliRunner()
    result = runner.invoke(cli, [*_TERMINAL_COMMAND, "--help"])
    assert result.exit_code == 0
    help_text = " ".join(result.output.split())
    for detail in (
        "bearer secret",
        "unsigned owner-local",
        "no signer on an open gateway",
        "--interact",
        "--signer",
    ):
        assert detail in help_text
    result = runner.invoke(cli, ["agents", "self", "gateway", "--help"])
    assert result.exit_code == 0
    assert "terminal-entry" not in result.output

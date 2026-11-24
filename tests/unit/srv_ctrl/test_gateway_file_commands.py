"""Exercise the scoped file CLI without a real listener, registry, or agent."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner, Result
from pydantic import BaseModel
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_models import GATEWAY_PROTOCOL_VERSION
from houmao.gateway.access import GatewayClientBinding, GatewayOwner, GatewayTarget
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.gateway.file_edits import contracts as file
from houmao.srv_ctrl.commands.agents import access, files
from houmao.srv_ctrl.commands.main import cli

_TARGET = GatewayTarget(
    owner=GatewayOwner(agent_id="writer", context_id="writer-owner"),
    incarnation="writer-generation",
)
_PRESENCE = "verified-listener"
_URL = "https://gateway.example.org/writer"
_MOUNT = "a" * 32
_BASE = "b" * 40
_CANDIDATE = "c" * 40
_SELECT = ["agents", "single", "--agent-id", "writer", "files"]
_REMOTE = [
    "--url",
    _URL,
    "--context-id",
    _TARGET.owner.context_id,
    "--generation",
    _TARGET.incarnation,
    "--presence",
    _PRESENCE,
]


@dataclass
class _Transport:
    """Keep endpoint probing and typed file calls independently observable."""

    endpoint: GatewayEndpointDescriptor
    results: dict[str, dict[str, object] | Exception] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    probes: list[dict[str, object]] = field(default_factory=list)
    calls: list[tuple[str, file.FileTargetRequest, dict[str, object]]] = field(default_factory=list)

    def client(self, **options: object) -> SimpleNamespace:
        """Substitute the HTTP transport while retaining the real endpoint checks and bindings."""

        def describe() -> GatewayEndpointDescriptor:
            """Return the descriptor from the selected endpoint."""

            self.events.append("verify")
            self.probes.append(options)
            return self.endpoint

        def request(
            name: str, payload: file.FileTargetRequest, response: type[BaseModel]
        ) -> BaseModel:
            """Record the exact binding and typed request."""

            self.events.append(name)
            self.calls.append((name, payload, options))
            assert payload.target == _TARGET
            assert payload.presence_id == _PRESENCE
            assert options["respect_proxy_env"] is False
            result = self.results[name]
            if isinstance(result, Exception):
                raise result
            return response.model_validate(result)

        return SimpleNamespace(describe_endpoint=describe, request_file_edit=request)


@pytest.fixture
def transport(monkeypatch: pytest.MonkeyPatch) -> _Transport:
    """Provide a verified endpoint with configurable authority and receipts."""

    connected = _Transport(
        GatewayEndpointDescriptor(
            protocol=GATEWAY_PROTOCOL_VERSION,
            target=_TARGET,
            presence_id=_PRESENCE,
            advertised_url=_URL,
            admin_mode="open",
        ),
    )
    monkeypatch.setattr(access, "GatewayClient", connected.client)
    monkeypatch.setattr(files, "GatewayClient", connected.client)
    return connected


def _command(*args: str, style: str = "json", stdin: str | None = None) -> Result:
    """Invoke the built-in CLI command tree with an explicit selected target."""

    return CliRunner().invoke(cli, [f"--print-{style}", *_SELECT, *args], input=stdin)


def test_owner_local_open_mount_and_draft(
    transport: _Transport, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Probe owner-local authority and carry an anonymous lease only for draft operations."""

    manifest = tmp_path / "manifest.json"
    current = tmp_path / "current.json"
    capability = "s" * 43
    secret = tmp_path / "draft-capability"
    secret.touch(mode=0o600)
    secret.write_text(f"{capability}\n", encoding="ascii")
    transport.results.update(
        mounts={
            "mounts": [
                {
                    "mount_id": _MOUNT,
                    "name": "skills",
                    "resource": f"files:{_MOUNT}",
                    "actions": ["files.read", "files.edit", "files.push"],
                    "published_commit": _BASE,
                }
            ]
        },
        **{
            "lease/open": {
                "draft_id": "draft-1",
                "base_commit": _BASE,
                "expires_at": 123.0,
                "actor": {"kind": "anonymous"},
                "lease_capability": capability,
            },
            "draft/write": {"draft_id": "draft-1", "actor": {"kind": "anonymous"}},
        },
    )

    def resolve_local(*, agent_id: str, agent_name: str | None) -> SimpleNamespace:
        """Capture the selected owner's current local record."""

        assert (agent_id, agent_name) == ("writer", None)
        return SimpleNamespace(
            manifest_path=manifest,
            target=_TARGET,
            require_current=lambda: transport.events.append("owner"),
        )

    monkeypatch.setattr(access, "resolve_owner_gateway_access", resolve_local)
    monkeypatch.setattr(
        access,
        "gateway_paths_from_manifest_path",
        lambda path: SimpleNamespace(current_instance_path=current) if path == manifest else None,
    )
    monkeypatch.setattr(
        access,
        "load_gateway_current_instance",
        lambda path: SimpleNamespace(endpoint_descriptor=transport.endpoint, port=1234),
    )
    discovered = _command("mounts")
    assert discovered.exit_code == 0, discovered.output
    assert json.loads(discovered.output)["mounts"][0]["resource"] == f"files:{_MOUNT}"
    assert transport.probes[0]["base_url"] == access.owner_gateway_base_url(1234)

    opened = _command("--mount", _MOUNT, "lease", "open", "--expected-base", _BASE)
    assert opened.exit_code == 0, opened.output
    assert json.loads(opened.output)["lease_capability"] == capability

    result = _command(
        "--mount",
        _MOUNT,
        "--draft",
        "draft-1",
        "--lease-capability-file",
        str(secret),
        "write",
        "review/SKILL.md",
        "--from-file",
        "-",
        stdin="content\n",
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["draft_id"] == "draft-1"
    assert capability not in result.output
    assert str(secret) not in result.output
    assert transport.events == [
        "owner",
        "verify",
        "mounts",
        "owner",
        "verify",
        "lease/open",
        "owner",
        "verify",
        "draft/write",
    ]
    name, payload, options = transport.calls[-1]
    assert name == "draft/write"
    assert isinstance(payload, file.FileDraftWriteRequest)
    assert (payload.mount_id, payload.draft_id, payload.lease_capability) == (
        _MOUNT,
        "draft-1",
        capability,
    )
    assert (payload.path, payload.content_base64) == ("review/SKILL.md", "Y29udGVudAo=")
    assert "binding" not in options


@pytest.mark.parametrize("signer_mode", ["explicit", "configured", "self"])
def test_trusted_remote_uses_independent_signer(
    transport: _Transport, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, signer_mode: str
) -> None:
    """Verify the remote target and CA before consulting any selected source identity."""

    key = tmp_path / "reviewer.key"
    key.touch(mode=0o600)
    ca = tmp_path / "gateway-ca.pem"
    ca.touch()
    transport.endpoint = transport.endpoint.model_copy(update={"admin_mode": "keyed"})
    transport.results["list"] = {"revision": _BASE, "entries": []}
    source = object()

    def source_access(agent_id: str | None) -> object:
        """Resolve a configured source only after explicit endpoint verification."""

        assert signer_mode != "explicit"
        assert agent_id == ("reviewer" if signer_mode == "configured" else None)
        transport.events.append("source")
        return source

    monkeypatch.setattr(files, "_source_access", source_access)
    monkeypatch.setattr(
        files, "_peer_signer_path", lambda record: key if record is source else None
    )
    selection = {
        "explicit": ["--signer", str(key)],
        "configured": ["--source-agent-id", "reviewer"],
        "self": ["--self-signer"],
    }[signer_mode]
    args = [*_REMOTE, "--ca-bundle", str(ca), *selection, "--mount", _MOUNT, "list"]
    result = _command(*args)
    assert result.exit_code == 0, result.output
    assert transport.events == [
        "verify",
        *(["source"] if signer_mode != "explicit" else []),
        "list",
    ]
    assert transport.probes == [
        {"base_url": _URL, "ca_bundle_path": ca, "respect_proxy_env": False}
    ]
    _, payload, options = transport.calls[0]
    binding = options["binding"]
    assert isinstance(binding, GatewayClientBinding)
    assert (binding.owner, binding.private_key_path, binding.purpose) == (
        _TARGET.owner,
        str(key),
        "caller",
    )
    assert binding.ca_bundle_path == str(ca)
    assert options["target_incarnation"] == _TARGET.incarnation
    assert options["target_presence_id"] == _PRESENCE
    assert isinstance(payload, file.FileListRequest) and payload.mount_id == _MOUNT
    assert str(key) not in result.output

    transport.endpoint = transport.endpoint.model_copy(update={"presence_id": "replacement"})
    refused = _command(*args)
    assert refused.exit_code == 1
    assert "verify the selected gateway" in refused.output
    assert transport.events[-1] == "verify"
    assert len(transport.calls) == 1


def test_file_cli_refuses_unverified_or_unauthorized_connection(
    transport: _Transport, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Never downgrade to unsigned after refusal or attach a missing gateway."""

    transport.endpoint = transport.endpoint.model_copy(update={"admin_mode": "keyed"})
    keyed = _command(*_REMOTE, "mounts")
    assert keyed.exit_code == 1
    assert "Select an enrolled signer" in keyed.output
    assert transport.events == ["verify"]

    transport.endpoint = transport.endpoint.model_copy(update={"admin_mode": "open"})
    transport.results["mounts"] = GatewayHttpError(
        method="POST",
        url=_URL,
        detail="private proof error",
        status_code=401,
    )
    key = tmp_path / "invalid.key"
    key.touch(mode=0o600)
    refused = _command(*_REMOTE, "--signer", str(key), "mounts")
    assert refused.exit_code == 1
    assert "HTTP 401" in refused.output
    assert "private proof error" not in refused.output
    assert transport.events == ["verify", "verify", "mounts"]
    assert "binding" in transport.calls[0][2]

    monkeypatch.setattr(access, "_owner_access", lambda: SimpleNamespace(manifest_path=key))
    monkeypatch.setattr(access, "gateway_paths_from_manifest_path", lambda path: None)
    detached = _command("mounts")
    assert detached.exit_code == 1
    assert "No gateway is attached" in detached.output
    assert transport.events[-1] == "mounts"
    assert len(transport.calls) == 1


@pytest.mark.parametrize("status_code", [None, 502])
def test_lost_push_reports_original_id_and_status_only(
    transport: _Transport, status_code: int | None
) -> None:
    """After an uncertain push, reconcile via read-only status using the emitted ID."""

    transport.results["push"] = GatewayHttpError(
        method="POST",
        url=_URL,
        detail="private transport details",
        status_code=status_code,
    )
    attempted = _command(*_REMOTE, "--mount", _MOUNT, "push", _CANDIDATE, "--expected-base", _BASE)
    assert attempted.exit_code == 1
    emitted = json.loads(attempted.output)
    operation_id = emitted["operation_id"]
    request = transport.calls[0][1]
    assert isinstance(request, file.FilePushRequest)
    assert emitted == {
        "operation_id": request.operation_id,
        "candidate": _CANDIDATE,
        "outcome": "unconfirmed",
    }

    receipt = {
        "operation_id": operation_id,
        "candidate": _CANDIDATE,
        "expected_base": _BASE,
        "publisher": {"kind": "anonymous"},
        "outcome": "published",
        "published_commit": _CANDIDATE,
        "effective_commit": None,
        "activation": "unknown",
        "native_settled": True,
        "native_ready": True,
    }
    transport.results["status"] = receipt
    observed = _command(*_REMOTE, "--mount", _MOUNT, "status", operation_id)
    assert observed.exit_code == 0, observed.output
    assert json.loads(observed.output)["published_commit"] == _CANDIDATE
    assert json.loads(observed.output)["effective_commit"] is None
    assert file.FILE_REQUESTS["status"][1] == "files.read"
    assert transport.events == ["verify", "push", "verify", "status"]
    request = transport.calls[-1][1]
    assert isinstance(request, file.FileStatusRequest) and request.operation_id == operation_id


def test_busy_receipt_keeps_references_without_fallback(transport: _Transport) -> None:
    """Report the confirmed busy attempt once and retain compact plain inspection references."""

    operation_id = "review-busy-attempt"
    transport.results["push"] = {
        "operation_id": operation_id,
        "candidate": _CANDIDATE,
        "expected_base": _BASE,
        "publisher": {"kind": "anonymous"},
        "outcome": "busy",
    }
    result = _command(
        *_REMOTE,
        "--mount",
        _MOUNT,
        "push",
        _CANDIDATE,
        "--expected-base",
        _BASE,
        "--operation-id",
        operation_id,
        style="plain",
    )
    assert result.exit_code == 1
    assert all(value in result.output for value in (operation_id, _CANDIDATE, "busy"))
    assert len(result.output) < 800
    assert transport.events == ["verify", "push"]


def test_file_subcommand_help_does_not_connect(transport: _Transport) -> None:
    """Render help without discovering the agent or loading a signing key."""

    result = _command("lease", "open", "--help")
    assert result.exit_code == 0, result.output
    assert "--expected-base" in result.output
    assert not transport.events

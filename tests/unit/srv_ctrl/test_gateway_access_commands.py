"""Test owner-local access changes and separately pinned gateway caller proof."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from click.testing import CliRunner
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import GATEWAY_PROTOCOL_VERSION
from houmao.gateway.access import GatewayAccessStore, GatewayAdminKey, GatewayClientBinding
from houmao.gateway.access import GatewayOwner, GatewayTarget, public_key_text
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.gateway.deployment import GatewayEndpointDescriptor
from houmao.gateway.roster import add_admin_key, remove_admin_key
from houmao.srv_ctrl.commands import managed_agents
from houmao.srv_ctrl.commands.agents import access as commands
from houmao.srv_ctrl.commands.main import cli

_OWNER = GatewayOwner(agent_id="writer", context_id="target-owner")
_TARGET = GatewayTarget(owner=_OWNER, incarnation="writer-generation")
_PRESENCE = "verified-listener"
_URL = "https://gateway.example.org/writer"
_SELECT = ["--print-json", "agents", "single", "--agent-id", _OWNER.agent_id, "access"]
_REMOTE = [
    "--url",
    _URL,
    "--context-id",
    _OWNER.context_id,
    "--generation",
    _TARGET.incarnation,
    "--presence",
    _PRESENCE,
]


def _key(root: Path, label: str) -> tuple[GatewayAdminKey, Path, Path]:
    """Create a synthetic signer and public enrollment file."""

    private_key = Ed25519PrivateKey.generate()
    public_key = public_key_text(private_key.public_key())
    secret_path = root / f"{label}.key"
    secret_path.touch(mode=0o600)
    secret_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
    )
    public_path = root / f"{label}.pub"
    public_path.write_text(public_key, encoding="utf-8")
    return GatewayAdminKey(principal=label, public_key=public_key), secret_path, public_path


def _command(*args: str) -> Any:
    """Run one access command and decode its confirmed structured response."""

    result = CliRunner().invoke(cli, [*_SELECT, *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.fixture
def owner_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Verify a stopped record through the maintained local owner selection path."""

    private_root = tmp_path / "policy"
    manifest_path = tmp_path / "manifest.json"
    binding = object()
    access = SimpleNamespace(
        manifest_path=manifest_path,
        owner=_OWNER,
        target=_TARGET,
        execution_binding=binding,
        store=AuthorizationStore(private_root, _OWNER),
        self_store=GatewayAccessStore.from_root(private_root, _OWNER),
        require_current=lambda: None,
    )
    record = SimpleNamespace(
        agent_id=_OWNER.agent_id,
        generation_id=_TARGET.incarnation,
        execution_binding=binding,
        runtime=SimpleNamespace(manifest_path=str(manifest_path)),
    )

    def select(**kwargs: object) -> tuple[SimpleNamespace, None]:
        """Use the explicit local target and allow owner changes when it is stopped."""

        assert kwargs == {"agent_id": _OWNER.agent_id, "agent_name": None, "include_inactive": True}
        return record, None

    def verified_manifest(path: Path) -> SimpleNamespace:
        """Read the selected owner-local manifest without starting any service."""

        assert path == manifest_path
        return access

    monkeypatch.setattr(
        managed_agents, "_resolve_local_managed_agent_record_with_miss_context", select
    )
    monkeypatch.setattr(managed_agents, "require_registry_mode_authority", lambda current: None)
    monkeypatch.setattr(managed_agents, "gateway_access_for_manifest", verified_manifest)
    return access


def test_offline_owner_policy_cli(owner_access: SimpleNamespace, tmp_path: Path) -> None:
    """Enroll and rotate a cross-account peer, grant it a role, and explain exact access."""

    operator, operator_path, _ = _key(tmp_path, "operator")
    seed = tmp_path / "seed.json"
    seed.touch(mode=0o600)
    seed.write_text(
        json.dumps({"schema_version": 2, "admin_keys": [operator.model_dump(mode="json")]})
    )
    assert _command("init", "--seed", str(seed))["admin_mode"] == "keyed"
    assert owner_access.self_store.load_self(_TARGET.incarnation).owner == _OWNER
    assert (
        _command(
            "principal-add",
            "reviewer-principal",
            "--kind",
            "agent",
            "--label",
            "Cross-account Reviewer",
            "--logical-agent-id",
            "reviewer",
        )["policy_revision"]
        == 1
    )

    peer, _, peer_public = _key(tmp_path, "reviewer")
    assert (
        _command("credential-enroll", "reviewer-principal", "--public-key", str(peer_public))[
            "key_id"
        ]
        == peer.key_id
    )
    _command("grant", "reviewer-principal", "agent", "agent.status.read", "--expires-at", "1")
    _command("role-put", "support", "--permission", "agent", "agent.status.read")
    _command("role-assign", "reviewer-principal", "support")
    allowed = _command("explain", "reviewer-principal", "agent", "agent.status.read")
    assert allowed["direct_grant"] == {"expires_at": 1, "active": False}
    assert allowed["matching_roles"] == [{"role_id": "support", "expires_at": None, "active": True}]
    assert allowed["keys"] == [{"key_id": peer.key_id, "allowed": True, "basis": "scoped"}]
    denied = _command("explain", "reviewer-principal", "agent", "agent.prompt")
    assert denied["keys"] == [
        {"key_id": peer.key_id, "allowed": False, "reason": "insufficient_authority"}
    ]

    _command("role-revoke", "reviewer-principal", "support")
    _command("revoke", "reviewer-principal", "agent", "agent.status.read")
    _command("credential-revoke", peer.key_id)
    view = _command("list")
    assert view["grants"] == []
    assert view["role_assignments"] == []
    assert view["credentials"] == [
        {"admin": True, "key_id": operator.key_id, "principal_id": "operator"}
    ]
    assert str(operator_path) not in json.dumps(view)
    assert operator.public_key not in json.dumps(view)


def test_empty_init_and_mismatched_owner(owner_access: SimpleNamespace) -> None:
    """Require an explicit initial choice and an exact observed owner binding."""

    runner = CliRunner()
    assert runner.invoke(cli, [*_SELECT, "init"]).exit_code == 2
    assert _command("init", "--empty")["admin_mode"] == "open"
    owner_access.execution_binding = object()
    refused = runner.invoke(cli, [*_SELECT, "list"])
    assert refused.exit_code == 1
    assert "verified local execution owner" in refused.output


def test_signed_roster_rotation_reports_exact_effect(
    owner_access: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """First and replacement proofs use the exact target, while removal preserves the credential."""

    owner_access.store.initialize()
    original, original_path, original_public = _key(tmp_path, "original")
    replacement, replacement_path, replacement_public = _key(tmp_path, "replacement")
    witnesses: list[tuple[str, str]] = []
    reads: list[str] = []

    def fake_client(**kwargs: Any) -> SimpleNamespace:
        """Validate each pinned signer binding and apply the real retained roster transform."""

        def observe() -> GatewayEndpointDescriptor:
            """Publish the state after actual admin mutations without retrying them."""

            state = owner_access.store.snapshot()
            reads.append(state.admin_mode)
            return GatewayEndpointDescriptor(
                protocol=GATEWAY_PROTOCOL_VERSION,
                target=_TARGET,
                presence_id=_PRESENCE,
                advertised_url=_URL,
                admin_mode=state.admin_mode,
            )

        if "binding" not in kwargs:
            assert kwargs == {"base_url": _URL, "ca_bundle_path": None, "respect_proxy_env": False}
            return SimpleNamespace(describe_endpoint=observe)

        binding = kwargs["binding"]
        assert binding.owner == _OWNER and binding.base_url == _URL
        assert kwargs["target_presence_id"] == _PRESENCE
        assert kwargs["target_incarnation"] == _TARGET.incarnation
        assert kwargs["respect_proxy_env"] is False

        def add(key: GatewayAdminKey) -> str:
            """Require the proposed-key proof or the selected original admin signer."""

            signer_path = Path(binding.private_key_path)
            if not witnesses:
                assert signer_path == original_path
                assert binding.purpose == "register" and kwargs["registration_key"] == key
            else:
                assert signer_path == original_path
                assert binding.purpose == "caller" and kwargs["registration_key"] is None
            witnesses.append(("add", key.key_id))
            owner_access.store.update(
                lambda state: add_admin_key(state, key), actor="operator", action="admin.key.add"
            )
            return key.key_id

        def remove(key_id: str) -> None:
            """Apply a removal using the currently selected replacement signer."""

            assert Path(binding.private_key_path) == replacement_path
            assert binding.purpose == "caller"
            witnesses.append(("remove", key_id))
            owner_access.store.update(
                lambda state: remove_admin_key(state, key_id),
                actor="operator",
                action="admin.key.remove",
            )

        return SimpleNamespace(add_admin_key=add, remove_admin_key=remove)

    monkeypatch.setattr(commands, "GatewayClient", fake_client)
    first = _command(
        "admin-add",
        *_REMOTE,
        "--first",
        "--signer",
        str(original_path),
        "--public-key",
        str(original_public),
        "--principal",
        original.principal,
    )
    assert first == {"key_id": original.key_id, "admin_mode": "keyed"}
    second = _command(
        "admin-add",
        *_REMOTE,
        "--signer",
        str(original_path),
        "--public-key",
        str(replacement_public),
        "--principal",
        replacement.principal,
    )
    assert second == {"key_id": replacement.key_id, "admin_mode": "keyed"}
    removed = _command("admin-remove", *_REMOTE, original.key_id, "--signer", str(replacement_path))
    assert removed == {"key_id": original.key_id, "admin_mode": "keyed", "removed": True}
    assert owner_access.store.snapshot().find_credential(original.key_id).admin_revision is None
    _command("credential-revoke", original.key_id)
    assert owner_access.store.snapshot().find_credential(original.key_id) is None
    removed = _command(
        "admin-remove", *_REMOTE, replacement.key_id, "--signer", str(replacement_path)
    )
    assert removed == {"key_id": replacement.key_id, "admin_mode": "open", "removed": True}
    assert reads == ["open", "keyed", "keyed", "keyed", "keyed", "open"]
    assert witnesses == [
        ("add", original.key_id),
        ("add", replacement.key_id),
        ("remove", original.key_id),
        ("remove", replacement.key_id),
    ]


def test_peer_key_selection_export_and_request(
    owner_access: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export the same peer key after relaunch and sign for an independently selected remote target."""

    owner_access.store.initialize()
    peer, signer_path, _ = _key(tmp_path, "source")
    saved: dict[str, object] = {}
    monkeypatch.setattr(
        commands,
        "save_gateway_deployment",
        lambda path, deployment: saved.update({str(path): deployment}),
    )
    monkeypatch.setattr(commands, "load_gateway_deployment", lambda path: saved.get(str(path)))
    selected = _command("peer-signer", "--key", str(signer_path))
    assert selected == {
        "logical_agent_id": _OWNER.agent_id,
        "public_key": peer.public_key,
        "key_id": peer.key_id,
    }
    monkeypatch.setattr(commands, "gateway_access_for_manifest", lambda path: owner_access)
    monkeypatch.setattr(
        commands,
        "resolve_self_manifest",
        lambda: SimpleNamespace(
            path=owner_access.manifest_path,
            agent_id=owner_access.owner.agent_id,
            record=SimpleNamespace(
                execution_binding=owner_access.execution_binding,
                generation_id=owner_access.target.incarnation,
            ),
        ),
    )
    owner_access.target = _TARGET.model_copy(update={"incarnation": "source-new-generation"})
    exported = CliRunner().invoke(cli, ["--print-json", "agents", "self", "access", "public-key"])
    assert exported.exit_code == 0, exported.output
    assert json.loads(exported.output) == selected
    assert str(signer_path) not in exported.output
    owner_access.owner = GatewayOwner(agent_id="other-peer", context_id="source-account")
    calls: list[Any] = []
    descriptor = GatewayEndpointDescriptor(
        protocol=GATEWAY_PROTOCOL_VERSION,
        target=_TARGET,
        presence_id=_PRESENCE,
        advertised_url=_URL,
        admin_mode="keyed",
    )

    def source_access(**kwargs: object) -> SimpleNamespace:
        """Resolve only the explicitly selected offline source from the local owner."""

        assert kwargs == {"agent_id": "other-peer", "agent_name": None}
        calls.append("source")
        return owner_access

    def fake_client(**kwargs: Any) -> SimpleNamespace:
        """Capture unsigned target verification before loading the independent signer."""

        if "binding" not in kwargs:
            calls.append("verify")
            return SimpleNamespace(describe_endpoint=lambda: descriptor)
        binding: GatewayClientBinding = kwargs["binding"]
        assert binding.owner == _TARGET.owner
        assert binding.purpose == "caller"
        assert binding.private_key_path == str(signer_path)
        assert kwargs["target_incarnation"] == _TARGET.incarnation
        assert kwargs["target_presence_id"] == _PRESENCE

        def operation(method: str, path: str, *, body: object) -> dict[str, str]:
            """Capture the exact operation handed to the proof-aware client."""

            calls.append((method, path, body))
            return {"status": "available"}

        return SimpleNamespace(request_json=operation)

    monkeypatch.setattr(commands, "GatewayClient", fake_client)
    monkeypatch.setattr(commands, "resolve_owner_gateway_access", source_access)
    result = _command("request", *_REMOTE, "--source-agent-id", "other-peer", "GET", "/v1/status")
    assert result == {"status": "available"}
    assert calls == ["verify", "source", ("GET", "/v1/status", None)]

    descriptor = descriptor.model_copy(update={"presence_id": "other-listener"})
    refused = CliRunner().invoke(
        cli, [*_SELECT, "request", *_REMOTE, "--source-agent-id", "other-peer", "GET", "/v1/status"]
    )
    assert refused.exit_code == 1
    assert "verify the selected gateway" in refused.output
    assert calls[-1] == "verify"


def test_roster_remove_does_not_repeat_after_unavailable_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A confirmed removal stays confirmed when the read-only roster observation fails."""

    key, signer_path, _ = _key(tmp_path, "operator")
    requests: list[str] = []
    descriptor = GatewayEndpointDescriptor(
        protocol=GATEWAY_PROTOCOL_VERSION,
        target=_TARGET,
        presence_id=_PRESENCE,
        advertised_url=_URL,
        admin_mode="keyed",
    )

    def fake_client(**kwargs: object) -> SimpleNamespace:
        """Record one mutation and make only its follow-up observation unavailable."""

        def describe() -> GatewayEndpointDescriptor:
            """Return initial metadata then simulate a transport error."""

            if requests:
                raise GatewayHttpError(method="GET", url=_URL, detail="unavailable")
            return descriptor

        return SimpleNamespace(describe_endpoint=describe, remove_admin_key=requests.append)

    monkeypatch.setattr(commands, "GatewayClient", fake_client)
    result = _command("admin-remove", *_REMOTE, key.key_id, "--signer", str(signer_path))
    assert result == {"key_id": key.key_id, "admin_mode": "unknown", "removed": True}
    assert requests == [key.key_id]


def test_peer_request_excludes_controls_with_dedicated_proof(tmp_path: Path) -> None:
    """Keep roster and browser commands in their separate client flows."""

    _, signer, _ = _key(tmp_path, "operator")
    client = GatewayClient(
        binding=GatewayClientBinding(
            base_url=_URL, owner=_OWNER, purpose="caller", private_key_path=str(signer)
        )
    )
    for route in ("/v1/admin/keys", "/v1/%61dmin/keys", "/v1/web/entry-ticket", "/v1/endpoint"):
        with pytest.raises(ValueError, match="protected gateway JSON operation"):
            client.request_json("POST", route)

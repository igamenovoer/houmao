"""Send real gateway proof from clients for synthetic runtime tests."""

from pathlib import Path
from collections.abc import Generator
from dataclasses import dataclass
from typing import Literal

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

import houmao.agents.realm_controller.gateway_service as gateway_service
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAdminKey,
    GatewayAccessStore,
    GatewayChallenge,
    GatewayChallengeRequest,
    GatewayRequestBinding,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewaySelfKey,
    GatewayTarget,
    load_gateway_signer,
    public_key_text,
    sign_sshsig,
    sshsig_header,
)
from houmao.gateway._access_sshsig import key_fingerprint
from houmao.gateway.deployment import GatewayDeployment


@dataclass(frozen=True)
class FixtureGatewayAccess:
    """Supply an isolated owner and generation for a synthetic manifest."""

    store: GatewayAccessStore
    target: GatewayTarget
    private_root: Path
    execution_binding: None = None

    @property
    def owner(self) -> GatewayOwner:
        """Return the owner of the fixture gateway."""

        return self.target.owner

    def current_self(self) -> GatewaySelfKey:
        """Read the current self key from private fixture storage."""

        return self.store.load_self(self.target.incarnation)


def configure_fixture_gateway_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> FixtureGatewayAccess:
    """Resolve access from private fixture storage instead of an active agent."""

    owner = GatewayOwner(agent_id="fixture-agent", context_id="fixture-owner")
    private_root = tmp_path / "gateway-access"
    store = GatewayAccessStore.from_root(private_root, owner)
    target = GatewayTarget(owner=owner, incarnation="fixture-generation")
    store.initialize(GatewayLaunchSeed())
    store.provision_self(target.incarnation)
    access = FixtureGatewayAccess(store=store, target=target, private_root=private_root)
    monkeypatch.setattr(gateway_service, "gateway_access_for_manifest", lambda _path: access)
    monkeypatch.setattr(
        gateway_service, "load_gateway_deployment", lambda _path: GatewayDeployment()
    )
    return access


def fixture_admin_key(tmp_path: Path, principal: str) -> tuple[GatewayAdminKey, Path]:
    """Generate an explicitly selected fixture signer outside the repository."""

    secret = Ed25519PrivateKey.generate()
    path = tmp_path / f"{principal}.key"
    path.touch(mode=0o600, exist_ok=False)
    path.write_bytes(
        secret.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption(),
        )
    )
    return GatewayAdminKey(
        principal=principal, public_key=public_key_text(secret.public_key())
    ), path


def enroll_fixture_admin(client: TestClient, key: GatewayAdminKey, path: Path) -> None:
    """Prove possession of the first key and check the safe enrollment response."""

    response = client.post(
        "/v1/admin/keys",
        json=key.model_dump(mode="json"),
        auth=FixtureProofAuth(path, purpose="register", proposed_key=key),
    )
    assert response.status_code == 201, response.text
    assert response.json() == {"key_id": key.key_id}


class FixtureProofAuth(httpx.Auth):
    """Exercise real challenge acquisition and signing from a fixture key."""

    requires_request_body = True
    requires_response_body = True

    def __init__(
        self,
        signer_path: Path,
        *,
        purpose: Literal["self", "admin", "register"] = "self",
        proposed_key: GatewayAdminKey | None = None,
    ) -> None:
        """Select an isolated fixture signer and challenge purpose."""

        self.m_signer = load_gateway_signer(signer_path)
        self.m_purpose = purpose
        self.m_proposed_key = proposed_key

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Request a signed challenge for the exact outgoing test request."""

        response = yield request
        if response.status_code != 401 or not response.headers.get("WWW-Authenticate"):
            return
        raw_path, _, query = request.url.raw_path.partition(b"?")
        key_id = (
            key_fingerprint(public_key_text(self.m_signer.public_key()))
            if self.m_purpose == "admin"
            else None
        )
        challenge_request = GatewayChallengeRequest(
            purpose=self.m_purpose,
            request=GatewayRequestBinding.from_request(
                request.method, raw_path.decode(), query.decode(), request.content
            ),
            key_id=key_id,
            proposed_key=self.m_proposed_key,
        )
        challenge_response = yield httpx.Request(
            "POST",
            request.url.copy_with(path="/v1/auth/challenge", query=None),
            json=challenge_request.model_dump(mode="json"),
        )
        challenge_response.raise_for_status()
        challenge = GatewayChallenge.model_validate_json(challenge_response.content)
        request.headers[CHALLENGE_HEADER] = challenge.challenge_id
        request.headers[SIGNATURE_HEADER] = sshsig_header(
            sign_sshsig(self.m_signer, challenge.signing_bytes())
        )
        yield request


def self_fixture_auth(runtime: GatewayServiceRuntime) -> FixtureProofAuth:
    """Select the current test fixture generation's configured key."""

    access = runtime.m_access_runtime
    assert access is not None
    return FixtureProofAuth(access.store.self_signer_path(access.target.incarnation))


def gateway_fixture_client(
    runtime: GatewayServiceRuntime, *, app: FastAPI | None = None
) -> TestClient:
    """Create a TestClient used by behavior tests that expect admitted gateway access."""

    selected_app = create_app(runtime=runtime) if app is None else app
    client = TestClient(selected_app, base_url=runtime.owner_connect_url)
    client.auth = self_fixture_auth(runtime)
    return client

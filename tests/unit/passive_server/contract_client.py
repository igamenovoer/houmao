"""Supply real admitted policy to passive HTTP contract tests with mocked runtimes."""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import httpx
import pytest

from houmao.gateway.access import (
    CHALLENGE_HEADER,
    SIGNATURE_HEADER,
    GatewayAccessPolicy,
    GatewayAccessStore,
    GatewayChallengeRequest,
    GatewayLaunchSeed,
    GatewayOwner,
    GatewayRequestBinding,
    GatewayTarget,
    load_gateway_signer,
    sign_sshsig,
    sshsig_header,
)
from houmao.passive_server.admission import PassiveAccessTarget, passive_route_access
from houmao.passive_server.discovery import DiscoveredAgent
from houmao.passive_server.service import PassiveServerService


def arrange_passive_launch_access(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Provide owned access state when the test replaces the runtime launcher."""

    owner = GatewayOwner(agent_id="fixture-agent", context_id="fixture-owner")
    target = GatewayTarget(owner=owner, incarnation="fixture-generation")
    root = path / "launch-authority"
    store = GatewayAccessStore.from_root(root, owner=owner)
    store.initialize(GatewayLaunchSeed())
    monkeypatch.setattr(
        "houmao.passive_server.headless.gateway_access_for_manifest",
        lambda _: SimpleNamespace(target=target, private_root=root),
    )


class AdmittedPassiveClient(TestClient):
    """Supply empty admin policy and current signed self for fixture-owned routes."""

    def __init__(self, app: FastAPI, *, extra_refs: Iterable[str] = ()) -> None:
        """Stage authority for the mocked bodies introduced by a transport test."""

        service: PassiveServerService = app.state.passive_service
        super().__init__(app, base_url=service.m_config.api_base_url)
        roots = service.m_config.runtime_root / "passive-contract-authority"
        cached: dict[tuple[str, str], PassiveAccessTarget] = {}

        def resolve(agent_ref: str) -> PassiveAccessTarget | tuple[int, dict[str, Any]]:
            """Select only explicitly provided discovered, managed, or fixture aliases."""

            discovered = service._resolve_agent_or_error(agent_ref)
            if isinstance(discovered, tuple) and discovered[0] == 409:
                return discovered
            matches = service.m_headless.resolve_usage_matches(agent_ref)
            if len(matches) > 1:
                return (409, {"detail": "Ambiguous managed agent reference"})
            tracked_id = matches[0] if matches else None
            authority = service.m_headless.access_authority(tracked_id) if tracked_id else None
            if isinstance(discovered, DiscoveredAgent):
                agent_id = discovered.record.agent_id
                generation = discovered.record.generation_id
                manifest_path = Path(discovered.record.runtime.manifest_path)
            elif authority is not None:
                agent_id = authority.agent_id or authority.tracked_agent_id
                generation = "managed-test-generation"
                manifest_path = Path(authority.manifest_path)
            elif agent_ref in extra_refs:
                agent_id = agent_ref
                generation = "synthetic-test-generation"
                manifest_path = roots / "fixture-manifest.json"
            else:
                return (404, {"detail": "Agent not found"})
            key = (agent_id, generation)
            existing = cached.get(key)
            if existing is not None:
                return existing
            owner = GatewayOwner(agent_id=agent_id, context_id="test-policy-context")
            target = GatewayTarget(owner=owner, incarnation=generation)
            private_root = roots / hashlib.sha256(f"{agent_id}/{generation}".encode()).hexdigest()
            store = GatewayAccessStore.from_root(private_root, owner=owner)
            store.initialize(GatewayLaunchSeed())
            own_key = store.provision_self(generation)
            runtime = SimpleNamespace(
                target=target, private_root=private_root, store=store, require_current=lambda: None
            )
            policy = GatewayAccessPolicy(
                store=store, target=lambda: target, current_self=lambda: own_key
            )
            selection = PassiveAccessTarget(runtime, policy, tracked_id, manifest_path)
            cached[key] = selection
            return selection

        self.m_resolve = resolve
        self.m_routes = [route for route in app.routes if isinstance(route, APIRoute)]
        self.m_issuer = service.m_config.api_base_url
        service.resolve_access_target = resolve  # type: ignore[method-assign]

    def request(self, method: str, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        """Sign only matched private operations, using the exact test HTTP body."""

        follow = kwargs.pop("follow_redirects", httpx.USE_CLIENT_DEFAULT)
        auth = kwargs.pop("auth", httpx.USE_CLIENT_DEFAULT)
        request = self.build_request(method, url, **kwargs)
        for route in self.m_routes:
            match = route.path_regex.fullmatch(request.url.path)
            if not match or request.method not in (route.methods or ()):
                continue
            if passive_route_access(request.method, route.path) != "private":
                break
            selected = self.m_resolve(match.group("agent_ref"))
            if isinstance(selected, tuple):
                break
            path, _, query = request.url.raw_path.decode("ascii").partition("?")
            binding = GatewayRequestBinding.from_request(
                request.method, path, query, request.read()
            )
            challenge = selected.policy.issue(
                self.m_issuer, GatewayChallengeRequest(purpose="self", request=binding)
            )
            runtime = selected.runtime
            key = load_gateway_signer(runtime.store.self_signer_path(runtime.target.incarnation))
            request.headers[CHALLENGE_HEADER] = challenge.challenge_id
            request.headers[SIGNATURE_HEADER] = sshsig_header(
                sign_sshsig(key, challenge.signing_bytes())
            )
            break
        return self.send(request, auth=auth, follow_redirects=follow)

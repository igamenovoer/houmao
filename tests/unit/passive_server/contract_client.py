"""Supply real admitted policy to passive HTTP contract tests with mocked runtimes."""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from houmao.gateway.access import GatewayAccessPolicy, GatewayOwner, GatewayTarget
from houmao.gateway.authorization_store import AuthorizationStore
from houmao.passive_server.admission import PASSIVE_PERMISSIONS, PassiveAccessTarget
from houmao.passive_server.discovery import DiscoveredAgent
from houmao.passive_server.service import PassiveServerService


def arrange_passive_launch_access(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    """Provide owned access state when the test replaces the runtime launcher."""

    owner = GatewayOwner(agent_id="fixture-agent", context_id="fixture-owner")
    target = GatewayTarget(owner=owner, incarnation="fixture-generation")
    root = path / "launch-authority"
    store = AuthorizationStore(root, owner)
    store.initialize()
    monkeypatch.setattr(
        "houmao.passive_server.headless.gateway_access_for_manifest",
        lambda _: SimpleNamespace(target=target, private_root=root),
    )


class AdmittedPassiveClient(TestClient):
    """Supply valid empty-roster policy for fixture-owned routes."""

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
            execution = (
                getattr(discovered.record, "execution_binding", None)
                if isinstance(discovered, DiscoveredAgent)
                else None
            )
            owner = GatewayOwner(
                agent_id=agent_id,
                context_id=execution.context_id if execution is not None else "test-policy-context",
            )
            target = GatewayTarget(owner=owner, incarnation=generation)
            private_root = roots / hashlib.sha256(f"{agent_id}/{generation}".encode()).hexdigest()
            store = AuthorizationStore(private_root, owner)
            store.initialize()
            runtime = SimpleNamespace(
                target=target,
                private_root=private_root,
                store=store,
                require_current=lambda: None,
                execution_binding=execution,
            )
            policy = GatewayAccessPolicy(
                store=store,
                target=lambda: target,
                current_self=lambda: None,
                listener_id=service.m_access_listener_id,
                catalog=lambda: PASSIVE_PERMISSIONS,
            )
            selection = PassiveAccessTarget(runtime, policy, tracked_id, manifest_path)
            cached[key] = selection
            return selection

        service.resolve_access_target = resolve  # type: ignore[method-assign]

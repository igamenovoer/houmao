"""Read-only native Web observation with verified gateway and direct sources."""

from __future__ import annotations

from collections import deque
from pathlib import Path
import threading
from typing import Any, Callable, Protocol, cast

from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayAttachBackendMetadataWebV1,
    GatewayWebControlStateV1,
    GatewayWebHistoryEntryV1,
    GatewayWebHistoryV1,
)
from houmao.agents.realm_controller.gateway_storage import web_attach_metadata_from_state
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.managed_control import MANAGED_WEB_BACKENDS
from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1
from houmao.agents.realm_controller.runtime import resume_runtime_session
from houmao.agents.realm_controller.web_observation import WebObservation, web_state_is_fresh
from houmao.passive_server.discovery import DiscoveredAgent
from houmao.passive_server.models import AgentWebHistoryResponse, AgentWebStateResponse


class _ReadOnlyWebBackend(Protocol):
    """Native observation methods that cannot create, resume, or send input."""

    def observe_web_state(self) -> dict[str, Any]:
        """Read native state and pending interactions."""

    def observe_web_history(self, *, after_sequence: int, limit: int) -> dict[str, Any]:
        """Read native transition metadata."""


class AgentWebObserver:
    """Keep one discovered Web binding observable without terminal parsing."""

    def __init__(self, *, agent: DiscoveredAgent) -> None:
        """Retain discovery identity; establish connections only during reads."""

        self.m_agent: DiscoveredAgent = agent
        self.m_lock: threading.RLock = threading.RLock()
        self.m_metadata: GatewayAttachBackendMetadataWebV1 | None = None
        self.m_direct: WebObservation | None = None
        self.m_close_direct: Callable[[], None] | None = None
        self.m_state: GatewayWebControlStateV1 | None = None
        self.m_entries: deque[GatewayWebHistoryEntryV1] = deque(maxlen=100)
        self.m_reconciled: bool = False

    def set_agent(self, agent: DiscoveredAgent) -> None:
        """Refresh discovery metadata without writing its manifest or native host."""

        with self.m_lock:
            self.m_agent = agent

    def _read_metadata(self) -> GatewayAttachBackendMetadataWebV1:
        """Require current manifest authority to match the discovered generation."""

        record = self.m_agent.record
        handle = load_session_manifest(Path(record.runtime.manifest_path))
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
        metadata = web_attach_metadata_from_state(payload.backend_state, backend=payload.backend)
        surface = getattr(record, "native_surface", None)
        if (
            payload.backend not in MANAGED_WEB_BACKENDS
            or record.identity.backend != payload.backend
            or not isinstance(surface, WebNativeSurfaceV1)
            or surface.origin != metadata.origin
            or surface.native_session_id != metadata.identity.native_session_id
            or metadata.identity.agent_id != record.agent_id
            or metadata.identity.generation != record.generation_id
            or metadata.identity.runtime_session_id != payload.runtime.session_id
        ):
            raise SessionManifestError("Discovered Web authority differs from the current manifest")
        return metadata

    def poll_cycle(self) -> None:
        """Refresh Web state independently of any supervisor pane or parser."""

        with self.m_lock:
            metadata = self._read_metadata()
            if metadata != self.m_metadata:
                if self.m_close_direct is not None:
                    self.m_close_direct()
                    self.m_close_direct = None
                self.m_metadata = metadata
                self.m_direct = None
                self.m_entries.clear()
                self.m_reconciled = False
            gateway = self.m_agent.record.gateway
            if gateway is not None and gateway.host is not None and gateway.port is not None:
                try:
                    client = GatewayClient(
                        endpoint=GatewayEndpoint(host=gateway.host, port=gateway.port),
                        timeout_seconds=1.0,
                    )
                    state = client.get_web_state()
                    if (
                        state.identity != metadata.identity
                        or state.origin != metadata.origin
                        or state.browser_url != metadata.browser_url
                        or state.availability != "available"
                        or not web_state_is_fresh(state)
                    ):
                        raise ValueError("Gateway Web source is stale or unavailable")
                    history = client.get_web_history(limit=100)
                    if history.sequence < state.sequence:
                        raise ValueError("Gateway native history is behind its state snapshot")
                    self._merge_history(history)
                    self.m_state = state.model_copy(update={"source": "gateway"})
                    return
                except (GatewayHttpError, OSError, RuntimeError, ValueError):
                    pass
            try:
                if self.m_direct is None:
                    agent_def_dir = self.m_agent.record.runtime.agent_def_dir
                    if agent_def_dir is None:
                        raise SessionManifestError(
                            "Direct Web observation needs private runtime authority"
                        )
                    # Reconstructing a controller only attaches to this Web host.
                    controller = resume_runtime_session(
                        agent_def_dir=Path(agent_def_dir),
                        session_manifest_path=Path(self.m_agent.record.runtime.manifest_path),
                        read_only=True,
                    )
                    backend = cast(_ReadOnlyWebBackend, controller.backend_session)
                    closer = getattr(backend, "close_control_connection", None)
                    self.m_close_direct = closer if callable(closer) else None
                    self.m_direct = WebObservation(
                        metadata=metadata,
                        state=backend.observe_web_state,
                        history=backend.observe_web_history,
                        sparse_history=self.m_agent.record.identity.backend == "kimi_web",
                    )
                self.m_state = self.m_direct.refresh()
                self._merge_history(self.m_direct.history(limit=100))
            except (OSError, RuntimeError, ValueError):
                self.m_reconciled = False
                self.m_state = self._unavailable(metadata)

    def current_state(self) -> AgentWebStateResponse:
        """Return fresh native compact state, closing readiness on observation loss."""

        with self.m_lock:
            try:
                self.poll_cycle()
            except (OSError, RuntimeError, ValueError):
                self.m_reconciled = False
                if self.m_metadata is None:
                    raise SessionManifestError("Verified Web identity is unavailable")
                self.m_state = self._unavailable(self.m_metadata)
            assert self.m_state is not None
            return AgentWebStateResponse(
                agent_id=self.m_agent.record.agent_id,
                agent_name=self.m_agent.record.agent_name,
                web=self.m_state,
            )

    def history(self, *, limit: int = 50) -> AgentWebHistoryResponse:
        """Return bounded native transitions across safe source changes."""

        with self.m_lock:
            self.current_state()
            assert self.m_metadata is not None
            return AgentWebHistoryResponse(
                agent_id=self.m_agent.record.agent_id,
                agent_name=self.m_agent.record.agent_name,
                web=GatewayWebHistoryV1(
                    identity=self.m_metadata.identity,
                    sequence=self.m_state.sequence if self.m_state is not None else 0,
                    entries=list(reversed(self.m_entries))[: max(0, min(limit, 500))],
                    has_more=len(self.m_entries) > limit,
                    reconciled=self.m_reconciled,
                ),
            )

    def close(self) -> None:
        """Discard observation state without stopping or detaching the native agent."""

        with self.m_lock:
            if self.m_close_direct is not None:
                self.m_close_direct()
                self.m_close_direct = None
            self.m_direct = None
            self.m_state = None
            self.m_entries.clear()

    def _merge_history(self, history: GatewayWebHistoryV1) -> None:
        """Deduplicate native identities and preserve original execution attribution."""

        assert self.m_metadata is not None
        if history.identity != self.m_metadata.identity or not history.reconciled:
            raise ValueError("Web history authority is unavailable")
        merged = {entry.sequence: entry for entry in self.m_entries}
        for entry in history.entries:
            if entry.identity != self.m_metadata.identity:
                raise ValueError("Native history execution differs from the current binding")
            previous = merged.get(entry.sequence)
            if previous is not None and previous != entry:
                raise ValueError("Native history sequence changed")
            merged[entry.sequence] = entry
        self.m_entries.clear()
        self.m_entries.extend(merged[key] for key in sorted(merged)[-100:])
        self.m_reconciled = True

    def _unavailable(self, metadata: GatewayAttachBackendMetadataWebV1) -> GatewayWebControlStateV1:
        """Return explicit unavailable Web state without preserving stale idle facts."""

        state = WebObservation(
            metadata=metadata, state=lambda: {}, history=lambda **_: {}
        ).unavailable()
        return state.model_copy(
            update={"sequence": max((entry.sequence for entry in self.m_entries), default=0)}
        )

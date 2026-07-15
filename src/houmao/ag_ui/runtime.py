"""Runtime observation contracts used by AG-UI run streaming."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from houmao.ag_ui.state import GatewayStatusSnapshot, JsonObject, JsonValue
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayRequestCreateV1,
)

AgUiTargetTransportFamily = Literal["headless", "tui", "http_rest", "unknown"]
AgUiObservedRequestTerminalState = Literal["completed", "failed", "coalesced"]


@dataclass(frozen=True)
class AgUiObservedRequestState:
    """Observed durable gateway request state for one admitted AG-UI run."""

    request_id: str
    request_kind: str
    state: str
    accepted_at_utc: str
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    error_detail: str | None = None
    result: JsonValue = None

    @property
    def terminal(self) -> bool:
        """Return whether the durable gateway request reached a final state."""

        return self.state in {"completed", "failed", "coalesced"}

    @property
    def failed(self) -> bool:
        """Return whether the durable gateway request failed."""

        return self.state == "failed"


@dataclass(frozen=True)
class AgUiHeadlessArtifactObservation:
    """Resolved headless artifact paths for one AG-UI run id."""

    run_id: str
    turn_dir: Path
    canonical_events_path: Path
    provider: str
    artifact_available: bool


@dataclass(frozen=True)
class AgUiTuiObservation:
    """Sanitized TUI observation snapshot for a lower-fidelity AG-UI stream."""

    available: bool
    status: JsonObject
    activity: str | None = None
    final_text: str | None = None
    state: JsonObject | None = None


class AgUiRuntimeObservationProtocol(Protocol):
    """Gateway runtime subset used by AG-UI run admission and observation."""

    def status(self) -> GatewayStatusSnapshot:
        """Return the current gateway status."""

    def create_request(self, request_payload: GatewayRequestCreateV1) -> GatewayAcceptedRequestV1:
        """Admit one gateway request through the existing gateway controls."""

    def ag_ui_request_state(self, request_id: str) -> AgUiObservedRequestState | None:
        """Return observed request state for one admitted request id."""

    def ag_ui_target_transport_family(self) -> AgUiTargetTransportFamily:
        """Return the target transport family for AG-UI mapping decisions."""

    def ag_ui_headless_artifact(self, run_id: str) -> AgUiHeadlessArtifactObservation | None:
        """Return headless artifact paths for one AG-UI run id when available."""

    def ag_ui_tui_observation(self) -> AgUiTuiObservation:
        """Return sanitized TUI observation for lower-fidelity AG-UI streaming."""


def ag_ui_target_transport_family_for_backend(backend: str) -> AgUiTargetTransportFamily:
    """Map one gateway backend value to the AG-UI observation family."""

    if backend in {"claude_headless", "codex_headless", "kimi_headless"}:
        return "headless"
    if backend in {"local_interactive", "cao_rest"}:
        return "tui"
    if backend in {"codex_app_server", "houmao_server_rest"}:
        return "http_rest"
    return "unknown"

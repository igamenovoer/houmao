"""Runtime observation contracts used by AG-UI run streaming."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from houmao.ag_ui.state import GatewayStatusSnapshot, JsonObject, JsonValue
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayRequestCreateV1,
    GatewayServiceRequestSnapshotV1,
    GatewayWebControlStateV1,
)
from houmao.agents.realm_controller.managed_control import MANAGED_SERVICE_BACKENDS
from houmao.agents.realm_controller.run_modes import RunMode

AgUiTargetTransportFamily = Literal["headless", "tui", "service", "web", "http_rest", "unknown"]


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
    service_request: GatewayServiceRequestSnapshotV1 | None = None

    @property
    def terminal(self) -> bool:
        """Return whether the durable gateway request reached a final state."""

        return self.state in {"completed", "failed", "coalesced", "uncertain"}

    @property
    def failed(self) -> bool:
        """Return whether the durable gateway request failed."""

        return self.state in {"failed", "uncertain"}


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

    def create_request(
        self, request_payload: GatewayRequestCreateV1, *, ready_only: bool = False
    ) -> GatewayAcceptedRequestV1:
        """Admit one gateway request through the existing gateway controls."""

    def ag_ui_request_state(self, request_id: str) -> AgUiObservedRequestState | None:
        """Return observed request state for one admitted request id."""

    def ag_ui_target_transport_family(self) -> AgUiTargetTransportFamily:
        """Return the target transport family for AG-UI mapping decisions."""

    def ag_ui_headless_artifact(self, run_id: str) -> AgUiHeadlessArtifactObservation | None:
        """Return headless artifact paths for one AG-UI run id when available."""

    def ag_ui_tui_observation(self) -> AgUiTuiObservation:
        """Return sanitized TUI observation for lower-fidelity AG-UI streaming."""

    def ag_ui_web_observation(self) -> GatewayWebControlStateV1:
        """Return structured native Web state without inventing output ownership."""


def ag_ui_target_transport_family_for_backend(backend: str) -> AgUiTargetTransportFamily:
    """Map one gateway backend value to the AG-UI observation family."""

    if backend in {"claude_headless", "codex_headless", "kimi_headless", "dsh_headless"}:
        return "headless"
    if backend in {"dsh_web", "kimi_web"}:
        return "web"
    if backend in MANAGED_SERVICE_BACKENDS:
        return "service"
    if backend in {"local_interactive", "cao_rest"}:
        return "tui"
    if backend == "houmao_server_rest":
        return "http_rest"
    return "unknown"


def ag_ui_target_transport_family_for_mode(mode: RunMode | None) -> AgUiTargetTransportFamily:
    """Select native observation from the verified owner mode."""

    return mode if mode is not None else "unknown"

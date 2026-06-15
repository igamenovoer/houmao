"""Sanitized Houmao state snapshots for AG-UI `STATE_SNAPSHOT` events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Protocol, TypeAlias

from houmao.ag_ui.connection import AgUiConnectionRecord

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


class GatewayStatusSnapshot(Protocol):
    """Gateway status fields safe for AG-UI snapshot export."""

    @property
    def attach_identity(self) -> str: ...

    @property
    def backend(self) -> str: ...

    @property
    def tmux_session_name(self) -> str: ...

    @property
    def gateway_health(self) -> str: ...

    @property
    def managed_agent_connectivity(self) -> str: ...

    @property
    def managed_agent_recovery(self) -> str: ...

    @property
    def request_admission(self) -> str: ...

    @property
    def terminal_surface_eligibility(self) -> str: ...

    @property
    def active_execution(self) -> str: ...

    @property
    def execution_mode(self) -> str: ...

    @property
    def queue_depth(self) -> int: ...

    @property
    def gateway_host(self) -> str | None: ...

    @property
    def gateway_port(self) -> int | None: ...

    @property
    def gateway_tmux_window_id(self) -> str | None: ...

    @property
    def gateway_tmux_window_index(self) -> str | None: ...

    @property
    def gateway_tmux_pane_id(self) -> str | None: ...

    @property
    def managed_agent_instance_epoch(self) -> int: ...

    @property
    def managed_agent_instance_id(self) -> str | None: ...


def build_houmao_state_snapshot(
    *,
    status: GatewayStatusSnapshot,
    connection: AgUiConnectionRecord,
) -> JsonObject:
    """Build a namespaced, sanitized Houmao state snapshot for AG-UI clients."""

    gateway: JsonObject = {
        "attachIdentity": status.attach_identity,
        "backend": status.backend,
        "tmuxSessionName": status.tmux_session_name,
        "availability": status.gateway_health,
        "managedAgentConnectivity": status.managed_agent_connectivity,
        "managedAgentRecovery": status.managed_agent_recovery,
        "requestAdmission": status.request_admission,
        "terminalSurfaceEligibility": status.terminal_surface_eligibility,
        "executionMode": status.execution_mode,
        "targetTransportFamily": _target_transport_family(status.backend),
        "managedAgentInstanceEpoch": status.managed_agent_instance_epoch,
    }
    if status.gateway_host is not None:
        gateway["host"] = status.gateway_host
    if status.gateway_port is not None:
        gateway["port"] = status.gateway_port
    if status.managed_agent_instance_id is not None:
        gateway["managedAgentInstanceId"] = status.managed_agent_instance_id
    if status.gateway_tmux_window_id is not None:
        gateway["gatewayTmuxWindowId"] = status.gateway_tmux_window_id
    if status.gateway_tmux_window_index is not None:
        gateway["gatewayTmuxWindowIndex"] = status.gateway_tmux_window_index
    if status.gateway_tmux_pane_id is not None:
        gateway["gatewayTmuxPaneId"] = status.gateway_tmux_pane_id

    active_execution: JsonObject = {
        "state": status.active_execution,
        "queueDepth": status.queue_depth,
        "requestAdmission": status.request_admission,
    }
    connection_state: JsonObject = {
        "connectionId": connection.connection_id,
        "threadId": connection.thread_id,
        "runId": connection.run_id,
        "createdAtUtc": _format_utc(connection.created_at_utc),
        "detached": connection.detached,
    }
    if connection.parent_run_id is not None:
        connection_state["parentRunId"] = connection.parent_run_id
    if connection.last_seen_event_id is not None:
        connection_state["lastSeenEventId"] = connection.last_seen_event_id

    return {
        "houmao": {
            "schemaVersion": 1,
            "connection": connection_state,
            "gateway": gateway,
            "activeExecution": active_execution,
            "endpoints": {
                "status": "/v1/status",
                "capabilities": "/v1/ag-ui/capabilities",
                "connect": "/v1/ag-ui/connect",
                "disconnect": "/v1/ag-ui/connections/{connection_id}",
                "runs": "/v1/ag-ui/runs",
            },
            "lifecycle": {
                "agentLifecycleManagedByGui": False,
                "detachOnly": True,
            },
        }
    }


def _target_transport_family(backend: str) -> Literal["http_rest", "tmux"]:
    """Return the compact transport family exposed to AG-UI clients."""

    if backend in {"cao_rest", "houmao_server_rest"}:
        return "http_rest"
    return "tmux"


def _format_utc(value: datetime) -> str:
    """Return an ISO-8601 UTC timestamp suitable for JSON state snapshots."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")

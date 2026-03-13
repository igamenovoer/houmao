# Gateway Protocol And State Contracts

This page explains the current v1 gateway contracts: how attachability is published, what the live HTTP surface looks like, and which files under `gateway/` are durable versus ephemeral.

## Mental Model

The gateway contract has two layers.

- Stable attachability tells the runtime how a session could gain a gateway.
- Live gateway bindings describe one currently running gateway instance.

Those layers are kept separate so a session can stay gateway-capable even when no sidecar is running.

## Stable Attachability

Stable attachability is published in two ways:

- tmux env pointers:
  - `AGENTSYS_GATEWAY_ATTACH_PATH`
  - `AGENTSYS_GATEWAY_ROOT`
- strict attach contract:
  - `<session-root>/gateway/attach.json`

Representative CAO-backed attach contract:

```json
{
  "schema_version": 1,
  "attach_identity": "cao-rest-1",
  "backend": "cao_rest",
  "tmux_session_name": "AGENTSYS-gpu",
  "working_directory": "/abs/path/repo",
  "backend_metadata": {
    "api_base_url": "http://localhost:9889",
    "terminal_id": "term-123",
    "profile_name": "runtime-profile",
    "profile_path": "/abs/path/runtime-profile.md",
    "parsing_mode": "shadow_only"
  },
  "manifest_path": "/abs/path/tmp/agents-runtime/sessions/cao_rest/cao-rest-1/manifest.json",
  "agent_def_dir": "/abs/path/tests/fixtures/agents",
  "runtime_session_id": "cao-rest-1",
  "desired_host": "127.0.0.1",
  "desired_port": 43123
}
```

Current v1 scope:

- Runtime-owned tmux-backed sessions publish gateway capability.
- Live attach is implemented first for `backend=cao_rest`.
- Headless backends can still be gateway-capable at the attach-contract layer even though the live adapter boundary is narrower today.

## Live Gateway Bindings

Live bindings exist only while a gateway process is running.

Published tmux env vars:

- `AGENTSYS_AGENT_GATEWAY_HOST`
- `AGENTSYS_AGENT_GATEWAY_PORT`
- `AGENTSYS_GATEWAY_STATE_PATH`
- `AGENTSYS_GATEWAY_PROTOCOL_VERSION`

Important rules:

- The runtime validates these bindings structurally before trusting them.
- `GET /health` is the authoritative liveness check for the live gateway.
- A dead gateway can leave stale env behind temporarily; validation plus health probing is what cleans that up.

## HTTP Surface

Current v1 routes:

- `GET /health`
- `GET /v1/status`
- `POST /v1/requests`

### `GET /health`

Gateway-local liveness only:

```json
{
  "protocol_version": "v1",
  "status": "ok"
}
```

This does not mean the managed agent is available. It only means the gateway control plane is alive enough to serve its contract.

### `GET /v1/status`

Status is shared by the live HTTP route and `state.json`.

Representative live status:

```json
{
  "schema_version": 1,
  "protocol_version": "v1",
  "attach_identity": "cao-rest-1",
  "backend": "cao_rest",
  "tmux_session_name": "AGENTSYS-gpu",
  "gateway_health": "healthy",
  "managed_agent_connectivity": "connected",
  "managed_agent_recovery": "idle",
  "request_admission": "open",
  "terminal_surface_eligibility": "ready",
  "active_execution": "idle",
  "queue_depth": 0,
  "gateway_host": "127.0.0.1",
  "gateway_port": 43123,
  "managed_agent_instance_epoch": 1,
  "managed_agent_instance_id": "term-123"
}
```

Representative seeded offline status:

```json
{
  "schema_version": 1,
  "protocol_version": "v1",
  "attach_identity": "cao-rest-1",
  "backend": "cao_rest",
  "tmux_session_name": "AGENTSYS-gpu",
  "gateway_health": "not_attached",
  "managed_agent_connectivity": "unavailable",
  "managed_agent_recovery": "idle",
  "request_admission": "blocked_unavailable",
  "terminal_surface_eligibility": "unknown",
  "active_execution": "idle",
  "queue_depth": 0,
  "managed_agent_instance_epoch": 0
}
```

Current status axes:

- `gateway_health`: `healthy` or `not_attached`
- `managed_agent_connectivity`: `connected` or `unavailable`
- `managed_agent_recovery`: `idle`, `awaiting_rebind`, or `reconciliation_required`
- `request_admission`: `open`, `blocked_unavailable`, or `blocked_reconciliation`
- `terminal_surface_eligibility`: `ready`, `unknown`, or `not_ready`
- `active_execution`: `idle` or `running`

### `POST /v1/requests`

Current public request kinds:

- `submit_prompt`
- `interrupt`

Representative prompt submission:

```json
{
  "schema_version": 1,
  "kind": "submit_prompt",
  "payload": {
    "prompt": "hello"
  }
}
```

Representative accepted response:

```json
{
  "request_id": "gwreq-20260313-000000Z-deadbeef",
  "request_kind": "submit_prompt",
  "state": "accepted",
  "accepted_at_utc": "2026-03-13T00:00:00+00:00",
  "queue_depth": 1,
  "managed_agent_instance_epoch": 1
}
```

Observable current error semantics:

- malformed request payloads return HTTP `422` from FastAPI validation,
- reconciliation-blocked admission returns HTTP `409`,
- unavailable managed-agent admission returns HTTP `503`.

The broader design leaves room for more policy-driven rejection states, but the current implementation should be documented as it exists today.

## Durable And Ephemeral Gateway Artifacts

Representative gateway tree:

```text
<session-root>/gateway/
  attach.json
  protocol-version.txt
  desired-config.json
  state.json
  queue.sqlite
  events.jsonl
  logs/
    gateway.log
  run/
    current-instance.json
    gateway.pid
```

Artifact roles:

- `attach.json`: stable attachability contract
- `protocol-version.txt`: simple version marker for local artifacts
- `desired-config.json`: desired host and port to reuse on later starts
- `state.json`: read-optimized current status contract
- `queue.sqlite`: durable queue records
- `events.jsonl`: append-only event log
- `logs/gateway.log`: gateway process output
- `run/current-instance.json`: current process id, host, port, epoch, and instance id
- `run/gateway.pid`: pidfile mirror

## Current Implementation Notes

- `state.json` exists even before the first live attach.
- Offline status must omit live `gateway_host` and `gateway_port`.
- The gateway client connects to `127.0.0.1` even when the published host is `0.0.0.0`, because `0.0.0.0` is a bind address, not a connect address.

## Source References

- [`src/gig_agents/agents/brain_launch_runtime/gateway_models.py`](../../../../src/gig_agents/agents/brain_launch_runtime/gateway_models.py)
- [`src/gig_agents/agents/brain_launch_runtime/gateway_storage.py`](../../../../src/gig_agents/agents/brain_launch_runtime/gateway_storage.py)
- [`src/gig_agents/agents/brain_launch_runtime/gateway_client.py`](../../../../src/gig_agents/agents/brain_launch_runtime/gateway_client.py)
- [`src/gig_agents/agents/brain_launch_runtime/runtime.py`](../../../../src/gig_agents/agents/brain_launch_runtime/runtime.py)

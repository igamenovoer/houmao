## Why

AG-UI enabled GUI tools need a way to observe an already-running Houmao agent without taking ownership of the agent process or replacing existing gateway APIs. The first step is a narrow per-agent gateway attachment surface that proves AG-UI protocol shape, status streaming, and lifecycle boundaries before adding task-run streaming or CopilotKit graphics.

## What Changes

- Add a separate AG-UI API namespace to the live per-agent gateway under `/v1/ag-ui`.
- Add AG-UI model and SSE encoder boundaries under `houmao.ag_ui`.
- Add a conservative capabilities endpoint for GUI feature discovery.
- Add a `connect` endpoint that accepts AG-UI-shaped input, creates a GUI connection record, emits an AG-UI `STATE_SNAPSHOT`, and follows attach-session lifecycle without submitting work.
- Add an explicit `disconnect` endpoint that removes GUI connection bookkeeping only.
- Add a `/runs` route shell that reports task-run submission as unavailable until the next AG-UI milestone.
- Define connect/disconnect semantics so GUI attachment never starts, stops, aborts, interrupts, or restarts the Houmao agent.
- Add unit tests for route registration, capabilities, camelCase parsing, SSE framing, sanitized state snapshots, and no prompt or lifecycle side effects.

## Capabilities

### New Capabilities

- `per-agent-ag-ui-attachment`: Live per-agent gateway AG-UI attachment API, conservative capabilities reporting, AG-UI SSE framing, and GUI connect/disconnect semantics for observing an existing Houmao agent.

### Modified Capabilities

- None.

## Impact

- Affected code includes `src/houmao/agents/realm_controller/gateway_service.py`, new `src/houmao/ag_ui/` adapter modules, packaging dependency declarations, and focused unit tests under `tests/unit/`.
- The live per-agent gateway gains new HTTP routes under `/v1/ag-ui` while existing Houmao gateway routes remain unchanged.
- The preferred dependency is `ag-ui-protocol>=0.1.19,<0.2`, kept behind the `houmao.ag_ui` boundary; if dependency resolution is unsuitable, the implementation may carry minimal internal models that preserve the same wire contract.
- `houmao-passive-server`, AG-UI task-run streaming, and CopilotKit graphics rendering remain out of scope for this change.

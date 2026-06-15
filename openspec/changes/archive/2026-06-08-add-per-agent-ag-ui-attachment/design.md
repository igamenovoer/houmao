## Context

Houmao already exposes a live per-agent gateway through `GatewayServiceRuntime` and `create_app()` in `src/houmao/agents/realm_controller/gateway_service.py`. That gateway owns existing status, memory, control, request, reminder, and mail APIs for one managed agent.

AG-UI clients expect JSON over HTTP SSE. The local AG-UI reference under `extern/orphan/ag-ui` defines `RunAgentInput`, event models, and an encoder that writes `data: <camelCase-json>\n\n` frames with `text/event-stream`. CopilotKit can proxy AG-UI run streams through `HttpAgent`, but its standard `HttpAgent` posts to a configured run URL. A direct Houmao `connect` endpoint is still useful as the attachment contract for GUI tools and for a future CopilotKit-side custom connect bridge.

The lifecycle boundary is the main constraint. Houmao owns the actual agent lifecycle. A GUI may attach, observe, submit future task runs, and detach, but it must not start, stop, restart, abort, or interrupt the managed Houmao agent through this milestone.

## Goals / Non-Goals

**Goals:**

- Add a separate AG-UI namespace to the live per-agent gateway.
- Provide AG-UI-compatible model parsing and SSE event encoding behind a `houmao.ag_ui` boundary.
- Let a GUI connect to an existing Houmao agent and receive an initial sanitized AG-UI `STATE_SNAPSHOT`.
- Keep a connection registry that can cleanly detach GUI sessions and can later support replay and live task events.
- Report truthful, conservative capabilities.
- Prove through tests that connect and disconnect do not submit prompts or invoke lifecycle control.

**Non-Goals:**

- Do not add AG-UI task-run streaming in this change.
- Do not add CopilotKit graphics rendering in this change.
- Do not add `houmao-passive-server` AG-UI proxy routes in this change.
- Do not support frontend tool execution, Open Generative UI, state deltas, or multimodal input in this change.
- Do not expose mailbox content, memory pages, raw terminal history, credentials, or arbitrary forwarded props in AG-UI state snapshots.

## Decisions

### Keep AG-UI code behind `houmao.ag_ui`

Add a small adapter package with modules such as `models.py`, `encoder.py`, `connection.py`, `capabilities.py`, and `routes.py`. Gateway code should call this package rather than directly spreading AG-UI model imports through existing gateway modules.

Alternative considered: define all AG-UI routes and models inline in `gateway_service.py`. That would ship quickly, but it would mix protocol-adapter code into an already large gateway module and make later run streaming harder to isolate.

### Prefer the upstream Python protocol package

Use `ag-ui-protocol>=0.1.19,<0.2` if dependency resolution works cleanly in the Pixi-managed environment. Wrap imported models and events through `houmao.ag_ui.models`, and wrap encoding through `houmao.ag_ui.encoder`.

Alternative considered: vendor only the minimal Pydantic models needed for connect and state snapshots. That avoids a new dependency, but it increases protocol drift risk and duplicates AG-UI's camelCase model behavior.

### Register routes from the per-agent gateway app

Wire AG-UI endpoints into the FastAPI app created by `create_app()`:

- `GET /v1/ag-ui/capabilities`
- `POST /v1/ag-ui/connect`
- `POST /v1/ag-ui/runs`
- `DELETE /v1/ag-ui/connections/{connection_id}`

The implementation may either call a helper such as `register_ag_ui_routes(app, runtime=runtime)` or define a small router factory under `houmao.ag_ui.routes`. Route registration should stay local to the live gateway for this change.

Alternative considered: add the routes first to `houmao-passive-server`. That central facade is useful later, but it would require streaming proxy semantics before the source per-agent event contract exists.

### Treat connect as a long-lived GUI attachment stream

`POST /v1/ag-ui/connect` should accept a `RunAgentInput`-shaped body plus optional `lastSeenEventId`, create a connection record, emit a current `STATE_SNAPSHOT`, then keep the SSE stream open until client disconnect or explicit deletion. The first implementation may replay only the current snapshot, but the registry and response generator should be shaped so compacted replay and live task-event follow can be added later.

Alternative considered: return one snapshot and immediately close. That is simpler to test, but it weakens the attach/detach semantics and forces a route-contract change once live follow is added.

### Sanitize state snapshots

The snapshot should contain a namespaced Houmao object with safe status fields derived from `GatewayServiceRuntime.status()`, such as gateway availability, transport type, active execution summary, connection id, thread id, run id, and supported endpoint metadata. It must omit raw prompt text, mailbox bodies, memory page contents, credential material, raw terminal history, and unmanaged forwarded props.

Alternative considered: dump the existing `GatewayStatusV1` object directly into AG-UI state. That would be convenient, but it risks leaking fields that are not intended for a GUI protocol and makes the AG-UI state contract dependent on internal gateway status shape.

### Keep `/runs` present but unavailable

Register `POST /v1/ag-ui/runs` now so route inventory and capabilities can describe the future API surface, but return a deterministic error until the next milestone implements run admission and task streaming. The response should not start an SSE stream and should not submit a prompt.

Alternative considered: omit `/runs` until run streaming is implemented. That avoids a placeholder route, but it makes client capability discovery less useful and hides the planned route namespace from early GUI integration tests.

### Make disconnect a detach-only operation

HTTP client disconnect and `DELETE /v1/ag-ui/connections/{connection_id}` should remove the GUI connection from registry state. They must not call prompt submission, stop, abort, interrupt, restart, or agent shutdown code.

Alternative considered: map disconnect or CopilotKit stop to an interrupt. That changes the underlying agent's work, while this milestone only changes GUI subscription state. Interrupt policy can be added later as an explicit opt-in.

## Risks / Trade-offs

- New dependency may not resolve cleanly in the managed environment -> Keep it behind `houmao.ag_ui` and fall back to minimal internal models only if needed.
- Long-lived SSE streams can be awkward to test with `TestClient` -> Unit-test the connection registry and encoder separately, then add a focused route smoke test for the first emitted frame.
- Snapshot sanitization can drift as `GatewayStatusV1` changes -> Build snapshots through an explicit sanitizer and test that sensitive fields are omitted.
- A placeholder `/runs` route could confuse clients -> Capabilities must report task runs as disabled, and the route must return a clear deterministic error.
- Connect replay beyond the current snapshot is not implemented yet -> Keep `lastSeenEventId` accepted but document that Milestone 1 only guarantees current status replay.

## Migration Plan

No stored runtime migration is required. This change adds new routes and a new adapter package without changing existing gateway routes or persisted gateway state. Rollback is removing the new dependency, route registration, adapter package, and tests.

## Open Questions

- Should the first long-lived connect stream send periodic SSE comment heartbeats, repeated state snapshots, or no keepalive frames after the initial snapshot?
- Which exact safe fields from `GatewayStatusV1` should be exposed in the namespaced AG-UI state object?
- Should the dependency be declared directly in project runtime dependencies or added only as a Pixi PyPI dependency until the protocol package stabilizes?

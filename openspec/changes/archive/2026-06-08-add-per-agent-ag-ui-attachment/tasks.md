## 1. Protocol Boundary

- [x] 1.1 Decide and apply the dependency path: use `ag-ui-protocol>=0.1.19,<0.2` if dependency resolution is clean, otherwise add minimal internal protocol models behind the same `houmao.ag_ui` boundary.
- [x] 1.2 Add the `src/houmao/ag_ui/` package with module-level docstrings and public exports scoped to this milestone.
- [x] 1.3 Add `houmao.ag_ui.models` for AG-UI connect input, events used by this milestone, and Houmao capability payload models.
- [x] 1.4 Add `houmao.ag_ui.encoder` that emits `text/event-stream` compatible `data: <camelCase-json>\n\n` frames and omits null optional fields.
- [x] 1.5 Add unit tests for camelCase AG-UI input parsing, including `threadId`, `runId`, `parentRunId`, `forwardedProps`, and optional `lastSeenEventId`.
- [x] 1.6 Add unit tests for SSE frame encoding, content type, camelCase field names, and null-field omission.

## 2. Capabilities and Snapshot State

- [x] 2.1 Add `houmao.ag_ui.capabilities` to build conservative per-agent AG-UI capability responses from the live gateway runtime.
- [x] 2.2 Report HTTP SSE, GUI connect, text input parsing, and state snapshots as enabled.
- [x] 2.3 Report task-run submission, state deltas, frontend tool execution, generated graphics, Open Generative UI, and multimodal input as disabled.
- [x] 2.4 Include Houmao metadata that states GUI lifecycle does not manage the Houmao agent lifecycle.
- [x] 2.5 Add `houmao.ag_ui.state` or equivalent snapshot-building helper that converts `GatewayServiceRuntime.status()` into a namespaced sanitized Houmao state object.
- [x] 2.6 Ensure snapshots omit mailbox message content, memory page content, raw terminal history, credentials, authorization headers, cookies, bearer tokens, raw prompt text, and unmanaged forwarded props.
- [x] 2.7 Add tests for conservative capabilities and disabled run/graphics/tool flags.
- [x] 2.8 Add tests that sanitized snapshots include connection and compact gateway status fields while omitting sensitive state.

## 3. Connection Registry and Attach Stream

- [x] 3.1 Add `houmao.ag_ui.connection` with typed connection records for `connection_id`, `thread_id`, `run_id`, creation time, and detached state.
- [x] 3.2 Implement registry methods for create, get, detach, unknown-detach handling, and active connection listing.
- [x] 3.3 Implement connect stream generation that creates a registry record and emits an initial AG-UI `STATE_SNAPSHOT`.
- [x] 3.4 Keep the connect stream open after the initial snapshot using the selected idle or heartbeat behavior from the design open question.
- [x] 3.5 Accept `lastSeenEventId` without claiming full historical replay support.
- [x] 3.6 Ensure client disconnect detaches only the GUI connection record.
- [x] 3.7 Add unit tests for registry create, explicit detach, unknown detach, client-disconnect detach, and no Houmao lifecycle side effects.

## 4. Per-Agent Gateway Routes

- [x] 4.1 Add a route registration helper under `houmao.ag_ui.routes` or equivalent that accepts the FastAPI app/router and `GatewayServiceRuntime`.
- [x] 4.2 Wire `GET /v1/ag-ui/capabilities` into the live gateway app created by `create_app()`.
- [x] 4.3 Wire `POST /v1/ag-ui/connect` as an AG-UI SSE endpoint backed by the connection registry and snapshot stream.
- [x] 4.4 Wire `DELETE /v1/ag-ui/connections/{connection_id}` as explicit detach-only cleanup.
- [x] 4.5 Wire `POST /v1/ag-ui/runs` as a deterministic unavailable route that does not open a stream or submit work.
- [x] 4.6 Ensure existing gateway routes such as `GET /v1/status` remain registered unchanged.
- [x] 4.7 Add route inventory tests for all AG-UI routes and existing route preservation.
- [x] 4.8 Add route behavior tests for capabilities, connect first frame, explicit disconnect, unknown disconnect, and unavailable runs.

## 5. No-Work and Lifecycle Safety Tests

- [x] 5.1 Add fake runtime or spy helpers that can detect calls to prompt-control submission, queued request creation, stop, abort, interrupt, restart, and shutdown paths.
- [x] 5.2 Test that `POST /v1/ag-ui/connect` does not submit a prompt, create a queued request, or emit `RUN_STARTED`.
- [x] 5.3 Test that HTTP/SSE client disconnect does not stop, abort, interrupt, restart, or shut down the Houmao agent.
- [x] 5.4 Test that `DELETE /v1/ag-ui/connections/{connection_id}` removes only connection bookkeeping.
- [x] 5.5 Test that `POST /v1/ag-ui/runs` returns the deterministic unavailable response and does not submit work or emit `RUN_STARTED`.

## 6. Verification

- [x] 6.1 Run focused unit tests for `houmao.ag_ui` models, encoder, capabilities, state snapshot, connection registry, and routes.
- [x] 6.2 Run `pixi run test` and fix regressions relevant to this change.
- [x] 6.3 Run `pixi run lint` and fix lint failures introduced by this change.
- [x] 6.4 Run `pixi run typecheck` and fix type errors introduced by this change.
- [x] 6.5 Run `openspec status --change add-per-agent-ag-ui-attachment` and confirm all required artifacts are present.
- [x] 6.6 Run `openspec validate add-per-agent-ag-ui-attachment --type change --strict` and fix validation issues.

## Context

Milestone 1 added the `houmao.ag_ui` package and live per-agent gateway routes under `/v1/ag-ui`. The current route set exposes capabilities, connect, explicit disconnect, and a `/runs` shell that returns a deterministic unavailable response. That boundary already uses `ag-ui-protocol>=0.1.19,<0.2`, the local AG-UI SSE encoder, and sanitized Houmao state snapshots.

Milestone 2 turns the per-agent gateway into a usable AG-UI run endpoint. The GUI still attaches to one existing Houmao agent. Houmao remains the lifecycle owner, and AG-UI run lifecycle events describe one submitted task, not the lifetime of the managed agent process.

The existing gateway already has the correct admission surface for this work:

- `GatewayServiceRuntime.create_request()` validates availability, busy state, execution overrides, and queue admission.
- `GatewayRequestPayloadSubmitPromptV1` carries a prompt, optional `turn_id`, optional `chat_session`, and optional execution override.
- Headless adapters already pass `turn_id` to the headless runner as `turn_artifact_dir_name`.
- Headless bridge code writes canonical provider-normalized events to a per-turn artifact while the provider stream is consumed.
- TUI gateways expose status and tracked terminal state, but not headless-level semantic tool events.

CopilotKit renders backend-generated UI through streamed AG-UI tool calls. The MVP graphics path should emit a tool call named `houmao_render_graphic` with typed JSON arguments, not unstructured Markdown or open-ended JavaScript.

## Goals / Non-Goals

**Goals:**

- Make `POST /v1/ag-ui/runs` accept AG-UI `RunAgentInput` and return `text/event-stream`.
- Admit runs through existing gateway controls and reject invalid, busy, or unavailable targets before `RUN_STARTED`.
- Convert AG-UI input into a deterministic Houmao prompt with structured context.
- Stream exactly one terminal AG-UI run event after admission: `RUN_FINISHED` or `RUN_ERROR`.
- Map headless canonical events to AG-UI text, reasoning, tool, activity, and terminal lifecycle events.
- Map TUI targets to a compatible lower-fidelity stream without claiming headless-level tool semantics.
- Validate explicit graphics artifacts and emit a CopilotKit-compatible `houmao_render_graphic` tool-call sequence.
- Update capability discovery to reflect enabled run submission and graphics support while preserving conservative unsupported flags.

**Non-Goals:**

- Do not add passive-server AG-UI proxy routes in this change.
- Do not let the GUI start, stop, restart, interrupt, abort, or shut down the Houmao agent by default.
- Do not add frontend tool execution or AG-UI interrupt/resume tool execution.
- Do not enable Open Generative UI or generated JavaScript.
- Do not expose mailbox content, memory content, raw terminal history, credentials, raw prompt text, or unmanaged forwarded props through AG-UI state.
- Do not add a second scheduler or bypass the gateway request queue.

## Decisions

### Use Gateway Request Admission for AG-UI Runs

`houmao.ag_ui.service` should submit runs through `GatewayServiceRuntime.create_request()` using `GatewayRequestCreateV1(kind="submit_prompt", payload=GatewayRequestPayloadSubmitPromptV1(...))`.

Rationale: this keeps AG-UI admission aligned with existing busy, unavailable, queue, headless active-turn, and execution override rules. It also avoids a parallel task path that could drift from gateway semantics.

Alternative considered: call `control_prompt()` directly from `/v1/ag-ui/runs`. That path dispatches immediately and is useful for operator control, but it does not give AG-UI the same durable request state boundary as the queue.

### Use AG-UI `runId` as Houmao `turn_id`

The AG-UI run service should pass `RunAgentInput.run_id` as `GatewayRequestPayloadSubmitPromptV1.turn_id`.

Rationale: native headless adapters already use `turn_id` as the artifact directory name. Reusing `runId` gives the mapper a stable join key for canonical headless artifacts and makes tests deterministic.

Alternative considered: generate an internal gateway turn id and map it to AG-UI `runId` in a side registry. That adds bookkeeping without benefit for the first per-agent milestone.

### Add a Narrow Runtime Observation Protocol

The AG-UI service should depend on a small protocol implemented by `GatewayServiceRuntime`, not private attributes. The protocol should expose:

- current status
- request admission through `create_request`
- observed request state for one request id
- target backend or transport family
- headless artifact location for a known AG-UI `runId` when available
- TUI tracked state or terminal summary when available

Rationale: tests can fake this protocol, and AG-UI code stays separate from gateway storage internals.

Alternative considered: let `houmao.ag_ui` read the gateway SQLite queue and artifact paths directly. That would couple the adapter to private storage layout and make future passive-server proxying harder.

### Start With Streamed Headless Artifacts, Degrade TUI Output

For headless backends, the mapper should read canonical headless events from the `runId` turn artifact. If the artifact exists while the request is running, the stream may tail new canonical event lines. If no live artifact is available yet, the service should still emit activity/status events and replay the canonical events after completion.

For TUI backends, the service should emit state and activity updates plus final text from the tracked terminal surface or dialog tail when available. It must not invent tool-call events from terminal text.

Rationale: headless canonical events are the high-fidelity semantic source. TUI state is observable but not equivalent.

Alternative considered: require live tailing for every backend before making `/runs` available. That would block the useful headless path on lower-fidelity TUI work.

### Treat Graphics as Explicit Structured Artifacts

`houmao.ag_ui.graphics` should accept only typed `HoumaoGraphicArtifact` payloads. The first recognized source should be an explicit canonical action/tool event whose name is `houmao_render_graphic` and whose arguments or result contain the artifact payload.

Rationale: explicit artifacts are testable and enforce validation. Markdown scraping would be fragile and could expose unsafe inline content.

Alternative considered: parse graphics out of assistant Markdown or file links. That can come later if users need it, but it should not define the first protocol contract.

### Attach Graphics Tool Calls to an Assistant Message

The graphics mapper should emit `TEXT_MESSAGE_START` before a `houmao_render_graphic` tool call when no assistant message is currently open. It should set `parentMessageId` on `TOOL_CALL_START`, then emit `TOOL_CALL_ARGS`, `TOOL_CALL_END`, and an optional `TOOL_CALL_RESULT`.

Rationale: CopilotKit reconstructs backend tool calls from assistant messages with `toolCalls`. Stable parent message IDs make renderers such as `useRenderTool({ name: "houmao_render_graphic" })` see the graphic inline.

Alternative considered: emit graphics as `CUSTOM` or `ACTIVITY_SNAPSHOT`. That might be visible to a generic AG-UI collector, but it does not satisfy CopilotKit's standard tool-rendering path.

### Disconnect Detaches From Streaming Only

If an HTTP client disconnects from `/runs`, the server should stop writing to that response and clean up AG-UI stream bookkeeping. It should not interrupt the underlying Houmao request unless a future explicit abort policy opts in.

Rationale: CopilotKit stop and browser disconnect are GUI subscription events by default. Interrupting the managed agent changes work ownership and must remain explicit.

Alternative considered: map stream disconnect to gateway interrupt. That conflicts with the lifecycle boundary established in Milestone 1.

## Risks / Trade-offs

- **Headless artifact path is not available for every gateway mode**: Add a runtime observation method that returns `None` for unsupported targets and fall back to status/activity streaming.
- **Live tailing canonical events can race with artifact creation**: Poll for artifact presence until request terminal state, deduplicate by file offset or event identity, then replay remaining events after completion.
- **Queued request coalescing could affect AG-UI stream expectations**: Reject overlapping AG-UI runs before admission when the target is not idle, and surface pre-admission conflicts as HTTP errors.
- **Post-admission failures can occur after `RUN_STARTED`**: Catch stream-side runtime errors and emit `RUN_ERROR` as the terminal event.
- **Reasoning content can expose unsafe internals**: Default to redaction unless a policy explicitly allows visible reasoning events for the backend.
- **SVG and HTML fragments can contain unsafe content**: Validate formats and reject scripts, event handler attributes, unsafe URLs, and unsupported MIME types before emission.
- **TUI streams are lower fidelity**: Make capabilities and emitted custom metadata clear that TUI output is status and final-text oriented, not semantic tool streaming.

## Migration Plan

This is a forward-only change in an unstable development repository. Existing `/v1/ag-ui/connect`, explicit disconnect, SSE encoding, and state snapshot behavior remain compatible. `/v1/ag-ui/runs` changes from deterministic `501` to a streaming endpoint for valid requests; clients that used the old unavailable response should already have read capabilities first.

Implementation can ship behind capability flags during development:

1. Add prompt conversion and mapper tests with no route behavior change.
2. Add the run service and fake-runtime route tests.
3. Replace the `/runs` route shell with the run stream once pre-admission errors and terminal events are covered.
4. Flip capability fields for run submission and graphics only when the route and mapper paths are complete.

Rollback is reverting the `/runs` route to the existing unavailable response and setting `taskRunSubmission` and `generatedGraphics` to false.

## Open Questions

- Should Milestone 2 require live tailing of canonical headless events, or is replay-after-completion acceptable for the first implementation?
- Which exact forwarded props should be allowed in the initial whitelist beyond `chatSession` and `execution.model`?
- Should graphics support be reported globally for all targets or only when the target backend can emit explicit `houmao_render_graphic` artifacts?

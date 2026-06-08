## 1. Runtime Observation Boundary

- [x] 1.1 Add AG-UI runtime observation protocols and data models for request state, target transport family, headless artifact lookup, and TUI observation.
- [x] 1.2 Implement `GatewayServiceRuntime` helpers for admitted request lookup without exposing private SQLite details to `houmao.ag_ui`.
- [x] 1.3 Implement headless artifact location lookup using AG-UI `runId` as the gateway `turn_id`.
- [x] 1.4 Implement TUI observation access for gateway status, activity state, and final text candidates where available.
- [x] 1.5 Add focused tests for runtime observation helpers, including unavailable artifact and unavailable TUI cases.

## 2. Prompt Conversion and Admission

- [x] 2.1 Add `houmao.ag_ui.prompt` to convert `RunAgentInput` messages, state, context, forwarded props, and resume data into a deterministic Houmao prompt.
- [x] 2.2 Select the latest user message or tool result as the primary prompt body and render prior messages as structured context.
- [x] 2.3 Add forwarded-prop whitelist handling for initial execution settings, including headless chat-session selection and execution model overrides if allowed.
- [x] 2.4 Reject unsupported multimodal input before gateway request admission.
- [x] 2.5 Add prompt conversion tests for message ordering, structured context, tool results, forwarded-prop filtering, resume data, and multimodal rejection.
- [x] 2.6 Add `houmao.ag_ui.service` admission logic that builds `GatewayRequestCreateV1` with `turn_id` equal to AG-UI `runId`.
- [x] 2.7 Add service tests for invalid input, busy agent, unavailable target, admitted request metadata, and no prompt submission on pre-admission failure.

## 3. AG-UI Event Mapping

- [x] 3.1 Add `houmao.ag_ui.mapper` for deterministic AG-UI message ids, tool-call ids, and lifecycle event construction.
- [x] 3.2 Map canonical headless assistant events to `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, and `TEXT_MESSAGE_END`.
- [x] 3.3 Map canonical headless action requests and action results to AG-UI tool-call start, args, end, and result events.
- [x] 3.4 Add reasoning visibility policy with default redaction for readable reasoning content.
- [x] 3.5 Map canonical progress and diagnostic events to `ACTIVITY_SNAPSHOT` or `CUSTOM` with Houmao metadata.
- [x] 3.6 Add TUI lower-fidelity mapping for state/activity updates and parsed final text without inventing tool-call events.
- [x] 3.7 Add mapper tests for headless text, tool calls, tool results, reasoning redaction, progress, diagnostics, TUI status, and TUI final text.

## 4. CopilotKit Graphics

- [x] 4.1 Add `houmao.ag_ui.graphics` with a typed `HoumaoGraphicArtifact` schema.
- [x] 4.2 Implement validators for `svg`, `html_fragment`, `image_url`, `image_data_uri`, and `chart_json`.
- [x] 4.3 Reject unsupported formats, scripts, event handler attributes, unsafe URLs, unsafe data URIs, and malformed chart JSON before emission.
- [x] 4.4 Recognize explicit structured `houmao_render_graphic` artifacts from canonical headless action or result event payloads.
- [x] 4.5 Emit validated graphics as `houmao_render_graphic` tool-call sequences attached to an assistant message.
- [x] 4.6 Add graphics tests for valid formats, unsafe payload rejection, exact tool-call event sequence, assistant parent message attachment, and optional result emission.
- [x] 4.7 Add a small CopilotKit renderer fixture or example that registers `useRenderTool({ name: "houmao_render_graphic" })`.

## 5. Run Streaming Routes and Capabilities

- [x] 5.1 Replace the `/v1/ag-ui/runs` unavailable route with an async SSE route backed by `houmao.ag_ui.service`.
- [x] 5.2 Emit `RUN_STARTED` only after gateway request admission succeeds.
- [x] 5.3 Stream mapped headless canonical events by tailing available canonical artifacts and replaying remaining events after request completion.
- [x] 5.4 Stream lower-fidelity TUI state/activity and final text events for TUI targets.
- [x] 5.5 Convert post-admission runtime failures into terminal `RUN_ERROR` events instead of unhandled stream exceptions.
- [x] 5.6 Clean up AG-UI run stream bookkeeping on HTTP client disconnect without calling Houmao stop, abort, interrupt, restart, or shutdown paths.
- [x] 5.7 Update `GET /v1/ag-ui/capabilities` so task-run submission and generated graphics are enabled only when supported and unsupported features remain disabled.
- [x] 5.8 Add route tests for success, invalid input, busy response, unavailable response, post-admission failure, client disconnect, capabilities, and content type.

## 6. Verification

- [x] 6.1 Run `pixi run pytest tests/unit/ag_ui -q`.
- [x] 6.2 Run focused gateway route tests that cover AG-UI registration and `/v1/ag-ui/runs`.
- [x] 6.3 Run `pixi run ruff check src/houmao/ag_ui tests/unit/ag_ui src/houmao/agents/realm_controller/gateway_service.py`.
- [x] 6.4 Run targeted mypy for `src/houmao/ag_ui` and any gateway runtime files touched by this change.
- [x] 6.5 Run `openspec validate add-ag-ui-run-streaming-graphics --strict`.

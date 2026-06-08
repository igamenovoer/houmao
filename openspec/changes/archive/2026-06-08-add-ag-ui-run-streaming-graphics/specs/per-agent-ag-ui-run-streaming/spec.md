## ADDED Requirements

### Requirement: Per-agent AG-UI runs stream task lifecycle events

`POST /v1/ag-ui/runs` SHALL accept AG-UI `RunAgentInput` JSON for the live per-agent gateway and return an AG-UI `text/event-stream` response after the run is admitted.

An admitted run stream SHALL emit `RUN_STARTED` before mapped task output.

An admitted run stream SHALL terminate with exactly one terminal AG-UI run event: `RUN_FINISHED` for success or `RUN_ERROR` for failure.

`RUN_STARTED`, `RUN_FINISHED`, and `RUN_ERROR` SHALL describe the submitted AG-UI task run, not the lifetime of the Houmao agent process.

#### Scenario: Successful run emits lifecycle and text events

- **WHEN** a caller posts valid AG-UI run input with one user text message to `POST /v1/ag-ui/runs`
- **AND WHEN** the target gateway admits and completes the Houmao task successfully
- **THEN** the response content type is `text/event-stream`
- **AND THEN** the stream emits `RUN_STARTED`
- **AND THEN** the stream emits mapped assistant text events when assistant output is available
- **AND THEN** the stream emits exactly one `RUN_FINISHED`
- **AND THEN** the stream does not emit `RUN_ERROR`

#### Scenario: Run lifecycle uses AG-UI thread and run ids

- **WHEN** a caller posts valid AG-UI run input with `threadId`, `runId`, and `parentRunId`
- **THEN** `RUN_STARTED` includes the caller-provided thread id, run id, and parent run id
- **AND THEN** the terminal run event includes the same thread id and run id

### Requirement: Run admission follows existing gateway controls

AG-UI run submission SHALL use the existing per-agent gateway admission controls instead of bypassing or duplicating Houmao request scheduling.

The run service SHALL reject invalid input, unavailable transports, and busy agents before emitting `RUN_STARTED`.

The run service SHALL pass the AG-UI `runId` as the gateway prompt `turn_id` so headless artifacts have a stable run-specific location.

The run service SHALL reject overlapping AG-UI runs for the same target unless a later change explicitly adds queued AG-UI stream semantics.

#### Scenario: Invalid input is rejected before streaming

- **WHEN** a caller posts malformed AG-UI input to `POST /v1/ag-ui/runs`
- **THEN** the gateway returns an HTTP validation error before any SSE frame is emitted
- **AND THEN** no prompt is submitted
- **AND THEN** no `RUN_STARTED` event is emitted

#### Scenario: Busy agent is rejected before streaming

- **WHEN** the target gateway reports active work or a non-empty admitted queue
- **AND WHEN** a caller posts otherwise valid AG-UI run input
- **THEN** the gateway returns a deterministic busy response before any SSE frame is emitted
- **AND THEN** no prompt is submitted for that AG-UI run

#### Scenario: Unavailable transport is rejected before streaming

- **WHEN** the target gateway transport is unavailable or cannot admit prompt work
- **AND WHEN** a caller posts otherwise valid AG-UI run input
- **THEN** the gateway returns a deterministic unavailable response before any SSE frame is emitted
- **AND THEN** no prompt is submitted for that AG-UI run

#### Scenario: AG-UI run id becomes gateway turn id

- **WHEN** a caller posts valid AG-UI run input with `runId` equal to `run-alpha`
- **AND WHEN** the gateway admits the run
- **THEN** the submitted gateway prompt payload uses `turn_id` equal to `run-alpha`

### Requirement: Prompt conversion is deterministic and bounded

The AG-UI adapter SHALL convert `RunAgentInput` into one Houmao prompt.

The converted prompt SHALL use the latest user message or tool result as the primary task body.

The converted prompt SHALL include prior AG-UI messages, state, context, forwarded props, and resume data as structured context when those fields are present.

The adapter SHALL ignore AG-UI activity messages as agent input.

The adapter SHALL pass only whitelisted forwarded props to Houmao execution controls and SHALL render all other forwarded props as inert prompt context or omit them.

Unsupported multimodal content SHALL fail with a clear validation error before admission unless the target backend explicitly supports that input type.

#### Scenario: Prompt conversion includes structured context

- **WHEN** a `RunAgentInput` contains prior messages, a current user message, state, context entries, forwarded props, and resume data
- **THEN** the generated Houmao prompt uses the current user message as the primary task body
- **AND THEN** the prompt includes prior messages as structured conversation context
- **AND THEN** the prompt includes state, context, forwarded props, and resume data in clearly labeled structured sections

#### Scenario: Tool result can be the primary prompt body

- **WHEN** the latest actionable AG-UI message is a tool result message
- **THEN** the generated Houmao prompt uses that tool result as the primary task body
- **AND THEN** prior messages remain available as structured context

#### Scenario: Forwarded props are whitelisted

- **WHEN** a `RunAgentInput` contains allowed and disallowed forwarded props
- **THEN** only allowed forwarded props reach Houmao execution controls
- **AND THEN** disallowed forwarded props do not change gateway runtime controls

#### Scenario: Unsupported multimodal input is rejected

- **WHEN** a `RunAgentInput` contains image, audio, video, document, or binary content for a target that does not support that modality
- **THEN** the gateway returns a clear validation error before admission
- **AND THEN** the adapter does not silently drop the multimodal content

### Requirement: Headless canonical events map to AG-UI events

For headless gateway targets, the AG-UI mapper SHALL map Houmao canonical headless events into AG-UI events.

Assistant output SHALL map to `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, and `TEXT_MESSAGE_END`.

Visible reasoning SHALL map to AG-UI reasoning events only when policy allows it; otherwise reasoning content SHALL be redacted or omitted.

Action requests SHALL map to `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`.

Action results SHALL map to `TOOL_CALL_RESULT`.

Progress and diagnostics SHALL map to `ACTIVITY_SNAPSHOT` or `CUSTOM`.

#### Scenario: Assistant event maps to text sequence

- **WHEN** the mapper receives a canonical headless assistant event with text
- **THEN** it emits `TEXT_MESSAGE_START`
- **AND THEN** it emits `TEXT_MESSAGE_CONTENT` with the assistant text
- **AND THEN** it emits `TEXT_MESSAGE_END`
- **AND THEN** all three text events share the same message id

#### Scenario: Tool call events map to AG-UI tool sequence

- **WHEN** the mapper receives a canonical action request and matching action result
- **THEN** it emits `TOOL_CALL_START`
- **AND THEN** it emits `TOOL_CALL_ARGS`
- **AND THEN** it emits `TOOL_CALL_END`
- **AND THEN** it emits `TOOL_CALL_RESULT`
- **AND THEN** the tool call id is stable across all tool-call events

#### Scenario: Reasoning is redacted when policy disallows it

- **WHEN** the mapper receives a canonical reasoning event
- **AND WHEN** reasoning visibility policy disallows surfacing reasoning content
- **THEN** the mapper does not emit readable reasoning content

#### Scenario: Progress maps to activity or custom events

- **WHEN** the mapper receives a canonical progress or diagnostic event
- **THEN** it emits `ACTIVITY_SNAPSHOT` or `CUSTOM`
- **AND THEN** the emitted payload identifies the event as Houmao gateway activity

### Requirement: TUI targets stream lower-fidelity AG-UI output

For TUI gateway targets, the AG-UI run stream SHALL remain protocol-compatible while reflecting the lower-fidelity observation source.

The TUI stream SHALL emit `RUN_STARTED` after admission.

The TUI stream SHALL emit a sanitized `STATE_SNAPSHOT` or activity event with current gateway and TUI status.

The TUI stream SHALL emit final assistant text when a parsed terminal surface or dialog tail is available.

The TUI stream SHALL NOT claim headless-level tool-call semantics from raw terminal text.

#### Scenario: TUI output maps to status and final text

- **WHEN** an AG-UI run is admitted for a TUI gateway target
- **THEN** the stream emits `RUN_STARTED`
- **AND THEN** the stream emits state or activity events describing gateway and TUI status
- **AND THEN** the stream emits final assistant text when parsed final text is available
- **AND THEN** the stream emits `RUN_FINISHED` or `RUN_ERROR`

#### Scenario: TUI stream does not invent tool calls

- **WHEN** a TUI terminal surface contains text that resembles a tool call
- **THEN** the AG-UI mapper does not emit `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, or `TOOL_CALL_RESULT` unless a structured Houmao event exists

### Requirement: Post-admission errors and disconnects preserve lifecycle boundaries

After `RUN_STARTED` has been emitted, runtime failures SHALL be reported through `RUN_ERROR` rather than an unhandled HTTP stream failure.

Closing the AG-UI run stream SHALL detach that GUI stream only.

Closing the AG-UI run stream SHALL NOT stop, abort, interrupt, restart, shut down, or otherwise manage the Houmao agent or its active task unless a future explicit abort policy opts in.

#### Scenario: Runtime failure becomes run error after admission

- **WHEN** the gateway admits an AG-UI run and emits `RUN_STARTED`
- **AND WHEN** the underlying Houmao task fails after admission
- **THEN** the stream emits `RUN_ERROR`
- **AND THEN** the stream does not fail with an unhandled server exception

#### Scenario: Client disconnect detaches the stream only

- **WHEN** a caller opens an AG-UI run stream
- **AND WHEN** the caller closes the HTTP/SSE connection while the Houmao task remains active
- **THEN** the gateway stops writing to that client stream
- **AND THEN** AG-UI stream bookkeeping is cleaned up
- **AND THEN** the gateway does not call any Houmao stop, abort, interrupt, restart, or shutdown path

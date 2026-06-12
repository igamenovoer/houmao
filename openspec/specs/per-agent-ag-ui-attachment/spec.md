# per-agent-ag-ui-attachment Specification

## Purpose
TBD - created by archiving change add-per-agent-ag-ui-attachment. Update Purpose after archive.
## Requirements
### Requirement: Per-agent gateway exposes an AG-UI attachment namespace

The live per-agent gateway SHALL expose AG-UI routes under `/v1/ag-ui` without changing existing Houmao gateway routes.

The gateway SHALL expose:

- `GET /v1/ag-ui/capabilities`
- `POST /v1/ag-ui/connect`
- `POST /v1/ag-ui/runs`
- `DELETE /v1/ag-ui/connections/{connection_id}`

The AG-UI namespace SHALL be served by the same live per-agent gateway runtime that serves `/v1/status` for the target agent.

#### Scenario: AG-UI routes are registered on the per-agent gateway

- **WHEN** the per-agent gateway FastAPI app is created
- **THEN** the app route inventory includes `GET /v1/ag-ui/capabilities`
- **AND THEN** the app route inventory includes `POST /v1/ag-ui/connect`
- **AND THEN** the app route inventory includes `POST /v1/ag-ui/runs`
- **AND THEN** the app route inventory includes `DELETE /v1/ag-ui/connections/{connection_id}`

#### Scenario: Existing gateway routes remain available

- **WHEN** the per-agent gateway FastAPI app is created with AG-UI routes enabled
- **THEN** existing routes such as `GET /v1/status` remain registered
- **AND THEN** AG-UI route registration does not replace or rename existing Houmao gateway routes

### Requirement: AG-UI capabilities report conservative attachment support

The gateway SHALL provide `GET /v1/ag-ui/capabilities` so GUI clients can discover supported AG-UI behavior before connecting or starting a run.

The capabilities response SHALL report HTTP SSE support, GUI connect support, text input parsing support, state snapshot support, and task-run submission as enabled when AG-UI run streaming is implemented for the live per-agent gateway.

The capabilities response SHALL report generated graphics support as enabled only when `houmao_render_graphic` artifact validation and event mapping are available for the target.

The capabilities response SHALL report resumable transport support as disabled for Houmao-published GUI events because the gateway does not replay retained `/v1/ag-ui/events` batches.

The capabilities response SHALL report state delta support, frontend tool execution, Open Generative UI, and unsupported multimodal input as disabled for this milestone.

The capabilities response SHALL identify that GUI lifecycle does not manage the Houmao agent lifecycle.

The Houmao metadata SHALL identify published-event delivery as live-only fanout with client-owned caching responsibility.

#### Scenario: Capabilities report run streaming support

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities` after AG-UI run streaming is enabled
- **THEN** the response reports HTTP SSE support as enabled
- **AND THEN** the response reports GUI connect support as enabled
- **AND THEN** the response reports state snapshot support as enabled
- **AND THEN** the response reports task-run submission as enabled
- **AND THEN** the response reports text input parsing as enabled

#### Scenario: Capabilities report graphics support when enabled

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities` for a gateway target with `houmao_render_graphic` mapping enabled
- **THEN** the response reports generated graphics as enabled
- **AND THEN** the response identifies `houmao_render_graphic` in Houmao metadata or tool capability metadata

#### Scenario: Capabilities report published-event delivery as non-resumable

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response reports resumable transport support as disabled for Houmao-published GUI events
- **AND THEN** Houmao metadata identifies `/v1/ag-ui/events` delivery as live-only fanout without gateway replay

#### Scenario: Capabilities remain conservative for unsupported features

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response reports state delta support as disabled
- **AND THEN** the response reports frontend tool execution as disabled
- **AND THEN** the response reports Open Generative UI as disabled
- **AND THEN** the response reports unsupported multimodal input as disabled

#### Scenario: Capabilities state that GUI does not own agent lifecycle

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response contains Houmao metadata indicating that the GUI does not manage the agent lifecycle

### Requirement: AG-UI request parsing and SSE encoding follow the protocol wire shape

The AG-UI adapter SHALL accept AG-UI camelCase request fields for connect input, including `threadId`, `runId`, `parentRunId`, and `forwardedProps`.

The AG-UI SSE encoder SHALL emit text/event-stream frames in the form `data: <json>\n\n`.

Encoded event JSON SHALL use camelCase field names and SHALL omit null optional fields.

#### Scenario: Connect input accepts camelCase AG-UI fields

- **WHEN** a caller submits AG-UI connect input containing `threadId`, `runId`, `parentRunId`, and `forwardedProps`
- **THEN** the gateway parses the request successfully
- **AND THEN** the parsed values preserve the caller-provided thread, run, parent-run, and forwarded-props values

#### Scenario: SSE encoder emits AG-UI JSON frames

- **WHEN** the gateway encodes an AG-UI state snapshot event
- **THEN** the encoded bytes start with `data: `
- **AND THEN** the encoded bytes end with a double newline
- **AND THEN** the event JSON uses camelCase field names
- **AND THEN** optional null fields are absent from the event JSON

### Requirement: Connect attaches a GUI stream without submitting work

`POST /v1/ag-ui/connect` SHALL create a GUI attachment connection for the existing Houmao agent and return an AG-UI SSE stream.

The connect stream SHALL emit an initial AG-UI `STATE_SNAPSHOT` describing sanitized current Houmao gateway status for that agent.

The connect handler SHALL NOT submit a prompt, create a gateway request, start a task run, stop the agent, interrupt the agent, restart the agent, or shut down the agent.

The connect handler MAY accept an optional `lastSeenEventId` field for request compatibility, but SHALL NOT treat it as a replay cursor for Houmao-published GUI events. The connect stream SHALL emit the current sanitized state snapshot and continue with future live events.

#### Scenario: Connect emits a state snapshot

- **WHEN** a caller posts valid AG-UI connect input to `POST /v1/ag-ui/connect`
- **THEN** the response content type is `text/event-stream`
- **AND THEN** the first AG-UI data event is a `STATE_SNAPSHOT`
- **AND THEN** the snapshot identifies the Houmao connection and current gateway status using a namespaced Houmao state object

#### Scenario: Connect does not submit prompt work

- **WHEN** a caller posts valid AG-UI connect input to `POST /v1/ag-ui/connect`
- **THEN** the gateway does not call prompt-control submission
- **AND THEN** the gateway does not create a queued gateway request
- **AND THEN** the gateway does not emit `RUN_STARTED`

#### Scenario: Connect does not replay after cursor

- **WHEN** a caller posts valid AG-UI connect input with `lastSeenEventId`
- **THEN** the connect stream emits the current sanitized state snapshot
- **AND THEN** it does not replay retained published AG-UI events after that cursor
- **AND THEN** it continues streaming future live matching events

#### Scenario: Connect remains usable when cursor cannot be honored

- **WHEN** a caller posts valid AG-UI connect input with an expired, unknown, malformed, or mismatched `lastSeenEventId`
- **THEN** the gateway emits at least the current sanitized state snapshot
- **AND THEN** the stream remains usable for later live events
- **AND THEN** the gateway does not claim complete replay for the missing range

### Requirement: AG-UI state snapshots expose only safe Houmao status

The AG-UI `STATE_SNAPSHOT` payload SHALL put Houmao-specific state under a namespaced Houmao object.

The snapshot SHALL include only safe observation fields needed by a GUI attachment, such as connection id, thread id, run id, gateway availability, target transport family, and a compact active-execution summary.

The snapshot SHALL NOT include mailbox message content, memory page content, raw terminal history, credentials, authorization headers, cookies, bearer tokens, raw prompt text, or unmanaged forwarded props.

#### Scenario: Snapshot contains namespaced Houmao status

- **WHEN** a connect stream emits its initial `STATE_SNAPSHOT`
- **THEN** the snapshot contains a namespaced Houmao object
- **AND THEN** the namespaced object contains the AG-UI connection id
- **AND THEN** the namespaced object contains a compact gateway status summary

#### Scenario: Snapshot omits sensitive state

- **WHEN** the gateway status source contains memory, mailbox, terminal, credential, or prompt-adjacent data
- **THEN** the AG-UI snapshot omits mailbox message content
- **AND THEN** the AG-UI snapshot omits memory page content
- **AND THEN** the AG-UI snapshot omits raw terminal history
- **AND THEN** the AG-UI snapshot omits credential and authorization material
- **AND THEN** the AG-UI snapshot omits raw prompt text

### Requirement: Disconnect detaches GUI bookkeeping only

The gateway SHALL support GUI detachment by both HTTP/SSE client disconnect and `DELETE /v1/ag-ui/connections/{connection_id}`.

Detaching a GUI connection SHALL remove the connection from AG-UI connection bookkeeping.

Detaching a GUI connection SHALL NOT stop, abort, interrupt, restart, shut down, or otherwise manage the Houmao agent or its active work.

#### Scenario: Closing the connect stream detaches only the GUI connection

- **WHEN** a caller opens `POST /v1/ag-ui/connect`
- **AND WHEN** the caller closes the SSE client connection
- **THEN** the AG-UI connection is detached from connection bookkeeping
- **AND THEN** the gateway does not stop, abort, interrupt, restart, or shut down the Houmao agent

#### Scenario: Explicit disconnect removes connection bookkeeping

- **WHEN** a caller has an active AG-UI connection id
- **AND WHEN** the caller sends `DELETE /v1/ag-ui/connections/{connection_id}`
- **THEN** the gateway removes that AG-UI connection from connection bookkeeping
- **AND THEN** the gateway does not stop, abort, interrupt, restart, or shut down the Houmao agent

#### Scenario: Unknown explicit disconnect is deterministic

- **WHEN** a caller sends `DELETE /v1/ag-ui/connections/{connection_id}` for an unknown connection id
- **THEN** the gateway returns a deterministic not-found or already-detached response
- **AND THEN** the gateway does not call any Houmao agent lifecycle control path

### Requirement: Per-agent AG-UI streams expose safe diagnostics
The live per-agent gateway SHALL emit safe diagnostics for AG-UI connect streams and run streams.

At minimum, AG-UI diagnostics SHALL cover connect creation, disconnect or detach, run admission, run stream start, run completion, stream client disconnect, and stream error outcomes.

AG-UI diagnostics SHALL include lifecycle identifiers and operational metadata such as connection id, thread id, run id, gateway request id, target transport family, terminal outcome, active connection count, active run count, duration, status code, and error category when available.

AG-UI diagnostics SHALL NOT include prompt text, full AG-UI message content, mailbox content, memory content, raw terminal history, credentials, authorization headers, or unmanaged forwarded props.

#### Scenario: Run diagnostics record lifecycle without private payloads
- **WHEN** an AG-UI run is admitted through `/v1/ag-ui/runs`
- **THEN** the gateway records safe diagnostics for admission and stream completion
- **AND THEN** the diagnostics include run id, gateway request id, target transport family, terminal outcome, and duration when available
- **AND THEN** the diagnostics do not include the submitted prompt text, AG-UI message bodies, credentials, or unmanaged forwarded props

#### Scenario: Connect diagnostics record attachment without submitting work
- **WHEN** a GUI attaches through `/v1/ag-ui/connect` and later disconnects
- **THEN** the gateway records safe diagnostics for connection creation and detachment
- **AND THEN** the diagnostics include the connection id and active AG-UI connection count
- **AND THEN** the diagnostics do not claim that a Houmao task run was started

### Requirement: Per-agent AG-UI diagnostics report active connection and run counts
The live per-agent gateway SHALL maintain lightweight AG-UI diagnostic counts for active GUI connections and active AG-UI run streams.

The counts SHALL reflect stream bookkeeping rather than the lifetime of the Houmao managed agent. A disconnected GUI stream SHALL decrement the relevant AG-UI count without stopping, restarting, shutting down, or interrupting the managed agent.

#### Scenario: Active counts update across connect and run streams
- **WHEN** one AG-UI connect stream and one AG-UI run stream are active
- **THEN** the gateway diagnostics report one active AG-UI connection and one active AG-UI run
- **AND WHEN** the connect stream and run stream close
- **THEN** the gateway diagnostics return those AG-UI counts to zero
- **AND THEN** the managed agent lifecycle remains unchanged by those stream closures

#### Scenario: Counts recover after stream error
- **WHEN** an AG-UI stream raises a mapping, encoding, or client-send error
- **THEN** the gateway records a stream-error diagnostic
- **AND THEN** the affected active AG-UI stream count is decremented during cleanup
- **AND THEN** unrelated AG-UI streams continue to be counted accurately

### Requirement: Per-agent AG-UI run streams emit deterministic terminal errors after admission
After an AG-UI run has been admitted and `RUN_STARTED` has been emitted, the live per-agent gateway SHALL convert stream mapping, encoding, or runtime-observation failures into a deterministic AG-UI `RUN_ERROR` event when the client is still connected and the stream can still write.

Pre-admission validation and availability failures SHALL remain HTTP errors and SHALL NOT emit `RUN_STARTED`.

Client disconnects SHALL clean up stream bookkeeping and SHALL NOT require a `RUN_ERROR` event because the client has detached from the stream.

#### Scenario: Mapping error after run start becomes RUN_ERROR
- **WHEN** an AG-UI run stream has emitted `RUN_STARTED`
- **AND WHEN** a mapping, encoding, or runtime-observation error occurs while the client is still connected
- **THEN** the stream emits a `RUN_ERROR` event with a stable Houmao error code
- **AND THEN** the gateway records a safe stream-error diagnostic with the error category
- **AND THEN** the stream performs active-run cleanup

#### Scenario: Pre-admission error remains an HTTP error
- **WHEN** an invalid AG-UI input, busy target, or unavailable gateway target is rejected before run admission
- **THEN** the gateway returns the appropriate HTTP error
- **AND THEN** the response does not contain `RUN_STARTED`
- **AND THEN** no active AG-UI run count is left behind

#### Scenario: Client abort detaches without interrupting by default
- **WHEN** an AG-UI client aborts the run stream after admission
- **THEN** the gateway detaches the stream and performs active-run cleanup
- **AND THEN** the gateway does not interrupt the underlying Houmao task unless an explicit abort policy opts into interruption

### Requirement: Per-agent gateway accepts published standard AG-UI event batches
The live per-agent gateway SHALL expose an AG-UI event ingestion route under `/v1/ag-ui` for callers that already have standard AG-UI events.

The ingestion route SHALL accept a bounded batch of AG-UI event JSON objects plus routing metadata needed to attach those events to a thread, run, or GUI connection.

The ingestion route SHALL validate each event against AG-UI core event shapes.

The ingestion route SHALL validate AG-UI event sequencing within the submitted batch when sequencing is locally checkable, including tool-call args and end events referencing a started tool call.

The ingestion route SHALL NOT validate Houmao component schemas, chart data semantics, table semantics, or dashboard layout semantics.

The ingestion route SHALL NOT submit a Houmao prompt, create a gateway request, stop, interrupt, restart, or otherwise manage the Houmao agent lifecycle.

#### Scenario: Valid standard AG-UI events are accepted
- **WHEN** a caller submits a bounded event batch containing valid AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` events
- **THEN** the gateway accepts the batch
- **AND THEN** the gateway records the accepted event count
- **AND THEN** no Houmao prompt request is created

#### Scenario: Gateway treats component names as opaque strings
- **WHEN** a caller submits a valid AG-UI tool-call sequence whose `toolCallName` is `houmao.graphic.template`
- **THEN** the gateway validates the AG-UI event envelope and sequence
- **AND THEN** it does not inspect or validate the chart payload against the `houmao.graphic.template` schema

#### Scenario: Malformed AG-UI event is rejected
- **WHEN** a caller submits `TOOL_CALL_ARGS` without a `toolCallId`
- **THEN** the gateway rejects the batch with a validation error
- **AND THEN** the gateway does not broadcast any event from that batch

### Requirement: Published AG-UI events are broadcast to matching streams
The gateway SHALL broadcast accepted published AG-UI events to active AG-UI connect or run streams whose routing metadata matches the submitted batch.

The gateway SHALL preserve the submitted AG-UI event payloads except for safe metadata needed for diagnostics or stream framing.

The gateway SHALL expose deterministic behavior when no matching stream is connected.

The gateway SHALL keep published-event stream bookkeeping separate from the Houmao task-run lifecycle.

The gateway SHALL NOT store accepted published events for delivery to future streams.

#### Scenario: Connected GUI receives published events
- **WHEN** a GUI has an active AG-UI connect stream for a thread
- **AND WHEN** a caller publishes a valid AG-UI event batch for that thread
- **THEN** the connect stream emits the accepted events in submission order

#### Scenario: No active GUI loses accepted live-only events
- **WHEN** no GUI stream matches the submitted routing metadata
- **AND WHEN** a caller publishes a valid AG-UI event batch
- **THEN** the gateway responds deterministically with accepted-but-not-delivered or an explicit no-subscriber status
- **AND THEN** the response reports no stored replay events
- **AND THEN** the response does not imply that a Houmao task run was started

### Requirement: Published AG-UI events use live-only fanout and safe diagnostics
The gateway SHALL treat accepted `/v1/ag-ui/events` batches as live-only fanout events.

The gateway SHALL NOT retain accepted published events for later gateway replay.

The gateway SHALL bound event count, event size, and total batch size before broadcast.

Gateway diagnostics for published events SHALL include safe operational metadata such as route, status code, event count, thread id, run id, delivery count, and validation error locations.

Gateway diagnostics SHALL NOT include full tool-call argument payloads, message contents, credentials, authorization headers, cookies, or raw request-body dumps by default.

#### Scenario: Accepted events are not retained by the gateway
- **WHEN** a caller publishes a valid AG-UI event batch
- **THEN** the gateway validates and fanouts the accepted events to currently matching streams
- **AND THEN** the gateway does not write those events to retained replay storage

#### Scenario: Oversized event batch is rejected before broadcast
- **WHEN** a caller submits an AG-UI event batch larger than the configured limit
- **THEN** the gateway rejects the batch before broadcasting
- **AND THEN** the diagnostic identifies the limit category without dumping the full payload

#### Scenario: Diagnostics omit raw component payloads
- **WHEN** a published event batch contains a large chart payload
- **THEN** gateway diagnostics record safe counts and routing metadata
- **AND THEN** gateway diagnostics do not record the full chart data

### Requirement: Published AG-UI event streams do not expose gateway replay cursors
The gateway SHALL NOT advertise SSE event ids from `/v1/ag-ui/events` delivery as durable gateway replay cursors.

The gateway MAY include best-effort SSE frame ids for connected streams when useful for client-side diagnostics or local deduplication.

Any best-effort SSE frame id SHALL NOT imply that the gateway can replay missed published events.

The AG-UI event JSON payload SHALL remain a standard AG-UI event object and SHALL NOT require Houmao-specific cursor fields inside the event body.

#### Scenario: Published event frame has no replay promise
- **WHEN** a caller publishes a valid AG-UI event batch for thread `thread-1`
- **AND WHEN** a matching GUI connect stream receives the batch
- **THEN** the stream emits standard AG-UI event JSON payloads
- **AND THEN** any SSE frame id is documented as non-replayable diagnostic metadata

#### Scenario: Reconnect cannot request missed published events
- **WHEN** a GUI reconnects after missing published AG-UI events
- **THEN** the gateway does not use an SSE id to recover those missed published events
- **AND THEN** the stream remains usable for future live events

### Requirement: Published AG-UI event responses distinguish accepted, stored, and delivered counts
The `/v1/ag-ui/events` response SHALL report the number of accepted events, the number of events stored for bounded replay, and the number of live stream deliveries.

For Houmao gateway live-only published GUI events, the response SHALL report `stored_count = 0`.

When no live stream currently matches a valid event batch, the response SHALL make that state visible with `accepted_count > 0`, `stored_count = 0`, and `delivered_count = 0`.

When a valid event batch reaches matching live streams, the response SHALL report `delivered_count` as the number of live stream deliveries performed at publish time.

The gateway SHALL NOT advertise resumable replay support for Houmao-published GUI events.

#### Scenario: Valid batch has no live subscriber
- **WHEN** no GUI stream matches a valid published AG-UI event batch
- **THEN** the publish response reports the batch as accepted
- **AND THEN** the response reports `stored_count = 0`
- **AND THEN** the response reports `delivered_count = 0`

#### Scenario: Live subscriber receives accepted batch
- **WHEN** a GUI stream matches a valid published AG-UI event batch
- **THEN** the publish response reports the batch as accepted
- **AND THEN** the response reports `stored_count = 0`
- **AND THEN** the matching stream receives the accepted events

### Requirement: AG-UI capabilities advertise Layer 2 Vega-Lite support
The live per-agent gateway SHALL include Houmao custom presentation metadata for Layer 2 Vega-Lite graphics when the target supports typed graphics capability metadata.

The metadata SHALL identify `houmao.graphic.vegalite` as a Vega DSL tool name, list supported Vega-Lite major versions, identify `vega-embed` as the workbench renderer, report remote data loading as disabled by default, report inline data support, and report optional Python Altair authoring.

The metadata SHALL keep Layer 1 `templateGraphics` separate from Layer 2 `vegaDsl` and SHALL NOT list Vega-Lite as a Layer 1 template renderer.

#### Scenario: Capabilities include Vega DSL metadata
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes Houmao custom presentation metadata for `vegaDsl`
- **AND THEN** the metadata lists `houmao.graphic.vegalite` as a supported Layer 2 tool name
- **AND THEN** the metadata reports remote data loading as disabled by default

#### Scenario: Layer 1 metadata remains Plotly-only
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response's Layer 1 template graphics metadata lists Plotly as the template renderer
- **AND THEN** it does not list Vega-Lite as a Layer 1 renderer or fallback

### Requirement: AG-UI tool metadata includes Vega-Lite when generated graphics are enabled
When AG-UI tool metadata is advertised for generated graphics, the tools list SHALL include `houmao.graphic.vegalite` with a JSON parameter shape for the Layer 2 envelope.

When generated graphics are not enabled for a target, conservative capabilities SHALL continue to report tools as unsupported even though Houmao custom presentation metadata can describe the available component vocabulary.

#### Scenario: Headless capabilities list Vega-Lite tool metadata
- **WHEN** a caller requests capabilities for a target that reports generated graphics tool metadata
- **THEN** the tools list includes `houmao.graphic.vegalite`
- **AND THEN** the tool metadata identifies the required `schemaVersion`, `library`, `specVersion`, `title`, and `spec` fields

#### Scenario: Conservative target does not advertise callable tools
- **WHEN** a caller requests capabilities for a target that does not report generated graphics support
- **THEN** the standard tools capability remains unsupported
- **AND THEN** the response does not imply frontend tool execution is enabled


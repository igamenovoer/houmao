## ADDED Requirements

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

## MODIFIED Requirements

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
- **THEN** the gateway emits the current sanitized state snapshot
- **AND THEN** it does not replay retained published AG-UI events after that cursor
- **AND THEN** it continues streaming future live matching events

#### Scenario: Connect remains usable when cursor cannot be honored

- **WHEN** a caller posts valid AG-UI connect input with an expired, unknown, malformed, or mismatched `lastSeenEventId`
- **THEN** the gateway emits at least the current sanitized state snapshot
- **AND THEN** the stream remains usable for later live events
- **AND THEN** the gateway does not claim complete replay for any missing range

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

## REMOVED Requirements

### Requirement: Published AG-UI events use bounded replay and safe diagnostics
**Reason**: Houmao gateway publish is now live-only fanout. Bounded replay belongs to the GUI client cache for events that the GUI actually received.

**Migration**: Move event retention and replay for visible graphics to the AG-UI workbench client cache. Keep gateway diagnostics, size limits, and validation, but remove retained-event writes for published GUI events.

#### Scenario: Gateway replay storage is not used
- **WHEN** a caller publishes a valid AG-UI event batch
- **THEN** the gateway does not store the batch for later replay

### Requirement: AG-UI SSE frames carry durable event identifiers for replayable events
**Reason**: Published AG-UI events are no longer replayable from the gateway.

**Migration**: The workbench records local receive order and optional non-durable SSE ids in its client cache. Reconnects do not send those ids as gateway replay cursors.

#### Scenario: Durable replay cursor is unavailable
- **WHEN** a GUI reconnects after a published AG-UI event was missed
- **THEN** the gateway has no durable cursor that can recover the missed event

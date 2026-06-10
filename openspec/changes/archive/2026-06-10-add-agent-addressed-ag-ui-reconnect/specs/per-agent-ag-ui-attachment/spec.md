## MODIFIED Requirements

### Requirement: AG-UI capabilities report conservative attachment support

The gateway SHALL provide `GET /v1/ag-ui/capabilities` so GUI clients can discover supported AG-UI behavior before connecting or starting a run.

The capabilities response SHALL report HTTP SSE support, GUI connect support, text input parsing support, state snapshot support, and task-run submission as enabled when AG-UI run streaming is implemented for the live per-agent gateway.

The capabilities response SHALL report generated graphics support as enabled only when `houmao_render_graphic` artifact validation and event mapping are available for the target.

The capabilities response SHALL report resumable transport support as enabled only when the gateway can accept `lastSeenEventId` and replay retained AG-UI events after that cursor for the requested thread.

The capabilities response SHALL report state delta support, frontend tool execution, Open Generative UI, and unsupported multimodal input as disabled for this milestone.

The capabilities response SHALL identify that GUI lifecycle does not manage the Houmao agent lifecycle.

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

#### Scenario: Capabilities report resumable support only after replay is available

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **AND WHEN** the gateway has bounded retained-event replay available for AG-UI connect streams
- **THEN** the response reports resumable transport support as enabled
- **AND THEN** Houmao metadata identifies replay support as event-log replay since cursor

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

The connect handler SHALL accept an optional `lastSeenEventId` field. When retained replay is available for the requested thread and the cursor is valid, the connect stream SHALL replay retained AG-UI events after that cursor before continuing with live events. When retained replay is unavailable or the cursor cannot be honored, the connect stream SHALL still emit the current sanitized state snapshot and continue with live events without claiming complete historical recovery.

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

#### Scenario: Connect replays retained events after cursor

- **WHEN** a caller posts valid AG-UI connect input with `lastSeenEventId`
- **AND WHEN** the gateway retains events after that cursor for the requested thread
- **THEN** the connect stream emits the current sanitized state snapshot
- **AND THEN** it emits retained AG-UI events after the cursor in event-id order
- **AND THEN** it continues streaming live matching events

#### Scenario: Connect falls back when cursor cannot be honored

- **WHEN** a caller posts valid AG-UI connect input with an expired, unknown, malformed, or mismatched `lastSeenEventId`
- **THEN** the gateway emits at least the current sanitized state snapshot
- **AND THEN** the stream remains usable for later live events
- **AND THEN** the gateway does not claim complete replay for the missing range

## ADDED Requirements

### Requirement: AG-UI SSE frames carry durable event identifiers for replayable events
Replayable AG-UI SSE data frames SHALL include an SSE `id` field that is stable within the gateway's retained event log.

The event id SHALL identify the agent, thread, and monotonically ordered event position or an equivalent stable cursor that lets a later `lastSeenEventId` request resume after a known event.

The AG-UI event JSON payload SHALL remain a standard AG-UI event object and SHALL NOT require Houmao-specific cursor fields inside the event body.

#### Scenario: Published event frame includes SSE id
- **WHEN** a caller publishes a valid AG-UI event batch for thread `thread-1`
- **AND WHEN** a matching GUI connect stream receives the batch
- **THEN** each replayable SSE data frame includes an `id` field
- **AND THEN** the `data` field remains a standard AG-UI event JSON object

#### Scenario: Cursor identifies replay position
- **WHEN** a GUI records the SSE id for a received event
- **AND WHEN** the GUI reconnects with that value as `lastSeenEventId`
- **THEN** the gateway can determine which retained events come after the cursor for the same thread

### Requirement: Published AG-UI event responses distinguish accepted, stored, and delivered counts
The `/v1/ag-ui/events` response SHALL report the number of accepted events, the number of events stored for bounded replay, and the number of live stream deliveries.

When a valid event batch is stored but no live stream currently matches, the response SHALL make that state visible with `stored_count > 0` and `delivered_count = 0`.

When the gateway cannot store events for replay, it SHALL report `stored_count = 0` and SHALL NOT advertise resumable replay support for those events.

#### Scenario: Valid batch stores without live subscriber
- **WHEN** no GUI stream matches a valid published AG-UI event batch
- **AND WHEN** the gateway has replay storage enabled for the target thread
- **THEN** the publish response reports the batch as accepted
- **AND THEN** the response reports a positive stored count
- **AND THEN** the response reports zero live deliveries

#### Scenario: Live subscriber receives stored batch
- **WHEN** a GUI stream matches a valid published AG-UI event batch
- **AND WHEN** the gateway has replay storage enabled for the target thread
- **THEN** the publish response reports accepted, stored, and delivered counts
- **AND THEN** the matching stream receives the accepted events

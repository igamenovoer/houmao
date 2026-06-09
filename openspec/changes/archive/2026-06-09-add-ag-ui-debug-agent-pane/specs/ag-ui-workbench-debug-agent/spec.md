## ADDED Requirements

### Requirement: Toolbar opens a Debug Agent pane
The AG-UI workbench SHALL provide a toolbar control that opens a Debug Agent pane for local AG-UI message testing.

The Debug Agent pane SHALL be a special workbench pane distinct from operator panes and managed-agent panes. It SHALL NOT create, register, launch, stop, restart, interrupt, or otherwise control a Houmao managed agent.

#### Scenario: User opens a debug pane
- **WHEN** a user clicks the Debug Agent toolbar control
- **THEN** the workbench creates a docked Debug Agent pane
- **AND THEN** the pane receives a stable debug-agent ID, label, AG-UI target URL, and thread ID

#### Scenario: Debug pane does not create managed runtime state
- **WHEN** a Debug Agent pane is opened
- **THEN** the workbench does not create a Houmao managed-agent manifest, tmux session, passive-server registry record, gateway sidecar, mailbox record, or credential binding

### Requirement: Debug Agent pane has white-box sender and AG-UI display sides
The Debug Agent pane SHALL present a side-by-side layout with a white-box sender area and an AG-UI display area.

The display area SHALL receive messages through the same AG-UI client, SSE parser, reducer, diagnostics, and typed component renderer path used by ordinary workbench AG-UI panes.

The sender area SHALL allow a user to validate and send at least raw AG-UI event batches and typed Houmao component payloads to the display.

#### Scenario: Sender and display are shown together
- **WHEN** a user opens a Debug Agent pane
- **THEN** the pane shows a sender area with message controls and endpoint guidance
- **AND THEN** the pane shows an AG-UI display area for transcript, graphics, diagnostics, and raw event evidence

#### Scenario: Display uses normal AG-UI reduction
- **WHEN** the debug relay sends `TEXT_MESSAGE_*` and `TOOL_CALL_*` SSE events to the display area
- **THEN** the display area reduces those events into transcript messages and tool-call records through the ordinary workbench AG-UI event path

### Requirement: Debug relay exposes AG-UI-compatible routes
The workbench host process SHALL expose a local Debug Agent relay route family for each debug-agent ID.

The route family SHALL include capabilities, connect, runs, events publish, and detach routes compatible with the workbench AG-UI client shape.

The relay SHALL expose a status route that identifies the debug relay as available and lists enough route information for the pane and documentation to produce curl examples.

#### Scenario: Debug capabilities are available
- **WHEN** a caller requests `GET /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/capabilities`
- **THEN** the relay returns an AG-UI capabilities response indicating HTTP SSE support and local debug-agent identity

#### Scenario: Display connects through AG-UI connect
- **WHEN** the Debug Agent display connects to `POST /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/connect`
- **THEN** the relay opens a `text/event-stream` response
- **AND THEN** the relay emits an initial state snapshot that includes the debug connection ID, thread ID, run ID, and debug-agent identity

#### Scenario: Detach closes only debug connection bookkeeping
- **WHEN** a caller requests `DELETE /__houmao_debug_agents/<debug_agent_id>/v1/ag-ui/connections/<connection_id>`
- **THEN** the relay detaches that debug connection when present
- **AND THEN** no managed-agent lifecycle operation is performed

### Requirement: External callers can publish AG-UI events with curl
The debug relay SHALL accept externally posted AG-UI event batches and deliver them to matching active Debug Agent display streams.

The events publish route SHALL accept route metadata including `threadId`, optional `runId`, optional `connectionId`, and a non-empty `events` array of standard AG-UI events.

The response SHALL report accepted event count, delivered event count, replay behavior, and the route metadata used.

#### Scenario: Curl-posted chart events render in the display
- **WHEN** a Debug Agent display is connected to thread `debug-agent-1-thread`
- **AND WHEN** an external caller posts a complete `houmao.chart.bar` AG-UI tool-call event batch to `/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events` with `threadId = "debug-agent-1-thread"`
- **THEN** the relay delivers the event batch to the display stream
- **AND THEN** the display renders the chart graphically through the typed component renderer

#### Scenario: Publish response reports live delivery
- **WHEN** a posted AG-UI event batch matches one active Debug Agent display stream
- **THEN** the publish response reports `acceptedCount` equal to the number of accepted events
- **AND THEN** the publish response reports `deliveredCount` greater than zero

#### Scenario: Invalid event batch is rejected
- **WHEN** an external caller posts an empty event batch or an event batch that fails standard AG-UI validation
- **THEN** the relay returns a deterministic validation error
- **AND THEN** the display stream does not receive the invalid batch

### Requirement: Sender can publish typed component payloads
The Debug Agent sender SHALL provide a typed component lane for Houmao component payloads such as `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

The typed component lane SHALL render or wrap valid component payloads into standard AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` events before delivering them to the display.

#### Scenario: Sender publishes a bar chart payload
- **WHEN** a user enters a valid `houmao.chart.bar` payload in the Debug Agent sender
- **AND WHEN** the user sends it to the display
- **THEN** the display receives a complete AG-UI tool-call event sequence
- **AND THEN** the display renders the bar chart graphically

#### Scenario: Sender surfaces component validation failure
- **WHEN** a user enters an invalid typed component payload
- **AND WHEN** the user validates or sends the payload
- **THEN** the sender shows a deterministic validation failure
- **AND THEN** the invalid payload is not delivered as a successful rendered component

### Requirement: Debug replay behavior is explicit and bounded
The debug relay SHALL support bounded per-thread replay for debug use and SHALL make replay behavior explicit in publish responses and the Debug Agent UI.

The relay SHALL support a live-only mode that disables replay and behaves like the live gateway for event batches posted before a matching display stream is connected.

#### Scenario: Replay delivers curl-before-connect batch
- **WHEN** replay is enabled for a debug agent
- **AND WHEN** an external caller posts a valid event batch for a thread before the display connects
- **AND WHEN** the display later connects to that thread
- **THEN** the relay replays the stored batch to the display
- **AND THEN** the UI and response evidence identify the batch as debug replay behavior

#### Scenario: Live-only mode does not replay
- **WHEN** live-only mode is enabled for a debug agent
- **AND WHEN** an external caller posts a valid event batch before any matching display stream is connected
- **THEN** the publish response reports zero live deliveries
- **AND THEN** a later display connection does not receive that earlier batch

### Requirement: Debug Agent persistence excludes stream payloads
The workbench SHALL persist only non-sensitive Debug Agent pane configuration needed to restore the pane layout, label, debug-agent ID, target URL, thread ID, and replay setting.

The workbench SHALL NOT persist debug-agent posted event batches, raw stream events, component payloads, transcript content, rendered graphics, external request bodies, credentials, cookies, authorization headers, or bearer tokens by default.

#### Scenario: Pane metadata persists after reload
- **WHEN** a user opens a Debug Agent pane and reloads the workbench
- **THEN** the workbench may restore the pane's label, debug-agent ID, target URL, thread ID, and replay setting
- **AND THEN** the pane does not restore prior raw event batches or rendered graphics from local storage

#### Scenario: Stream payloads are not stored in local storage
- **WHEN** a Debug Agent display receives transcript messages, raw events, and rendered typed components
- **AND WHEN** local storage is inspected
- **THEN** those stream payloads are absent from persisted workbench state

### Requirement: Deterministic Playwright proof covers external publish and graphics
The repository SHALL include deterministic Playwright coverage for the Debug Agent pane.

The test SHALL prove that an external-style HTTP POST to the debug relay can deliver AG-UI events to the display and that the display renders a graphical typed component.

The test SHALL save or expose enough visual evidence to confirm that the rendered component is visible.

#### Scenario: E2E posts chart events and captures rendered proof
- **WHEN** the Playwright test opens the workbench and creates a Debug Agent pane
- **AND WHEN** the test posts a `houmao.chart.bar` AG-UI event batch to the debug relay events endpoint
- **THEN** the publish response reports accepted events and at least one live delivery
- **AND THEN** the Debug Agent display shows a visible chart with an SVG and rendered bar elements
- **AND THEN** the test captures screenshot evidence of the rendered chart

#### Scenario: E2E covers replay and live-only modes
- **WHEN** the Playwright test posts a valid event batch before connecting the display
- **THEN** the replay-enabled path can show the stored batch after connect
- **AND THEN** the live-only path reports no replay for a batch posted before connect

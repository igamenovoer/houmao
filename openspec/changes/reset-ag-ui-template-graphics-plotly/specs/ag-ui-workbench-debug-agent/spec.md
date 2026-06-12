## MODIFIED Requirements

### Requirement: External callers can publish AG-UI events with curl
The debug relay SHALL accept externally posted AG-UI event batches and deliver them to matching active Debug Agent display streams.

The events publish route SHALL accept route metadata including `threadId`, optional `runId`, optional `connectionId`, and a non-empty `events` array of standard AG-UI events.

The response SHALL report accepted event count, delivered event count, replay behavior, and the route metadata used.

#### Scenario: Curl-posted Plotly template chart events render in the display
- **WHEN** a Debug Agent display is connected to thread `debug-agent-1-thread`
- **AND WHEN** an external caller posts a complete `houmao.graphic.template` AG-UI tool-call event batch to `/__houmao_debug_agents/debug-agent-1/v1/ag-ui/events` with `threadId = "debug-agent-1-thread"`
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
The Debug Agent sender SHALL provide a typed component lane for Houmao component payloads such as `houmao.graphic.template`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

The Debug Agent sender SHALL NOT provide retired fixed chart presets for `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

The typed component lane SHALL render or wrap valid component payloads into standard AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` events before delivering them to the display.

#### Scenario: Sender publishes a Plotly template chart payload
- **WHEN** a user enters a valid `houmao.graphic.template` chart payload in the Debug Agent sender
- **AND WHEN** the user sends it to the display
- **THEN** the display receives a complete AG-UI tool-call event sequence
- **AND THEN** the display renders the chart graphically

#### Scenario: Sender does not offer retired fixed chart presets
- **WHEN** a user opens the typed component lane presets
- **THEN** the preset list omits `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie`
- **AND THEN** chart examples use `houmao.graphic.template`

#### Scenario: Sender surfaces component validation failure
- **WHEN** a user enters an invalid typed component payload
- **AND WHEN** the user validates or sends the payload
- **THEN** the sender shows a deterministic validation failure
- **AND THEN** the invalid payload is not delivered as a successful rendered component

### Requirement: Deterministic Playwright proof covers external publish and graphics
The repository SHALL include deterministic Playwright coverage for the Debug Agent pane.

The test SHALL prove that an external-style HTTP POST to the debug relay can deliver AG-UI events to the display and that the display renders a graphical typed component.

The test SHALL save or expose enough visual evidence to confirm that the rendered component is visible.

#### Scenario: E2E posts template chart events and captures rendered proof
- **WHEN** the Playwright test opens the workbench and creates a Debug Agent pane
- **AND WHEN** the test posts a `houmao.graphic.template` AG-UI event batch to the debug relay events endpoint
- **THEN** the publish response reports accepted events and at least one live delivery
- **AND THEN** the Debug Agent display shows a visible Plotly-backed chart
- **AND THEN** the test captures screenshot evidence of the rendered chart

#### Scenario: E2E covers replay and live-only modes
- **WHEN** the Playwright test posts a valid event batch before connecting the display
- **THEN** the replay-enabled path can show the stored batch after connect
- **AND THEN** the live-only path reports no replay for a batch posted before connect

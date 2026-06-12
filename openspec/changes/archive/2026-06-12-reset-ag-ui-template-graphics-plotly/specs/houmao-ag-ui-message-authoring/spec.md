## MODIFIED Requirements

### Requirement: Houmao defines typed GUI component schemas for AG-UI authoring
Houmao SHALL define an application-layer GUI component schema namespace for typed AG-UI authoring.

The schema namespace SHALL include `houmao.graphic.template`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard` in the supported component set.

The schema namespace SHALL NOT include the retired fixed chart APIs `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

Each component schema SHALL include a stable component name, `schemaVersion`, description, JSON Schema-compatible payload shape, and at least one valid example payload.

Each typed component payload SHALL validate without requiring a live gateway or frontend process.

Component names and payload schemas SHALL be documented as Houmao application-layer protocol, not as AG-UI core standard names.

#### Scenario: Component schemas are discoverable offline
- **WHEN** an agent asks `houmao-mgr` for the schema of `houmao.graphic.template`
- **THEN** the command returns the component name, schema version, JSON Schema-compatible payload shape, and a valid Plotly-backed chart example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Retired fixed chart schemas are not discoverable
- **WHEN** an agent asks `houmao-mgr` for the schema of `houmao.chart.bar`
- **THEN** the command exits non-zero with an unsupported component diagnostic
- **AND THEN** the diagnostic directs the agent to `houmao.graphic.template`

#### Scenario: Component namespace is clearly Houmao-owned
- **WHEN** an agent lists supported GUI components
- **THEN** the returned component names use the `houmao.` namespace
- **AND THEN** the command describes those names as Houmao application-layer component schemas carried over AG-UI

### Requirement: `houmao-mgr internals ag-ui` exposes schema discovery and payload validation
`houmao-mgr` SHALL expose AG-UI authoring utilities under `houmao-mgr internals ag-ui`.

The CLI SHALL support listing component schemas, returning one component schema, validating one component payload, validating a standard AG-UI event sequence, and rendering a component payload into AG-UI events.

Any `houmao-mgr` publish helper for rendered AG-UI events SHALL be Houmao-gateway-specific and SHALL NOT act as an arbitrary third-party endpoint client.

Validation failures SHALL include the selected component or event context, normalized field paths, and a concise repair hint without echoing large unsafe payload content.

The commands SHALL accept JSON input from stdin or a path.

#### Scenario: Valid component payload passes validation
- **WHEN** an agent runs `houmao-mgr internals ag-ui components validate houmao.graphic.template --input payload.json`
- **AND WHEN** `payload.json` matches the Plotly-backed `houmao.graphic.template` schema
- **THEN** the command exits successfully
- **AND THEN** the output identifies the component and schema version that accepted the payload

#### Scenario: Retired fixed chart payload fails validation
- **WHEN** an agent runs `houmao-mgr internals ag-ui components validate houmao.chart.line --input payload.json`
- **THEN** the command exits non-zero
- **AND THEN** the diagnostic names `houmao.chart.line` as unsupported or retired

#### Scenario: Invalid component payload reports field paths
- **WHEN** an agent validates a `houmao.table` payload with rows that do not match the declared columns
- **THEN** the command exits non-zero
- **AND THEN** the diagnostic names `houmao.table`
- **AND THEN** the diagnostic includes normalized field paths for the invalid fields

#### Scenario: Event validation accepts standard AG-UI events
- **WHEN** an agent runs `houmao-mgr internals ag-ui events validate --input events.json`
- **AND WHEN** `events.json` contains a valid AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` sequence
- **THEN** the command exits successfully
- **AND THEN** it reports the accepted event count

### Requirement: Component rendering emits standard AG-UI tool-call events
`houmao-mgr internals ag-ui events render` SHALL render a validated Houmao component payload into AG-UI core events.

The canonical render form SHALL be a complete AG-UI tool-call sequence whose `toolCallName` equals the Houmao component name.

The generated sequence SHALL include `TOOL_CALL_START`, one or more `TOOL_CALL_ARGS`, and `TOOL_CALL_END`.

The generated tool-call arguments SHALL contain the validated component payload using stable JSON field names and SHALL preserve `schemaVersion`.

The render command SHALL support deterministic output formats for machine use, including JSON array, JSON Lines, and SSE frame output.

The render command SHALL be able to generate stable message and tool-call identifiers from explicit options or deterministic defaults.

#### Scenario: Plotly template chart renders to AG-UI tool-call events
- **WHEN** an agent renders a valid `houmao.graphic.template` chart payload
- **THEN** the output event sequence contains `TOOL_CALL_START` with `toolCallName` equal to `houmao.graphic.template`
- **AND THEN** the sequence contains `TOOL_CALL_ARGS` whose JSON payload validates as `houmao.graphic.template`
- **AND THEN** the sequence ends that tool call with `TOOL_CALL_END`

#### Scenario: Render output supports SSE framing
- **WHEN** an agent renders a valid `houmao.metric_grid` payload with `--format sse`
- **THEN** each emitted event is encoded as a `data: <json>` SSE frame
- **AND THEN** the frame JSON uses AG-UI camelCase field names

#### Scenario: Render does not require gateway availability
- **WHEN** no Houmao gateway is running
- **AND WHEN** an agent renders a valid component payload
- **THEN** the command still emits a valid AG-UI event sequence

### Requirement: Houmao gateway publish helper sends only standard AG-UI events to Houmao gateways
`houmao-mgr` SHALL provide a Houmao-gateway-specific AG-UI publish helper for sending caller-provided standard AG-UI events to a Houmao per-agent gateway ingestion route.

The publish helper SHALL validate the event sequence before sending it.

The publish helper SHALL NOT send Houmao typed component payloads directly unless they have first been rendered into standard AG-UI events.

The publish helper SHALL target Houmao gateway AG-UI ingestion semantics and SHALL NOT accept arbitrary third-party endpoint URLs, HTTP methods, content types, or endpoint-specific request policies.

For third-party AG-UI-compatible endpoints, `houmao-mgr` SHALL provide generated and validated AG-UI event output, and the agent SHALL perform delivery outside the Houmao publish helper according to that endpoint's own constraints.

The publish helper SHALL fail before network submission when the input is not a valid AG-UI event sequence.

The publish helper SHALL report the Houmao gateway publish response, including accepted, stored, and delivered counts when the gateway returns them.

The publish helper SHALL identify Houmao gateway GUI-event publishing as live-only when `stored_count = 0` and replay support is absent.

The publish helper SHALL NOT claim durable delivery or GUI visibility when the gateway reports `delivered_count = 0`.

#### Scenario: Publish rejects typed payload before rendering
- **WHEN** an agent passes a raw `houmao.graphic.template` component payload to the publish helper as the event input
- **THEN** the command exits non-zero before contacting the Houmao gateway
- **AND THEN** the diagnostic tells the agent to render the component payload into AG-UI events first

#### Scenario: Publish sends validated AG-UI events to Houmao gateway
- **WHEN** an agent provides a valid AG-UI event sequence and a resolvable Houmao gateway target
- **THEN** the publish helper validates the events
- **AND THEN** it sends the events to the Houmao gateway AG-UI ingestion route
- **AND THEN** it reports the gateway response status without logging credential material

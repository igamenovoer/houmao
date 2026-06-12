# houmao-ag-ui-message-authoring Specification

## Purpose
Define Houmao-owned typed GUI component schemas, `houmao-mgr internals ag-ui` authoring utilities, AG-UI event rendering, Houmao gateway publish behavior, and unsafe content boundaries for agent-authored GUI messages.
## Requirements
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

### Requirement: Authoring commands preserve unsafe content boundaries
The AG-UI authoring schema SHALL NOT accept arbitrary raw HTML, scriptable SVG, iframe content, JavaScript URLs, credential material, or local file contents as component payload by default.

Components that display external or inline media SHALL use explicit safe fields and validation rules.

The authoring CLI SHALL reject unsafe inline content before producing AG-UI events.

#### Scenario: Unsafe SVG is rejected by authoring validation
- **WHEN** an agent validates a component payload containing inline SVG with a script tag or event-handler attribute
- **THEN** validation fails
- **AND THEN** no AG-UI event sequence is produced from that payload

#### Scenario: Secret-like fields are not echoed in validation diagnostics
- **WHEN** validation fails for a payload containing a field named like a token, key, password, or credential
- **THEN** the diagnostic includes the field path
- **AND THEN** the diagnostic does not echo the raw secret-like value

### Requirement: Houmao gateway publish helper can rely on active-thread fallback
The Houmao AG-UI publish helper SHALL allow callers to omit explicit AG-UI routing when targeting a Houmao gateway.

When explicit routing is omitted, the publish helper SHALL submit the validated AG-UI event batch to the Houmao gateway in a form that allows active-thread fallback routing.

Explicit `connectionId`, `threadId`, or `runId` options SHALL remain available and SHALL take priority over active-thread and default sink fallback.

When the gateway routes through active-thread, the publish helper SHALL report the gateway publish result, including accepted and delivered counts.

When the gateway reports that it used the default sink because no destination was available, the publish helper SHALL surface that warning clearly.

The publish helper SHALL NOT claim GUI visibility when the gateway reports default-sink routing or zero live delivery.

The publish helper SHALL NOT describe last-sent-thread as a fallback route.

#### Scenario: Publish helper omits routing for active-thread fallback
- **WHEN** an agent has rendered and validated a Houmao chart as standard AG-UI events
- **AND WHEN** the agent runs the Houmao gateway publish helper without `--thread-id`, `--run-id`, or `--connection-id`
- **THEN** the helper submits the event batch to the Houmao gateway for active-thread fallback routing
- **AND THEN** the helper reports the gateway publish result and warnings

#### Scenario: Explicit route still overrides active-thread fallback
- **WHEN** an agent passes `--thread-id agent-explicit-thread` to the publish helper
- **AND WHEN** the gateway has a different active-thread value
- **THEN** the helper sends the explicit thread route
- **AND THEN** it does not ask the gateway to infer the route from active-thread

#### Scenario: Default sink warning is shown for missing active thread
- **WHEN** an agent runs the publish helper without an explicit route
- **AND WHEN** the gateway reports default-sink routing due to no active-thread destination
- **THEN** the helper reports the default-sink warning
- **AND THEN** it does not describe the graphic as visible in the GUI

#### Scenario: Last-sent bookkeeping is not described as fallback
- **WHEN** publish helper documentation or output describes omitted routing
- **THEN** it lists active-thread fallback and default sink behavior
- **AND THEN** it does not list last-sent-thread as a fallback destination

### Requirement: Authoring utilities support Layer 2 Vega-Lite graphics
Houmao AG-UI authoring utilities SHALL include `houmao.graphic.vegalite` in the discoverable Houmao typed component namespace.

The component schema SHALL validate without requiring a live gateway, passive server, workbench browser, Python Altair execution, or Vega runtime.

The generic `houmao-mgr internals ag-ui components validate` and `events render` commands SHALL work for `houmao.graphic.vegalite` through the existing component authoring surface.

#### Scenario: Vega-Lite schema appears in component list
- **WHEN** an agent runs `houmao-mgr internals ag-ui components list`
- **THEN** the returned component list includes `houmao.graphic.vegalite`
- **AND THEN** the list continues to include `houmao.graphic.template`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`

#### Scenario: Vega-Lite payload validates offline
- **WHEN** an agent validates a `houmao.graphic.vegalite` payload with inline Vega-Lite data values
- **THEN** the command exits successfully
- **AND THEN** the output identifies `houmao.graphic.vegalite` and the accepted schema version

#### Scenario: Vega-Lite payload renders to AG-UI tool-call events
- **WHEN** an agent renders a valid `houmao.graphic.vegalite` payload
- **THEN** the output event sequence contains `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`
- **AND THEN** the `TOOL_CALL_START.toolCallName` value is `houmao.graphic.vegalite`
- **AND THEN** the rendered event sequence passes standard AG-UI event validation

### Requirement: Authoring validation accepts Altair-shaped Vega-Lite JSON
Authoring validation SHALL accept valid Vega-Lite JSON generated by Python Altair when the generated object is passed as the `spec` field in a `houmao.graphic.vegalite` payload.

Authoring validation SHALL treat Altair as optional authoring context and SHALL NOT require pandas, notebook display integration, `vl-convert-python`, or Python code execution to validate or render the component payload.

#### Scenario: Altair schema URL is accepted
- **WHEN** a `houmao.graphic.vegalite` payload contains a `spec.$schema` value matching a supported Vega-Lite v6 schema URL emitted by Altair
- **THEN** authoring validation accepts the schema URL
- **AND THEN** the normalized payload preserves the declarative `spec` object

#### Scenario: Python code is not accepted as the spec
- **WHEN** an agent submits Python or Altair source code instead of a JSON object under `spec`
- **THEN** authoring validation rejects the payload
- **AND THEN** the diagnostic instructs the agent to send `chart.to_dict()` or equivalent Vega-Lite JSON

### Requirement: Dashboard children may include Vega-Lite graphics
Houmao dashboard payloads SHALL allow `houmao.graphic.vegalite` as a child component when the child props validate as a Vega-Lite graphic payload.

Dashboard validation SHALL continue to reject unknown or malformed child components.

#### Scenario: Dashboard embeds a Vega-Lite child
- **WHEN** an agent validates a `houmao.dashboard` payload containing a `houmao.graphic.vegalite` child with valid props
- **THEN** component validation accepts the dashboard
- **AND THEN** rendered dashboard AG-UI events preserve the Vega-Lite child component name and props


## ADDED Requirements

### Requirement: Implementation graphics categories are listable
Houmao SHALL provide category-specific commands that list supported graphics implementation schemas separately from the full implementation schema list.

The `templated-graphics` list SHALL include `houmao.graphic.template` when that implementation is supported.

The `templated-graphics` list SHALL identify `houmao.graphic.template` as a Layer 1 Plotly-backed schema with schema version `3`, backend `plotly`, renderer `plotly.js`, template kind, and available catalog names.

The `freeform-graphics` list SHALL include `houmao.graphic.vegalite` when that implementation is supported.

The `freeform-graphics` list SHALL identify `houmao.graphic.vegalite` as a Layer 2 Vega-Lite schema with schema version `1`, backend `vega-lite`, renderer `vega-embed`, freeform graphics kind, and available catalog names.

The graphics category lists SHALL NOT include non-graphic UI implementation schemas such as `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard`.

The graphics category lists SHALL NOT treat Plotly trace types such as `bar`, `heatmap`, or `sankey` as separate schemas; those SHALL remain catalog entries for `houmao.graphic.template`.

#### Scenario: Templated graphics schemas are listed separately
- **WHEN** an agent runs `houmao-mgr ag-ui impl templated-graphics list`
- **THEN** the output includes `houmao.graphic.template` with schema version `3`
- **AND THEN** the output identifies backend `plotly` and renderer `plotly.js`
- **AND THEN** the output does not include `houmao.graphic.vegalite`
- **AND THEN** the output does not include `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard`

#### Scenario: Freeform graphics schemas are listed separately
- **WHEN** an agent runs `houmao-mgr ag-ui impl freeform-graphics list`
- **THEN** the output includes `houmao.graphic.vegalite` with schema version `1`
- **AND THEN** the output identifies backend `vega-lite` and renderer `vega-embed`
- **AND THEN** the output does not include `houmao.graphic.template`
- **AND THEN** the output does not include `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard`

#### Scenario: Plotly traces remain catalog entries
- **WHEN** an agent runs `houmao-mgr ag-ui impl templated-graphics list`
- **THEN** the output identifies that `houmao.graphic.template` has a `traces` catalog
- **AND THEN** the output does not list `heatmap` or `sankey` as standalone schema names

### Requirement: New-component rendering supports frontend-specific implementations
Houmao SHALL provide an implementation-layer `new-component` command that renders a standard AG-UI tool-call event sequence for an arbitrary caller-provided tool name and JSON argument object.

The `new-component` renderer SHALL compose with the same schema-agnostic AG-UI protocol tool-call renderer used by `houmao-mgr ag-ui protocol tool-call render`.

The schema-agnostic renderer SHALL NOT require the tool name to appear in the Houmao implementation registry.

The schema-agnostic renderer SHALL validate only standard AG-UI protocol properties, including safe non-empty tool-call name, valid JSON arguments, deterministic tool-call ordering, event batch count limits, and encoded byte limits.

The schema-agnostic renderer SHALL NOT claim that a GUI can render the tool-call payload unless a matching frontend implementation is known or the user provides that knowledge separately.

#### Scenario: Custom frontend tool call renders through new-component command
- **WHEN** a user runs `houmao-mgr ag-ui impl new-component render --tool-name myapp.graphic.timeline --args payload.json`
- **AND WHEN** `payload.json` contains a valid JSON object
- **THEN** the command emits a standard AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` sequence
- **AND THEN** the `TOOL_CALL_START.toolCallName` value is `myapp.graphic.timeline`
- **AND THEN** the command does not require `myapp.graphic.timeline` to be listed by `houmao-mgr ag-ui impl list`

#### Scenario: Protocol validity does not imply render support
- **WHEN** a protocol-rendered event sequence uses a custom tool name unknown to Houmao
- **THEN** protocol validation can still accept the standard AG-UI event shape
- **AND THEN** Houmao output and documentation do not claim that any GUI will render that custom payload

## MODIFIED Requirements

### Requirement: Houmao defines typed GUI component schemas for AG-UI authoring
Houmao SHALL define a Houmao-owned AG-UI implementation schema namespace for typed GUI authoring.

The implementation schema namespace SHALL include `houmao.graphic.template`, `houmao.graphic.vegalite`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard` in the supported implementation set.

The implementation schema namespace SHALL NOT include the retired fixed chart APIs `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie`.

Each implementation schema SHALL include a stable tool name, `schemaVersion`, description, JSON Schema-compatible payload shape, and at least one valid example payload.

Each typed implementation payload SHALL validate without requiring a live gateway or frontend process.

Implementation names and payload schemas SHALL be documented as Houmao application-layer implementation contracts carried over AG-UI, not as AG-UI protocol names.

#### Scenario: Implementation schemas are discoverable offline
- **WHEN** an agent asks `houmao-mgr ag-ui impl schema houmao.graphic.template`
- **THEN** the command returns the implementation name, schema version, JSON Schema-compatible payload shape, and a valid Plotly-backed chart example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Retired fixed chart schemas are not discoverable
- **WHEN** an agent asks `houmao-mgr ag-ui impl schema houmao.chart.bar`
- **THEN** the command exits non-zero with an unsupported implementation diagnostic
- **AND THEN** the diagnostic directs the agent to `houmao.graphic.template`

#### Scenario: Implementation namespace is clearly Houmao-owned
- **WHEN** an agent lists supported GUI implementations
- **THEN** the returned implementation names use the `houmao.` namespace for Houmao-owned payload contracts
- **AND THEN** the command describes those names as Houmao application-layer implementation contracts carried over AG-UI protocol events

### Requirement: `houmao-mgr internals ag-ui` exposes schema discovery and payload validation
`houmao-mgr` SHALL expose AG-UI authoring utilities through separate `houmao-mgr ag-ui protocol` and `houmao-mgr ag-ui impl` command surfaces.

The `protocol` surface SHALL support validating a standard AG-UI event sequence, framing a standard AG-UI event sequence as JSON, JSON Lines, or SSE, and rendering a generic standard AG-UI tool-call event sequence for any valid caller-provided tool name and JSON arguments.

The `impl` surface SHALL support listing Houmao implementation schemas, listing supported `templated-graphics` schemas, listing supported `freeform-graphics` schemas, rendering a schema-agnostic `new-component` payload into AG-UI protocol events, returning one implementation schema, validating one Houmao implementation payload, rendering one validated Houmao implementation payload into AG-UI protocol events, and returning implementation-specific catalogs.

Any `houmao-mgr` publish helper for rendered AG-UI events SHALL be Houmao-gateway-specific and SHALL NOT act as an arbitrary third-party endpoint client.

Validation failures SHALL include the selected implementation or event context, normalized field paths, and a concise repair hint without echoing large unsafe payload content.

The commands SHALL accept JSON input from stdin or a path.

#### Scenario: Valid implementation payload passes validation
- **WHEN** an agent runs `houmao-mgr ag-ui impl validate houmao.graphic.template --input payload.json`
- **AND WHEN** `payload.json` matches the Plotly-backed `houmao.graphic.template` schema
- **THEN** the command exits successfully
- **AND THEN** the output identifies the implementation and schema version that accepted the payload

#### Scenario: Retired fixed chart payload fails validation
- **WHEN** an agent runs `houmao-mgr ag-ui impl validate houmao.chart.line --input payload.json`
- **THEN** the command exits non-zero
- **AND THEN** the diagnostic names `houmao.chart.line` as unsupported or retired

#### Scenario: Invalid implementation payload reports field paths
- **WHEN** an agent validates a `houmao.table` payload with rows that do not match the declared columns
- **THEN** the command exits non-zero
- **AND THEN** the diagnostic names `houmao.table`
- **AND THEN** the diagnostic includes normalized field paths for the invalid fields

#### Scenario: Event validation accepts standard AG-UI events
- **WHEN** an agent runs `houmao-mgr ag-ui protocol events validate --input events.json`
- **AND WHEN** `events.json` contains a valid AG-UI `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END` sequence
- **THEN** the command exits successfully
- **AND THEN** it reports the accepted event count

### Requirement: Component rendering emits standard AG-UI tool-call events
`houmao-mgr ag-ui impl render` SHALL render a validated Houmao implementation payload into AG-UI protocol events.

The canonical render form SHALL be a complete AG-UI tool-call sequence whose `toolCallName` equals the Houmao implementation name.

The generated sequence SHALL include `TOOL_CALL_START`, one or more `TOOL_CALL_ARGS`, and `TOOL_CALL_END`.

The generated tool-call arguments SHALL contain the validated implementation payload using stable JSON field names and SHALL preserve `schemaVersion`.

The implementation render command SHALL support deterministic output formats for machine use, including JSON array, JSON Lines, and SSE frame output, either directly or by composing with `houmao-mgr ag-ui protocol events frame`.

The render command SHALL be able to generate stable message and tool-call identifiers from explicit options or deterministic defaults.

#### Scenario: Plotly template implementation renders to AG-UI tool-call events
- **WHEN** an agent renders a valid `houmao.graphic.template` chart payload with `houmao-mgr ag-ui impl render`
- **THEN** the output event sequence contains `TOOL_CALL_START` with `toolCallName` equal to `houmao.graphic.template`
- **AND THEN** the sequence contains `TOOL_CALL_ARGS` whose JSON payload validates as `houmao.graphic.template`
- **AND THEN** the sequence ends that tool call with `TOOL_CALL_END`

#### Scenario: Render output supports SSE framing
- **WHEN** an agent renders a valid `houmao.metric_grid` payload with SSE output requested
- **THEN** each emitted event is encoded as a `data: <json>` SSE frame
- **AND THEN** the frame JSON uses AG-UI camelCase field names

#### Scenario: Render does not require gateway availability
- **WHEN** no Houmao gateway is running
- **AND WHEN** an agent renders a valid implementation payload
- **THEN** the command still emits a valid AG-UI event sequence

### Requirement: Authoring utilities support Layer 2 Vega-Lite graphics
Houmao AG-UI implementation utilities SHALL include `houmao.graphic.vegalite` in the discoverable Houmao implementation namespace.

The implementation schema SHALL validate without requiring a live gateway, passive server, workbench browser, Python Altair execution, or Vega runtime.

The generic `houmao-mgr ag-ui impl validate` and `houmao-mgr ag-ui impl render` commands SHALL work for `houmao.graphic.vegalite` through the implementation authoring surface.

#### Scenario: Vega-Lite schema appears in implementation list
- **WHEN** an agent runs `houmao-mgr ag-ui impl list`
- **THEN** the returned implementation list includes `houmao.graphic.vegalite`
- **AND THEN** the list continues to include `houmao.graphic.template`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`

#### Scenario: Vega-Lite payload validates offline
- **WHEN** an agent validates a `houmao.graphic.vegalite` payload with inline Vega-Lite data values
- **THEN** the command exits successfully
- **AND THEN** the output identifies `houmao.graphic.vegalite` and the accepted schema version

#### Scenario: Vega-Lite payload renders to AG-UI tool-call events
- **WHEN** an agent renders a valid `houmao.graphic.vegalite` payload
- **THEN** the output event sequence contains `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`
- **AND THEN** the `TOOL_CALL_START.toolCallName` value is `houmao.graphic.vegalite`
- **AND THEN** the rendered event sequence passes standard AG-UI protocol event validation

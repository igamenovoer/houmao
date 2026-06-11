## ADDED Requirements

### Requirement: Houmao defines standardized template graphic payloads
Houmao SHALL define a Layer 1 AG-UI component named `houmao.graphic.template`.

The payload SHALL include `schemaVersion`, `chartType`, `renderer`, `title`, optional `subtitle`, `data`, `encoding`, optional `interactions`, optional `style`, and optional `extra`.

The initial `chartType` values SHALL include `bar`, `line`, `scatter`, `area`, and `pie`.

The payload SHALL represent data as inline JSON rows under `data.values`.

The payload SHALL represent renderer-neutral visual intent through encoding channels that identify data fields, field types, titles, and common chart hints.

The standardized fields SHALL be sufficient for a GUI to render the chart without using `extra`.

#### Scenario: Template graphic schema is discoverable
- **WHEN** an agent asks `houmao-mgr internals ag-ui components schema houmao.graphic.template`
- **THEN** the command returns the component name, schema version, JSON Schema-compatible payload shape, and a valid example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Standardized payload validates offline
- **WHEN** an agent validates a `houmao.graphic.template` payload with inline rows and valid encodings
- **THEN** the command exits successfully
- **AND THEN** the output identifies `houmao.graphic.template` and the accepted schema version

### Requirement: Template graphics support renderer selection and fallback
Template graphic payloads SHALL support renderer selection through a `renderer` object.

The `renderer` object SHALL support a `preferred` renderer id and a `fallback` renderer id list.

The initial renderer ids SHALL include `recharts` and `vega-lite`.

When a preferred renderer is unavailable or unsupported for the payload, the GUI SHALL select the first supported fallback renderer.

When no requested renderer is usable, the GUI SHALL use a deterministic fallback or show an invalid component message that preserves the payload for diagnostics.

#### Scenario: Preferred Vega-Lite renderer is selected
- **WHEN** a complete `houmao.graphic.template` tool call requests `renderer.preferred` equal to `vega-lite`
- **AND WHEN** the workbench supports Vega-Lite for the chart type
- **THEN** the workbench renders the chart with the Vega-Lite renderer

#### Scenario: Renderer fallback is used
- **WHEN** a complete `houmao.graphic.template` tool call requests an unavailable preferred renderer and includes `recharts` in `renderer.fallback`
- **THEN** the workbench renders the chart with Recharts when Recharts supports the chart type
- **AND THEN** the workbench does not reject the payload solely because the preferred renderer was unavailable

### Requirement: Renderer-specific extra fields are constrained refinements
Template graphic payloads SHALL allow an optional `extra` object keyed by renderer id.

The `extra` object SHALL be optional and SHALL NOT be required for correct rendering.

Python authoring validation SHALL reject `extra` content that attempts to replace standardized chart semantics, including full backend specs, raw data replacement, raw transform lists, raw layer or concat structures, arbitrary JavaScript, HTML, iframe content, scriptable SVG, or remote URL loading.

The Vega-Lite `extra` block SHALL be limited to safe renderer presentation refinements such as config, mark style, axis style, legend style, and view sizing hints.

Unsupported renderer keys or unsupported fields inside a known renderer block SHALL be ignored by renderers or reported as non-fatal diagnostics.

#### Scenario: Safe Vega-Lite extra validates
- **WHEN** a `houmao.graphic.template` payload includes `extra.vega-lite.config.axis.labelFontSize`
- **THEN** Python authoring validation accepts the payload
- **AND THEN** a renderer that does not use Vega-Lite can still render the chart from standardized fields

#### Scenario: Full Vega-Lite spec in extra is rejected
- **WHEN** a `houmao.graphic.template` payload includes `extra.vega-lite.data` or `extra.vega-lite.layer`
- **THEN** Python authoring validation rejects the payload before rendering AG-UI events
- **AND THEN** the diagnostic names the invalid field path without echoing unsafe content

### Requirement: Template graphic rendering emits standard AG-UI events
`houmao-mgr internals ag-ui events render` SHALL render a validated `houmao.graphic.template` payload into a complete standard AG-UI tool-call event sequence.

The generated `TOOL_CALL_START` event SHALL use `toolCallName` equal to `houmao.graphic.template`.

The generated `TOOL_CALL_ARGS` event SHALL contain the normalized payload with stable camelCase field names.

The generated sequence SHALL remain compatible with the existing Houmao gateway publish helper.

#### Scenario: Template graphic renders to tool-call events
- **WHEN** an agent renders a valid `houmao.graphic.template` payload
- **THEN** the output event sequence contains `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`
- **AND THEN** the `TOOL_CALL_START.toolCallName` value is `houmao.graphic.template`
- **AND THEN** the rendered event sequence passes standard AG-UI event validation

#### Scenario: Publish helper accepts rendered template events
- **WHEN** an agent passes rendered `houmao.graphic.template` AG-UI events to the Houmao gateway publish helper
- **THEN** the helper validates the standard event sequence before sending
- **AND THEN** the helper does not require knowledge of the template graphic schema at publish time

### Requirement: Workbench renders template graphics through Recharts and Vega-Lite
The AG-UI workbench SHALL render completed `houmao.graphic.template` tool calls.

The workbench SHALL provide a renderer registry keyed by renderer id.

The Recharts renderer SHALL render supported template graphic payloads using the existing React chart stack.

The Vega-Lite renderer SHALL convert supported template graphic payloads into a Vega-Lite spec and render it with a browser Vega runtime.

The Vega-Lite renderer SHALL clean up mounted Vega views when the React component unmounts or rerenders.

The workbench SHALL show deterministic invalid or unsupported component fallbacks for malformed template payloads or unsupported chart types.

#### Scenario: Vega-Lite chart renders visibly
- **WHEN** a stream emits a complete `houmao.graphic.template` tool-call sequence for a bar chart with `renderer.preferred` equal to `vega-lite`
- **THEN** the workbench renders a visible chart in the AG-UI pane
- **AND THEN** the raw tool-call event details remain available for diagnostics

#### Scenario: Malformed template payload degrades visibly
- **WHEN** a stream emits a complete `houmao.graphic.template` tool-call sequence with missing required fields
- **THEN** the workbench shows an invalid component fallback
- **AND THEN** the workbench does not crash or remove unrelated pane content

### Requirement: Capabilities advertise Layer 1 template graphics
The AG-UI capabilities response SHALL advertise Houmao Layer 1 template graphics in Houmao custom metadata.

The metadata SHALL include the template tool name, schema version, supported chart types, supported renderer ids, default renderer id, `extra` policy, and whether raw Vega-Lite DSL specs are supported.

The initial raw Vega-Lite DSL support flag SHALL be false for this Layer 1 change.

#### Scenario: Capabilities list template renderer ids
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes Houmao custom metadata for template graphics
- **AND THEN** that metadata lists `recharts` and `vega-lite` as supported Layer 1 renderer ids
- **AND THEN** the metadata states that raw Vega-Lite DSL graphics are not part of this Layer 1 feature

### Requirement: Agent guidance prefers template graphics for ordinary charts
The `houmao-interop-ag-ui` skill SHALL teach agents to prefer `houmao.graphic.template` for new ordinary charts.

The skill SHALL explain that Layer 1 template graphics use standardized Houmao JSON and optional renderer-specific `extra`.

The skill SHALL explain that `extra` is disposable and must not be used as a full Vega-Lite, Plotly, React, HTML, or JavaScript escape hatch.

The skill SHALL keep the existing render, validate, and publish workflow based on `houmao-mgr internals ag-ui` and `houmao-mgr agents ... gateway ag-ui publish`.

#### Scenario: Agent chooses template graphics
- **WHEN** an agent needs to display an ordinary bar, line, scatter, area, or pie chart
- **THEN** the skill directs it to inspect and use `houmao.graphic.template`
- **AND THEN** the skill tells it to validate and render the payload before publishing

#### Scenario: Agent does not use Layer 1 as raw Vega-Lite
- **WHEN** an agent needs a custom Vega-Lite chart structure that cannot be represented by standardized template fields
- **THEN** the skill tells it that raw Vega-Lite belongs to a future or separate Layer 2 path
- **AND THEN** the skill does not tell it to place a full Vega-Lite spec in Layer 1 `extra`

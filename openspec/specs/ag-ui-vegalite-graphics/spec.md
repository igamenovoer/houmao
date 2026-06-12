# ag-ui-vegalite-graphics Specification

## Purpose
TBD - created by archiving change add-ag-ui-vegalite-graphics. Update Purpose after archive.
## Requirements
### Requirement: Houmao defines Layer 2 Vega-Lite graphics
Houmao SHALL define a Layer 2 AG-UI typed component named `houmao.graphic.vegalite`.

The payload SHALL contain `schemaVersion`, `library`, `specVersion`, `title`, optional `description`, a raw Vega-Lite JSON object under `spec`, and optional display metadata.

The payload SHALL require `schemaVersion` equal to `1`, `library` equal to `vega-lite`, and `specVersion` equal to the supported Vega-Lite major version.

The component SHALL be separate from Layer 1 `houmao.graphic.template`; Layer 1 SHALL NOT use `renderer.preferred`, `renderer.fallback`, or `extra` fields to carry raw Vega-Lite specs.

#### Scenario: Vega-Lite component schema is discoverable
- **WHEN** an agent asks `houmao-mgr internals ag-ui components schema houmao.graphic.vegalite`
- **THEN** the command returns the component name, schema version, JSON Schema-compatible payload shape, and a valid example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Vega-Lite component stays separate from Layer 1
- **WHEN** an agent inspects Layer 2 component guidance
- **THEN** the guidance identifies `houmao.graphic.vegalite` as the raw Vega-Lite DSL component
- **AND THEN** it does not instruct the agent to place Vega-Lite specs in `houmao.graphic.template.extra`

### Requirement: Vega-Lite payloads support optional Altair authoring
Agents SHALL be allowed to use Python Altair as an optional authoring tool to generate the Vega-Lite `spec` JSON for `houmao.graphic.vegalite`.

The system SHALL treat Altair output as JSON input to the component payload. The gateway and workbench SHALL NOT execute Python, Altair code, pandas code, notebooks, or local source files while validating or rendering the component.

Hand-authored Vega-Lite JSON SHALL remain valid when it satisfies the same payload and safety rules.

#### Scenario: Altair-generated JSON validates
- **WHEN** an agent generates a Vega-Lite v6 object with Altair `chart.to_dict()`
- **AND WHEN** the object uses inline `data.values`
- **AND WHEN** the object is placed under `houmao.graphic.vegalite.spec`
- **THEN** component validation accepts the payload
- **AND THEN** rendered AG-UI events contain the declarative JSON spec, not Python code

#### Scenario: Hand-authored Vega-Lite JSON validates
- **WHEN** an agent provides a hand-authored Vega-Lite v6 object with inline data under `spec`
- **THEN** component validation applies the same envelope, size, and safety checks
- **AND THEN** the payload can be rendered into standard AG-UI tool-call events

### Requirement: Vega-Lite safety policy rejects remote and unsafe content
Layer 2 Vega-Lite validation SHALL reject remote data loading, unsafe inline HTML, script tags, iframe content, JavaScript URLs, scriptable SVG, and payloads that exceed configured size limits.

Validation SHALL allow known Vega-Lite v6 `$schema` URLs emitted by Altair while still rejecting remote data or asset loading fields such as `data.url`.

Validation diagnostics SHALL name the failing component and normalized field path without echoing credential material or large unsafe content.

#### Scenario: Vega-Lite schema URL is allowed
- **WHEN** a `houmao.graphic.vegalite` payload includes `$schema` equal to a known Vega-Lite v6 schema URL
- **THEN** component validation does not reject the payload solely because of that schema URL

#### Scenario: Remote data URL is rejected
- **WHEN** a `houmao.graphic.vegalite` payload includes `spec.data.url` with an HTTP or HTTPS URL
- **THEN** component validation rejects the payload before AG-UI event rendering
- **AND THEN** the diagnostic names `houmao.graphic.vegalite` and the remote data field path

#### Scenario: Unsafe inline content is rejected
- **WHEN** a `houmao.graphic.vegalite` payload contains inline script, iframe, JavaScript URL, or scriptable SVG content
- **THEN** component validation rejects the payload
- **AND THEN** no AG-UI event sequence is produced from that payload

### Requirement: Workbench renders Vega-Lite with bounded diagnostics
The workbench SHALL render completed `houmao.graphic.vegalite` tool calls using a browser Vega-Lite runtime through `vega-embed`.

The renderer SHALL mount the Vega-Lite view in a bounded component frame, apply workbench display defaults, disable external data loading by default, and clean up the mounted Vega view when the component rerenders, unmounts, or the pane is cleared.

Malformed specs, compile errors, runtime errors, unsupported versions, and rejected remote data SHALL produce deterministic visible fallbacks without crashing the pane or removing unrelated content.

#### Scenario: Valid Vega-Lite chart renders visibly
- **WHEN** a stream emits a complete `houmao.graphic.vegalite` tool-call sequence with a valid inline Vega-Lite bar chart spec
- **THEN** the workbench renders a visible Vega-Lite chart in the AG-UI pane
- **AND THEN** raw tool-call event details remain available for diagnostics

#### Scenario: Malformed Vega-Lite spec degrades visibly
- **WHEN** a stream emits a complete `houmao.graphic.vegalite` tool-call sequence with a malformed Vega-Lite spec
- **THEN** the workbench shows an invalid component fallback
- **AND THEN** the workbench does not crash or remove unrelated pane content

#### Scenario: Vega view is cleaned up
- **WHEN** a rendered Vega-Lite component rerenders, unmounts, or is cleared from the pane
- **THEN** the workbench finalizes or otherwise disposes the mounted Vega view
- **AND THEN** subsequent graphics can render in the same pane without leaking the prior view

### Requirement: Capabilities advertise Vega DSL as Layer 2
The AG-UI capabilities response SHALL advertise Layer 2 Vega DSL support in Houmao custom presentation metadata when the GUI target supports `houmao.graphic.vegalite`.

The metadata SHALL identify `houmao.graphic.vegalite`, supported Vega-Lite major versions, `vega-embed` as the browser renderer, disabled remote data policy, inline data support, optional Altair authoring, and whether Python preflight compilation is enabled.

Layer 1 template graphics metadata SHALL continue to report that raw Vega-Lite DSL specs are not part of `houmao.graphic.template`.

#### Scenario: Capabilities list Vega DSL separately from template graphics
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** Houmao custom presentation metadata includes a `vegaDsl` block for Layer 2
- **AND THEN** the Layer 2 block identifies `houmao.graphic.vegalite`
- **AND THEN** Layer 1 template metadata does not list Vega-Lite as a template renderer


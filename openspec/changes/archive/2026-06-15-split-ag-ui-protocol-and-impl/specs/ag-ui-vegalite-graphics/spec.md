## MODIFIED Requirements

### Requirement: Houmao defines Layer 2 Vega-Lite graphics
Houmao SHALL define a Layer 2 AG-UI implementation named `houmao.graphic.vegalite`.

The payload SHALL contain `schemaVersion`, `library`, `specVersion`, `title`, optional `description`, a raw Vega-Lite JSON object under `spec`, and optional display metadata.

The payload SHALL require `schemaVersion` equal to `1`, `library` equal to `vega-lite`, and `specVersion` equal to the supported Vega-Lite major version.

The implementation SHALL be separate from Layer 1 `houmao.graphic.template`; Layer 1 SHALL NOT use `renderer.preferred`, `renderer.fallback`, or `extra` fields to carry raw Vega-Lite specs.

#### Scenario: Vega-Lite implementation schema is discoverable
- **WHEN** an agent asks `houmao-mgr ag-ui impl schema houmao.graphic.vegalite`
- **THEN** the command returns the implementation name, schema version, JSON Schema-compatible payload shape, and a valid example
- **AND THEN** the command does not require a live gateway, passive server, or GUI

#### Scenario: Vega-Lite implementation stays separate from Layer 1
- **WHEN** an agent inspects Layer 2 implementation guidance
- **THEN** the guidance identifies `houmao.graphic.vegalite` as the raw Vega-Lite DSL implementation
- **AND THEN** it does not instruct the agent to place Vega-Lite specs in `houmao.graphic.template.extra`

### Requirement: Capabilities advertise Vega DSL as Layer 2
The AG-UI capabilities response SHALL advertise Layer 2 Vega DSL support in Houmao custom AG-UI implementation metadata when the GUI target supports `houmao.graphic.vegalite`.

The metadata SHALL identify `houmao.graphic.vegalite`, implementation category `freeform-graphics`, supported Vega-Lite major versions, `vega-embed` as the browser renderer, disabled remote data policy, inline data support, optional Altair authoring, and whether Python preflight compilation is enabled.

Layer 1 template graphics implementation metadata SHALL continue to report that raw Vega-Lite DSL specs are not part of `houmao.graphic.template`.

#### Scenario: Capabilities list Vega DSL separately from template graphics
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** Houmao custom implementation metadata includes a `houmao.graphic.vegalite` block for Layer 2
- **AND THEN** the Layer 2 block identifies `houmao.graphic.vegalite`
- **AND THEN** the Layer 2 block classifies it as `freeform-graphics`
- **AND THEN** Layer 1 template metadata does not list Vega-Lite as a template renderer

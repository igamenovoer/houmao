## ADDED Requirements

### Requirement: AG-UI capabilities advertise Layer 2 Vega-Lite support
The live per-agent gateway SHALL include Houmao custom presentation metadata for Layer 2 Vega-Lite graphics when the target supports typed graphics capability metadata.

The metadata SHALL identify `houmao.graphic.vegalite` as a Vega DSL tool name, list supported Vega-Lite major versions, identify `vega-embed` as the workbench renderer, report remote data loading as disabled by default, report inline data support, and report optional Python Altair authoring.

The metadata SHALL keep Layer 1 `templateGraphics` separate from Layer 2 `vegaDsl` and SHALL NOT list Vega-Lite as a Layer 1 template renderer.

#### Scenario: Capabilities include Vega DSL metadata
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes Houmao custom presentation metadata for `vegaDsl`
- **AND THEN** the metadata lists `houmao.graphic.vegalite` as a supported Layer 2 tool name
- **AND THEN** the metadata reports remote data loading as disabled by default

#### Scenario: Layer 1 metadata remains Plotly-only
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response's Layer 1 template graphics metadata lists Plotly as the template renderer
- **AND THEN** it does not list Vega-Lite as a Layer 1 renderer or fallback

### Requirement: AG-UI tool metadata includes Vega-Lite when generated graphics are enabled
When AG-UI tool metadata is advertised for generated graphics, the tools list SHALL include `houmao.graphic.vegalite` with a JSON parameter shape for the Layer 2 envelope.

When generated graphics are not enabled for a target, conservative capabilities SHALL continue to report tools as unsupported even though Houmao custom presentation metadata can describe the available component vocabulary.

#### Scenario: Headless capabilities list Vega-Lite tool metadata
- **WHEN** a caller requests capabilities for a target that reports generated graphics tool metadata
- **THEN** the tools list includes `houmao.graphic.vegalite`
- **AND THEN** the tool metadata identifies the required `schemaVersion`, `library`, `specVersion`, `title`, and `spec` fields

#### Scenario: Conservative target does not advertise callable tools
- **WHEN** a caller requests capabilities for a target that does not report generated graphics support
- **THEN** the standard tools capability remains unsupported
- **AND THEN** the response does not imply frontend tool execution is enabled

## MODIFIED Requirements

### Requirement: AG-UI capabilities report conservative attachment support
The gateway SHALL provide `GET /v1/ag-ui/capabilities` so GUI clients can discover supported AG-UI behavior before connecting or starting a run.

The capabilities response SHALL report HTTP SSE support, GUI connect support, text input parsing support, state snapshot support, and task-run submission as enabled when AG-UI run streaming is implemented for the live per-agent gateway.

The capabilities response SHALL report generated graphics support as enabled only when `houmao_render_graphic` artifact validation and event mapping are available for the target.

The capabilities response SHALL report resumable transport support as disabled for Houmao-published GUI events because the gateway does not replay retained `/v1/ag-ui/events` batches.

The capabilities response SHALL report state delta support, frontend tool execution, Open Generative UI, and unsupported multimodal input as disabled for this milestone.

The capabilities response SHALL identify that GUI lifecycle does not manage the Houmao agent lifecycle.

The Houmao metadata SHALL identify published-event delivery as live-only fanout with client-owned caching responsibility.

The Houmao metadata SHALL expose AG-UI protocol support separately from AG-UI implementation metadata.

The AG-UI protocol metadata SHALL identify standard event validation, tool-call event rendering, supported event output formats, and Houmao gateway publish semantics.

The AG-UI implementation metadata SHALL identify Houmao-known implementation tool names and SHALL state that frontend-specific implementation events can still be transported through AG-UI protocol commands even when Houmao does not validate their payload semantics.

The AG-UI implementation metadata SHALL group graphics-oriented implementation contracts under `templated-graphics`, `freeform-graphics`, and `new-component` categories.

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
- **AND THEN** the response identifies `houmao_render_graphic` in Houmao implementation metadata or tool capability metadata

#### Scenario: Capabilities report published-event delivery as non-resumable
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response reports resumable transport support as disabled for Houmao-published GUI events
- **AND THEN** Houmao metadata identifies `/v1/ag-ui/events` delivery as live-only fanout without gateway replay

#### Scenario: Capabilities remain conservative for unsupported features
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response reports state delta support as disabled
- **AND THEN** the response reports frontend tool execution as disabled
- **AND THEN** the response reports Open Generative UI as disabled
- **AND THEN** the response reports unsupported multimodal input as disabled

#### Scenario: Capabilities state that GUI does not own agent lifecycle
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response contains Houmao metadata indicating that the GUI does not manage the agent lifecycle

#### Scenario: Capabilities separate protocol and impl
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** Houmao custom metadata includes AG-UI protocol support metadata
- **AND THEN** Houmao custom metadata includes AG-UI implementation metadata
- **AND THEN** Houmao custom implementation metadata identifies `templated-graphics`, `freeform-graphics`, and `new-component` categories
- **AND THEN** Plotly, Vega-Lite, table, metric, and dashboard payload semantics appear under implementation metadata rather than protocol metadata

### Requirement: AG-UI capabilities advertise Layer 2 Vega-Lite support
The live per-agent gateway SHALL include Houmao custom AG-UI implementation metadata for Layer 2 Vega-Lite graphics when the target supports typed graphics capability metadata.

The metadata SHALL identify `houmao.graphic.vegalite` as a Vega-Lite implementation tool name, classify it under `freeform-graphics`, list supported Vega-Lite major versions, identify `vega-embed` as the workbench renderer, report remote data loading as disabled by default, report inline data support, and report optional Python Altair authoring.

The metadata SHALL keep the Layer 1 `houmao.graphic.template` implementation separate from the Layer 2 `houmao.graphic.vegalite` implementation and SHALL NOT list Vega-Lite as a Layer 1 template renderer.

#### Scenario: Capabilities include Vega-Lite implementation metadata
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response includes Houmao custom implementation metadata for `houmao.graphic.vegalite`
- **AND THEN** the metadata identifies `houmao.graphic.vegalite` as a supported Layer 2 implementation tool name
- **AND THEN** the metadata classifies it under `freeform-graphics`
- **AND THEN** the metadata reports remote data loading as disabled by default

#### Scenario: Layer 1 metadata remains Plotly-only
- **WHEN** a caller requests `GET /v1/ag-ui/capabilities`
- **THEN** the response's Layer 1 template graphics implementation metadata lists Plotly as the template renderer
- **AND THEN** the response classifies Layer 1 template graphics under `templated-graphics`
- **AND THEN** it does not list Vega-Lite as a Layer 1 renderer or fallback

### Requirement: AG-UI tool metadata includes Vega-Lite when generated graphics are enabled
When AG-UI tool metadata is advertised for generated graphics, the tools list SHALL include `houmao.graphic.vegalite` with a JSON parameter shape for the Layer 2 implementation envelope.

When generated graphics are not enabled for a target, conservative capabilities SHALL continue to report tools as unsupported even though Houmao custom implementation metadata can describe the available implementation vocabulary.

#### Scenario: Headless capabilities list Vega-Lite tool metadata
- **WHEN** a caller requests capabilities for a target that reports generated graphics tool metadata
- **THEN** the tools list includes `houmao.graphic.vegalite`
- **AND THEN** the tool metadata identifies the required `schemaVersion`, `library`, `specVersion`, `title`, and `spec` fields

#### Scenario: Conservative target does not advertise callable tools
- **WHEN** a caller requests capabilities for a target that does not report generated graphics support
- **THEN** the standard tools capability remains unsupported
- **AND THEN** the response does not imply frontend tool execution is enabled

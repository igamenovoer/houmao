## ADDED Requirements

### Requirement: Workbench template renderer override is separate from payload renderer selection
For completed `houmao.graphic.template` tool calls, the workbench GUI SHALL provide a local renderer override that chooses a specific supported renderer for presentation.

When no GUI override is active, the workbench SHALL preserve the payload-driven renderer selection behavior based on `renderer.preferred` and `renderer.fallback`.

When a GUI override is active, the workbench SHALL apply that override only to local presentation of the reconstructed component and SHALL NOT change the payload contract, Python authoring validation, gateway fanout semantics, capabilities metadata, or raw diagnostic evidence.

Forced renderer selection SHALL either render with the forced renderer or show a deterministic unsupported-renderer diagnostic. It SHALL NOT silently use payload fallback renderers for that forced-renderer attempt.

#### Scenario: No override uses payload renderer selection
- **WHEN** a completed `houmao.graphic.template` tool call contains `renderer.preferred` equal to `vega-lite` and `renderer.fallback` containing `recharts`
- **AND WHEN** the workbench pane has no forced renderer override
- **THEN** the workbench selects the renderer from the payload preference and fallback order

#### Scenario: GUI override changes presentation only
- **WHEN** a completed `houmao.graphic.template` tool call contains `renderer.preferred` equal to `vega-lite`
- **AND WHEN** the workbench pane forces the local template renderer to `recharts`
- **THEN** the workbench presents the component through Recharts when supported
- **AND THEN** message diagnostics, raw events, and reconstructed tool-call arguments still contain the original `vega-lite` payload preference

#### Scenario: Forced renderer does not use silent fallback
- **WHEN** a completed `houmao.graphic.template` tool call is shown in a pane with a forced renderer override
- **AND WHEN** the forced renderer is unavailable or unsupported for the payload
- **THEN** the workbench shows a deterministic unsupported-renderer diagnostic
- **AND THEN** the workbench does not silently render the component through another renderer from the payload fallback list

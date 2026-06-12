## ADDED Requirements

### Requirement: Workbench renders Layer 2 Vega-Lite components
The AG-UI workbench SHALL register a typed component renderer for `houmao.graphic.vegalite`.

The renderer SHALL use `vega`, `vega-lite`, and `vega-embed` to render accepted Vega-Lite specs in the browser.

The renderer SHALL disable remote data loading by default, disable renderer action controls by default, apply bounded responsive sizing, and clean up Vega view resources on rerender, unmount, pane clear, or target clear.

#### Scenario: Vega-Lite tool call renders in an agent pane
- **WHEN** an AG-UI pane receives a complete `houmao.graphic.vegalite` tool-call sequence with a valid inline Vega-Lite spec
- **THEN** the pane renders a visible Vega-Lite chart
- **AND THEN** normal transcript, tool-call, and raw-event diagnostics remain available

#### Scenario: Invalid Vega-Lite tool call shows fallback
- **WHEN** an AG-UI pane receives a complete `houmao.graphic.vegalite` tool-call sequence whose payload is malformed or rejected by browser validation
- **THEN** the pane shows a deterministic invalid component fallback
- **AND THEN** unrelated transcript and graphics content remain visible

#### Scenario: Clear canvas disposes Vega view
- **WHEN** a pane displays a rendered Vega-Lite chart
- **AND WHEN** the user activates clear-canvas for that pane
- **THEN** the chart is removed from visible state
- **AND THEN** the workbench disposes the mounted Vega view without stopping or detaching the target

### Requirement: Workbench keeps Vega-Lite separate from Layer 1 renderer selection
The workbench SHALL NOT reintroduce a Layer 1 template renderer selector for Vega-Lite.

The workbench SHALL render `houmao.graphic.template` through the existing Plotly Layer 1 path and SHALL render `houmao.graphic.vegalite` through the Layer 2 Vega-Lite path.

#### Scenario: Template graphics still use Plotly
- **WHEN** a pane receives a valid `houmao.graphic.template` payload
- **THEN** the workbench renders it through the Plotly template renderer
- **AND THEN** the workbench does not route it through the Vega-Lite renderer

#### Scenario: Vega-Lite graphics use Layer 2 renderer
- **WHEN** a pane receives a valid `houmao.graphic.vegalite` payload
- **THEN** the workbench renders it through the Vega-Lite renderer
- **AND THEN** the workbench does not require or inspect a Layer 1 `renderer.preferred` value

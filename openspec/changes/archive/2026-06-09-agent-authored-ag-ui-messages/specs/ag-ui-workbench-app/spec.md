## ADDED Requirements

### Requirement: Workbench renders Houmao typed components from standard AG-UI events
The workbench SHALL render known Houmao typed components carried by standard AG-UI tool-call or custom events.

The renderer registry SHALL be keyed by component or tool-call name.

The initial renderer registry SHALL support `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

The workbench SHALL preserve unknown component events as visible raw tool-call or custom-event records rather than failing the pane.

The workbench SHALL continue to render existing `houmao_render_graphic` events through the same rendering path or a compatibility registry entry.

#### Scenario: Bar chart tool call renders visibly
- **WHEN** a stream emits a complete AG-UI tool-call sequence with `toolCallName` equal to `houmao.chart.bar`
- **AND WHEN** the tool-call args validate as a `houmao.chart.bar` payload
- **THEN** the pane renders a visible bar chart with the provided title, labels, and values

#### Scenario: Dashboard event renders contained components
- **WHEN** a stream emits a valid `houmao.dashboard` component payload containing chart and metric-grid children
- **THEN** the pane renders the dashboard layout
- **AND THEN** the child components render through their registered component renderers

#### Scenario: Unknown component remains inspectable
- **WHEN** a stream emits a complete AG-UI tool call with an unknown `toolCallName`
- **THEN** the pane keeps the raw tool-call record visible
- **AND THEN** the pane does not crash or hide the event timeline

### Requirement: Workbench validates component payloads before rendering
The workbench SHALL defensively validate known Houmao component payloads before rendering them.

Invalid known-component payloads SHALL render a deterministic unsupported or invalid-component placeholder.

The placeholder SHALL preserve enough raw event detail for debugging.

The workbench SHALL NOT render raw unsanitized HTML, scriptable SVG, iframe content, or JavaScript URLs from component payloads.

#### Scenario: Invalid chart payload degrades visibly
- **WHEN** a stream emits `houmao.chart.line` with malformed series data
- **THEN** the pane renders an invalid-component placeholder
- **AND THEN** the raw tool-call args remain available in the event timeline or tool-call detail

#### Scenario: Unsafe inline content is not rendered
- **WHEN** a component payload contains raw HTML or scriptable SVG content
- **THEN** the pane does not inject that content into the DOM
- **AND THEN** the pane shows a deterministic unsupported-content placeholder

### Requirement: Workbench renderer tests cover dashboard-style graphics
The repository SHALL include deterministic workbench browser coverage for the Houmao typed component registry.

The browser fixture SHALL emit at least one chart component, one table or metric-grid component, one dashboard component, and one unknown component over AG-UI event streams.

The test SHALL verify visible chart/dashboard evidence and fallback behavior for unknown or invalid components.

#### Scenario: E2E fixture renders typed components
- **WHEN** the workbench E2E suite runs against the deterministic AG-UI fixture
- **THEN** it verifies visible evidence for a Houmao chart component
- **AND THEN** it verifies visible evidence for a dashboard or metric-grid component

#### Scenario: E2E fixture verifies fallback
- **WHEN** the deterministic fixture emits an unknown component name
- **THEN** the E2E test verifies that the raw tool-call or custom-event record remains visible
- **AND THEN** the pane continues processing later AG-UI events

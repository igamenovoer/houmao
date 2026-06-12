## ADDED Requirements

### Requirement: Workbench has no Recharts runtime dependency
The AG-UI workbench SHALL NOT depend on Recharts for chart rendering.

The workbench frontend SHALL NOT import from the `recharts` package.

The workbench dependency manifest SHALL NOT list `recharts` after template graphics and supported typed component rendering no longer require it.

The deterministic browser tests SHALL NOT use Recharts-specific DOM selectors as evidence of successful chart rendering.

#### Scenario: Dependency manifest omits Recharts
- **WHEN** a developer inspects the workbench package manifest after this change
- **THEN** the manifest does not list `recharts` as a dependency or dev dependency
- **AND THEN** chart rendering tests still pass with Plotly-backed evidence

#### Scenario: Source does not import Recharts
- **WHEN** a developer searches the workbench source after this change
- **THEN** no workbench runtime module imports from `recharts`
- **AND THEN** template graphics and supported typed components still render visibly

## MODIFIED Requirements

### Requirement: Workbench renders Houmao typed components from standard AG-UI events
The workbench SHALL render known Houmao typed components carried by standard AG-UI tool-call or custom events.

The renderer registry SHALL be keyed by component or tool-call name.

The initial renderer registry SHALL support `houmao.graphic.template`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

The renderer registry SHALL NOT register `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie` after those fixed chart APIs are retired.

The workbench SHALL preserve unknown component events as visible raw tool-call or custom-event records rather than failing the pane.

The workbench SHALL continue to render existing `houmao_render_graphic` events through the same rendering path or a compatibility registry entry.

#### Scenario: Plotly template chart tool call renders visibly
- **WHEN** a stream emits a complete AG-UI tool-call sequence with `toolCallName` equal to `houmao.graphic.template`
- **AND WHEN** the tool-call args validate as a Plotly-backed schema version `2` chart payload
- **THEN** the pane renders a visible chart with the provided title, traces, labels, and values
- **AND THEN** the rendered evidence does not require a Recharts DOM node or Recharts-specific selector

#### Scenario: Retired fixed chart tool call remains inspectable
- **WHEN** a stream emits a complete AG-UI tool-call sequence with `toolCallName` equal to `houmao.chart.bar`
- **THEN** the pane shows a visible unknown or unsupported component fallback
- **AND THEN** the raw tool-call record remains inspectable
- **AND THEN** the pane does not try to render the payload through Recharts or a hidden legacy chart adapter

#### Scenario: Dashboard event renders contained components
- **WHEN** a stream emits a valid `houmao.dashboard` component payload containing `houmao.graphic.template` and metric-grid children
- **THEN** the pane renders the dashboard layout
- **AND THEN** the child template chart renders through Plotly-backed registered component renderers

#### Scenario: Unknown component remains inspectable
- **WHEN** a stream emits a complete AG-UI tool call with an unknown `toolCallName`
- **THEN** the pane keeps the raw tool-call record visible
- **AND THEN** the pane does not crash or hide the event timeline

### Requirement: Workbench tests cover pane presentation behavior
The deterministic workbench browser coverage SHALL exercise Plotly-backed template graphic rendering, retired fixed-chart fallback behavior, datasource-bound template rendering, visible renderer diagnostics, and tmux terminal repaint behavior.

Chart rendering coverage SHALL verify Plotly-backed visible evidence without relying on Recharts-specific DOM selectors.

Tmux repaint coverage SHALL attach to a deterministic tmux bridge fixture, create enough terminal output to scroll, perform mouse-wheel scrolling, and verify that the terminal remains visibly updated without forcing an outer window resize.

#### Scenario: E2E validates Plotly-backed chart presentation
- **WHEN** the workbench E2E suite emits completed `houmao.graphic.template` tool calls for an agent pane
- **THEN** the test verifies Plotly-backed visible evidence for the template chart
- **AND THEN** the raw tool-call diagnostics still expose the original payloads

#### Scenario: E2E validates retired fixed chart fallback
- **WHEN** the workbench E2E suite emits a completed `houmao.chart.bar` tool call for an agent pane
- **THEN** the test verifies visible unknown or unsupported component evidence
- **AND THEN** the test verifies that no Recharts-specific DOM selector is required

#### Scenario: E2E validates tmux scroll repaint
- **WHEN** the workbench E2E suite attaches a tmux tab through the deterministic tmux bridge fixture
- **AND WHEN** the test scrolls the terminal viewport with the mouse wheel
- **THEN** the test verifies that terminal content remains visibly refreshed without resizing the browser window

## REMOVED Requirements

### Requirement: Agent panes expose a template graphic renderer override
**Reason**: Layer 1 now has one renderer, Plotly, and the workbench is retiring Recharts completely. A renderer override control would expose choices that no longer exist.

**Migration**: Remove the pane-level renderer override UI and render `houmao.graphic.template` through Plotly. Legacy stored override values SHALL be ignored or sanitized to the Plotly default.

### Requirement: Template renderer preference persists as safe pane metadata
**Reason**: The renderer preference exists only to support the removed multi-renderer override control.

**Migration**: Remove persisted template renderer preference from the active pane presentation model. Existing stored values such as `auto`, `vega-lite`, and `recharts` SHALL NOT affect rendering after this change.

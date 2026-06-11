## ADDED Requirements

### Requirement: Agent panes expose a template graphic renderer override
Agent panes SHALL provide a pane-level control for choosing how `houmao.graphic.template` tool calls are rendered.

The control SHALL expose at least `auto`, `vega-lite`, and `recharts` options.

When the value is `auto`, the workbench SHALL use the renderer selection encoded in the received template graphic payload.

When the value is a renderer id such as `vega-lite` or `recharts`, the workbench SHALL attempt to render completed `houmao.graphic.template` tool calls in that pane with the selected renderer before considering message-level renderer preference.

The renderer override SHALL be presentation metadata only. The workbench SHALL NOT mutate the received AG-UI events, reconstructed tool-call arguments, diagnostics payloads, or gateway messages to apply the override.

#### Scenario: Auto respects message renderer selection
- **WHEN** an agent pane renderer control is set to `auto`
- **AND WHEN** a completed `houmao.graphic.template` tool call requests `renderer.preferred` equal to `vega-lite`
- **THEN** the workbench selects the renderer through the message-level renderer preference and fallback rules
- **AND THEN** the raw tool-call diagnostics still show the original message payload

#### Scenario: Forced renderer overrides message preference
- **WHEN** an agent pane renderer control is set to `recharts`
- **AND WHEN** a completed `houmao.graphic.template` tool call requests `renderer.preferred` equal to `vega-lite`
- **THEN** the workbench renders that template graphic through Recharts when Recharts supports the payload
- **AND THEN** the raw tool-call diagnostics still show `renderer.preferred` equal to `vega-lite`

#### Scenario: Unsupported forced renderer degrades visibly
- **WHEN** an agent pane renderer control is set to a renderer that cannot render the completed template graphic payload
- **THEN** the workbench shows a deterministic renderer-override diagnostic in the pane
- **AND THEN** the workbench does not silently fall back to another renderer for that forced-renderer attempt
- **AND THEN** unrelated pane messages and rendered components remain visible

### Requirement: Template renderer preference persists as safe pane metadata
The workbench SHALL persist each agent pane's template graphic renderer preference in the same safe browser configuration boundary as pane layout and target metadata.

The persisted renderer preference SHALL default to `auto` when absent, invalid, or unsupported by the current workbench build.

The persisted renderer preference SHALL NOT include AG-UI stream content, tool-call payloads, transcript text, prompt text, raw terminal bytes, gateway response bodies, credentials, cookies, bearer tokens, or authorization headers.

#### Scenario: Renderer preference restores after reload
- **WHEN** a tester sets pane `agent-1` to force the `vega-lite` template renderer
- **AND WHEN** the browser reloads the workbench
- **THEN** pane `agent-1` restores the `vega-lite` renderer preference
- **AND THEN** the restored localStorage state does not contain prior template graphic payloads or AG-UI stream content

#### Scenario: Invalid stored renderer falls back to auto
- **WHEN** localStorage contains an unsupported template renderer preference for pane `agent-1`
- **AND WHEN** the workbench loads that pane
- **THEN** the pane uses `auto` as its template renderer preference
- **AND THEN** the invalid stored value does not prevent the pane from rendering AG-UI messages

### Requirement: Tmux terminal panes repaint after scroll and layout-local changes
Tmux panes SHALL keep xterm `Terminal`, `FitAddon`, DOM refs, and direct terminal rendering outside reduced runtime state while ensuring the full visible terminal area repaints after local terminal viewport changes.

Tmux panes SHALL schedule a visible-row xterm refresh after local scroll events, parsed terminal writes, successful fit operations, Dockview dimension or visibility changes, and terminal host resize observations.

Tmux panes SHALL continue to send tmux resize messages to the runtime only when the fitted terminal column or row count changes.

The repaint behavior SHALL NOT persist terminal bytes in reduced runtime state or localStorage.

#### Scenario: Mouse scroll repaints full terminal width
- **WHEN** a tmux pane is attached to a session with enough scrollback for mouse-wheel scrolling
- **AND WHEN** the tester scrolls the xterm viewport with the mouse wheel
- **THEN** the visible terminal rows repaint across the full terminal width without requiring an outer browser-window resize
- **AND THEN** the workbench does not store terminal bytes in reduced runtime state

#### Scenario: Same-size layout refresh does not send redundant tmux resize
- **WHEN** a Dockview layout or visibility event causes the tmux pane to refit at the same terminal columns and rows
- **THEN** the pane refreshes the visible terminal area
- **AND THEN** the runtime does not receive a redundant tmux resize action solely because the repaint ran

#### Scenario: Real resize still updates tmux attachment size
- **WHEN** a tmux pane is attached to a session
- **AND WHEN** the browser or Dockview panel changes the visible terminal host size enough to change fitted columns or rows
- **THEN** the pane sends the updated terminal columns and rows to the runtime attachment
- **AND THEN** the visible terminal area repaints after the fit

### Requirement: Workbench tests cover pane presentation behavior
The deterministic workbench browser coverage SHALL exercise template graphic renderer override behavior and tmux terminal repaint behavior.

Renderer override coverage SHALL verify `auto`, forced `vega-lite`, forced `recharts`, and visible forced-renderer diagnostics using deterministic AG-UI fixture events.

Tmux repaint coverage SHALL attach to a deterministic tmux bridge fixture, create enough terminal output to scroll, perform mouse-wheel scrolling, and verify that the terminal remains visibly updated without forcing an outer window resize.

#### Scenario: E2E validates template renderer override
- **WHEN** the workbench E2E suite emits a completed `houmao.graphic.template` tool call for an agent pane
- **AND WHEN** the test switches the pane renderer control between `auto`, `vega-lite`, and `recharts`
- **THEN** the test verifies the renderer-specific visible evidence for the selected mode
- **AND THEN** the raw tool-call diagnostics still expose the original payload

#### Scenario: E2E validates tmux scroll repaint
- **WHEN** the workbench E2E suite attaches a tmux tab through the deterministic tmux bridge fixture
- **AND WHEN** the test scrolls the terminal viewport with the mouse wheel
- **THEN** the test verifies that terminal content remains visibly refreshed without resizing the browser window

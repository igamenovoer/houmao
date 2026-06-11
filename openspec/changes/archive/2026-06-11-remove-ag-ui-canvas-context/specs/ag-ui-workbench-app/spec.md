## MODIFIED Requirements

### Requirement: Workbench run requests minimize agent-visible metadata
For normal agent pane prompt submissions, including operator-designated panes, the workbench SHALL submit AG-UI `RunAgentInput` requests with only protocol-required routing fields, the user message, an empty tools array, an empty state object, an empty context array, and an empty forwarded props object.

The workbench SHALL NOT include GUI-derived layout measurements in `RunAgentInput.context`, including `houmao.canvas_size_px.v1`, `houmao.canvas.v1`, pane dimensions, display surface dimensions, transcript dimensions, renderer dimensions, scroll state, or any equivalent canvas-size hint.

The workbench SHALL NOT measure the visible graphics surface as part of normal prompt submission.

The workbench SHALL NOT duplicate pane id, pane kind, source labels, component schemas, CLI command recipes, agent identity, thread id, run id, delivery semantics, or safety guidance in `state`, `context`, or non-Houmao `forwardedProps` for normal prompt submissions.

The workbench SHALL use `forwardedProps.houmao` only for explicit gateway-recognized runtime controls when a future caller intentionally requests those controls.

#### Scenario: Prompt run uses empty context despite available surface size
- **WHEN** an agent pane submits a text prompt while the visible graphics surface measures 640 by 520 CSS pixels
- **THEN** the submitted `RunAgentInput.context` is an empty array
- **AND THEN** the submitted request does not include `houmao.canvas_size_px.v1`, `houmao.canvas.v1`, width, height, pane, display surface, transcript, renderer, or scroll-state measurements

#### Scenario: Prompt run omits redundant pane metadata
- **WHEN** an agent pane submits a normal text prompt
- **THEN** the submitted `RunAgentInput.state` is an empty object
- **AND THEN** the submitted `RunAgentInput.forwardedProps` is an empty object
- **AND THEN** the submitted request does not include pane id, pane kind, source label, agent identity, thread id duplicate, or run id duplicate outside the standard AG-UI routing fields

#### Scenario: Prompt run keeps typed graphics out of declared tools
- **WHEN** an agent pane submits a normal text prompt intended to produce Houmao typed graphics
- **THEN** the submitted `RunAgentInput.tools` is an empty array
- **AND THEN** the request does not declare `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard` as frontend tools

#### Scenario: Pane layout changes do not alter agent-visible context
- **WHEN** an agent pane is resized, scrolled, cleared, or rendered with a different graphics backend before submitting a text prompt
- **THEN** the submitted `RunAgentInput.context` remains an empty array
- **AND THEN** the workbench does not send guessed, measured, or cached canvas width or height values

### Requirement: Agent panes delegate AG-UI lifecycles to runtime
Agent panes SHALL delegate long-lived AG-UI lifecycle ownership to the workbench runtime.

Agent panes SHALL dispatch runtime actions for target changes, connect/watch requests, run requests, stream cancellation, clear-canvas requests, and pane disposal.

Agent panes SHALL keep UI-local concerns such as prompt editor state, target form editing, display DOM refs, and rendered DOM outside the runtime lifecycle effects.

Agent panes SHALL NOT keep component-local reconnect timers, stream abort refs, connection ids, or duplicated connect/run status after the equivalent workflow has moved into the runtime.

#### Scenario: Agent pane connect uses runtime action
- **WHEN** a user connects an agent pane to a target
- **THEN** the pane dispatches a runtime connect or watch action for that target
- **AND THEN** runtime effects own passive resolution, AG-UI connect stream startup, reconnect behavior, and detach cleanup

#### Scenario: Agent pane run uses runtime action
- **WHEN** a user submits a prompt from an agent pane
- **THEN** the pane dispatches a runtime run action containing the submitted message and target only
- **AND THEN** the runtime run action does not contain canvas size, pane dimensions, display surface dimensions, renderer dimensions, or scroll-state measurements
- **AND THEN** runtime effects own the AG-UI run stream and reduce the received events into pane-visible state

#### Scenario: Pane close cancels pane-owned AG-UI streams
- **WHEN** an agent pane with a live pane-owned run stream closes
- **THEN** the pane dispatches disposal to the runtime
- **AND THEN** runtime effects abort that pane-owned stream without stopping watched-target listeners still required by storage state

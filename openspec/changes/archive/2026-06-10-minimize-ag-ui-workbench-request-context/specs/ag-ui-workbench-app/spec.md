## ADDED Requirements

### Requirement: Workbench run requests minimize agent-visible metadata
For normal operator and agent pane prompt submissions, the workbench SHALL submit AG-UI `RunAgentInput` requests with only protocol-required routing fields, the user message, an empty tools array, an empty state object, an empty forwarded props object, and at most one compact canvas context entry.

When a positive visible graphics surface size is available, the workbench SHALL include one context entry with `description` equal to `houmao.canvas_size_px.v1` and `value` equal to a compact JSON string containing integer `widthPx` and `heightPx` fields in CSS pixels.

When no positive visible graphics surface size is available, the workbench SHALL omit the canvas context entry rather than inventing a default size.

The workbench SHALL NOT duplicate pane id, pane kind, source labels, component schemas, CLI command recipes, agent identity, thread id, run id, delivery semantics, or safety guidance in `state`, `context`, or non-Houmao `forwardedProps` for normal prompt submissions.

The workbench MAY still use `forwardedProps.houmao` for explicit gateway-recognized runtime controls when a future caller intentionally requests those controls.

#### Scenario: Prompt run includes only compact canvas context
- **WHEN** an operator or agent pane submits a text prompt and the visible graphics surface measures 640 by 520 CSS pixels
- **THEN** the submitted `RunAgentInput.context` contains exactly one Houmao presentation entry
- **AND THEN** that entry has `description` equal to `houmao.canvas_size_px.v1`
- **AND THEN** that entry has `value` equal to `{"widthPx":640,"heightPx":520}` or an equivalent compact JSON string with those integer fields

#### Scenario: Prompt run omits redundant pane metadata
- **WHEN** an operator or agent pane submits a normal text prompt
- **THEN** the submitted `RunAgentInput.state` is an empty object
- **AND THEN** the submitted `RunAgentInput.forwardedProps` is an empty object
- **AND THEN** the submitted request does not include pane id, pane kind, source label, agent identity, thread id duplicate, or run id duplicate outside the standard AG-UI routing fields

#### Scenario: Prompt run keeps typed graphics out of declared tools
- **WHEN** an operator or agent pane submits a normal text prompt intended to produce Houmao typed graphics
- **THEN** the submitted `RunAgentInput.tools` is an empty array
- **AND THEN** the request does not declare `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, `houmao.table`, `houmao.metric_grid`, or `houmao.dashboard` as frontend tools

#### Scenario: Missing surface size omits canvas context
- **WHEN** an operator or agent pane submits a text prompt before a positive visible graphics surface size can be measured
- **THEN** the submitted `RunAgentInput.context` does not include `houmao.canvas_size_px.v1`
- **AND THEN** the workbench does not send guessed width or height values

### Requirement: Workbench connect requests do not send redundant GUI metadata
For AG-UI connect requests that attach or watch a target without submitting prompt work, the workbench SHALL avoid sending pane/source metadata through agent-visible fields.

Connect requests SHALL use empty `state`, empty `context`, empty `tools`, and empty non-Houmao `forwardedProps` unless a future gateway-recognized control explicitly requires otherwise.

#### Scenario: Connect request is metadata-minimal
- **WHEN** an operator, agent, watched-target, or Debug Agent pane opens an AG-UI connect stream
- **THEN** the submitted connect input has empty `state`, `context`, `tools`, and `forwardedProps`
- **AND THEN** it does not include pane id, pane kind, or source label in the request body

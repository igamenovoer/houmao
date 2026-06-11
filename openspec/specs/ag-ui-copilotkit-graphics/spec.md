# ag-ui-copilotkit-graphics Specification

## Purpose
TBD - created by archiving change add-ag-ui-run-streaming-graphics. Update Purpose after archive.
## Requirements
### Requirement: Graphics artifacts are explicit and validated

Houmao SHALL define a typed AG-UI graphics artifact payload for CopilotKit rendering.

The graphics payload SHALL include `title`, `description`, `format`, `content`, `contentUrl`, `altText`, and `metadata` fields, with nullable fields allowed only where the schema permits them.

The supported initial formats SHALL be `svg`, `html_fragment`, `image_url`, `image_data_uri`, and `chart_json`.

The graphics validator SHALL reject unsupported formats and unsafe inline content before emitting AG-UI tool-call events.

The graphics mapper SHALL recognize explicit structured Houmao graphics artifacts and SHALL NOT scrape arbitrary Markdown as a graphics source.

#### Scenario: Supported graphics formats validate

- **WHEN** the graphics validator receives artifacts with formats `svg`, `html_fragment`, `image_url`, `image_data_uri`, and `chart_json`
- **AND WHEN** each artifact satisfies the safety rules for its format
- **THEN** each artifact is accepted as a typed Houmao graphics artifact

#### Scenario: Unsupported graphics format is rejected

- **WHEN** the graphics validator receives an artifact with an unsupported `format`
- **THEN** validation fails before any AG-UI graphics event is emitted

#### Scenario: Unsafe inline graphics content is rejected

- **WHEN** the graphics validator receives inline SVG or HTML fragment content containing scripts, event handler attributes, or unsafe URLs
- **THEN** validation fails before any AG-UI graphics event is emitted

#### Scenario: Markdown is not scraped for graphics

- **WHEN** assistant text contains Markdown image links, code fences, or HTML snippets
- **THEN** the graphics mapper does not emit `houmao_render_graphic` unless a structured Houmao graphics artifact is present

### Requirement: Graphics stream as CopilotKit-compatible tool calls

The AG-UI graphics mapper SHALL emit each validated graphics artifact as a complete tool-call sequence named `houmao_render_graphic`.

The tool-call sequence SHALL include `TOOL_CALL_START`, one or more `TOOL_CALL_ARGS`, and `TOOL_CALL_END`.

The tool-call sequence SHALL include `TOOL_CALL_RESULT` with a compact normalized artifact summary when a result message is configured or available.

The `TOOL_CALL_START` event SHALL include `parentMessageId` for an assistant message.

When no assistant message is currently open, the mapper SHALL create an assistant text message context before emitting the graphics tool call.

#### Scenario: Graphics artifact emits tool-call sequence

- **WHEN** the mapper receives a validated graphics artifact
- **THEN** it emits `TOOL_CALL_START` with `toolCallName` equal to `houmao_render_graphic`
- **AND THEN** it emits `TOOL_CALL_ARGS` containing JSON arguments that match the validated artifact payload
- **AND THEN** it emits `TOOL_CALL_END`

#### Scenario: Graphics tool call is attached to assistant message

- **WHEN** the mapper emits a `houmao_render_graphic` tool call
- **THEN** `TOOL_CALL_START` includes `parentMessageId`
- **AND THEN** the parent message id belongs to an assistant message in the same AG-UI stream
- **AND THEN** a CopilotKit-style message reconstruction can place the tool call in the assistant message `toolCalls` list

#### Scenario: Graphics result is emitted when enabled

- **WHEN** a validated graphics artifact includes a result summary or the mapper is configured to emit one
- **THEN** the mapper emits `TOOL_CALL_RESULT`
- **AND THEN** the result event references the same tool call id as the graphics tool-call sequence

### Requirement: Graphics capability metadata supports CopilotKit renderers

The AG-UI capabilities response SHALL describe generated graphics support when `houmao_render_graphic` mapping is enabled.

The repository SHALL provide a small CopilotKit renderer fixture or example that registers `useRenderTool({ name: "houmao_render_graphic" })`.

The renderer fixture SHALL demonstrate how a CopilotKit GUI can render the typed Houmao graphics payload from streamed AG-UI tool-call arguments.

#### Scenario: Capabilities expose graphics tool name

- **WHEN** a caller requests `GET /v1/ag-ui/capabilities` for a target with graphics mapping enabled
- **THEN** the response reports generated graphics support
- **AND THEN** the response exposes `houmao_render_graphic` as the Houmao graphics tool name in metadata

#### Scenario: Renderer fixture targets the graphics tool

- **WHEN** the CopilotKit renderer fixture is inspected
- **THEN** it registers `useRenderTool({ name: "houmao_render_graphic" })`
- **AND THEN** it reads the typed graphics payload from tool-call arguments

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

# houmao-ext-graphing-skill Specification

## Purpose
TBD - created by archiving change rename-graphing-extension-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao packages a graphing extension system skill
The system SHALL package a Houmao-owned system skill named `houmao-ext-graphing` under the maintained system-skill asset root.

The skill SHALL teach agents how to author built-in Houmao graphing payloads carried over AG-UI implementation events.

The skill SHALL identify `templated-graphics` as the built-in Layer 1 graphing category and SHALL identify its current concrete implementation as Plotly.js-backed `houmao.graphic.template`.

The skill SHALL identify `freeform-graphics` as the built-in higher-freedom graphing category and SHALL identify its current concrete implementation as Vega-Lite-backed `houmao.graphic.vegalite`.

The skill SHALL be installable through the Houmao system-skill catalog as an extension skill.

#### Scenario: Installed graphing extension explains its scope
- **WHEN** an agent opens the installed `houmao-ext-graphing` skill
- **THEN** the skill states that it authors built-in Houmao graphing payloads
- **AND THEN** it identifies Plotly.js template graphics and Vega-Lite freeform graphics as the current built-in graphing flavors
- **AND THEN** it does not present itself as the AG-UI gateway lifecycle or message delivery skill

#### Scenario: System-skill catalog includes the graphing extension
- **WHEN** an operator lists maintained Houmao system skills
- **THEN** `houmao-ext-graphing` appears as an installable Houmao-owned skill
- **AND THEN** it is described as a graphing extension skill rather than as a managed-agent lifecycle skill or utility skill

### Requirement: Graphing extension provides graphing schema discovery workflows
The `houmao-ext-graphing` skill SHALL instruct agents to discover supported built-in graphing schemas through maintained `houmao-mgr ag-ui impl` surfaces.

The skill SHALL instruct agents to use `houmao-mgr ag-ui impl templated-graphics list` to list supported `templated-graphics` schemas.

The skill SHALL instruct agents to use `houmao-mgr ag-ui impl freeform-graphics list` to list supported `freeform-graphics` schemas.

The skill SHALL instruct agents to use `houmao-mgr ag-ui impl schema houmao.graphic.template` and `houmao-mgr ag-ui impl schema houmao.graphic.vegalite` before authoring unfamiliar graphing payloads.

The skill SHALL instruct agents to use `houmao-mgr ag-ui impl catalog houmao.graphic.template traces` when they need supported and excluded Plotly trace information.

The skill SHALL NOT instruct agents to infer schema names from Plotly trace names such as `bar`, `heatmap`, or `sankey`.

#### Scenario: Agent lists built-in graphing schemas by layer
- **WHEN** an agent needs to know which graphing schemas Houmao supports
- **THEN** the graphing extension tells it to run `houmao-mgr ag-ui impl templated-graphics list`
- **AND THEN** it tells the agent to run `houmao-mgr ag-ui impl freeform-graphics list`
- **AND THEN** it does not tell the agent to treat Plotly trace names as standalone schema names

#### Scenario: Agent checks Plotly trace catalog coverage
- **WHEN** an agent wants to emit an uncommon Plotly 2D trace family
- **THEN** the graphing extension tells it to inspect `houmao-mgr ag-ui impl catalog houmao.graphic.template traces`
- **AND THEN** it tells the agent to validate the payload before rendering AG-UI events

### Requirement: Graphing extension teaches Plotly.js templated graphics authoring
The `houmao-ext-graphing` skill SHALL teach agents to prefer `houmao.graphic.template` for supported Plotly.js 2D snapshot charts and chart-like visualizations that fit the Layer 1 trace catalog.

The skill SHALL teach agents that `houmao.graphic.template` uses schema version `3`, `figureType: "plotly2d"`, and `traces[].type`.

The skill SHALL tell agents that the current Layer 1 renderer is Plotly.js and that agents do not need to choose among Layer 1 renderers.

The skill SHALL tell agents to use inline `traces[].data` for visible one-off charts unless capabilities explicitly advertise datasource materialization support.

The skill SHALL tell agents that datasource bindings use catalog field paths such as `data.x`, `data.y`, `data.open`, `data.high`, `data.low`, `data.close`, `data.node.label`, `data.link.value`, `data.header.values`, and `data.cells.values`.

The skill SHALL state that Layer 1 does not accept Vega-Lite renderer ids, fallback renderer lists, raw Plotly replacement specs, JavaScript, HTML, iframes, remote URLs, 3D scene traces, or `extra.vega-lite`.

#### Scenario: Agent keeps supported Plotly 2D charts on Layer 1
- **WHEN** an agent needs an ordinary supported Plotly 2D chart with inline data, such as a heatmap, box plot, violin plot, polar chart, financial chart, treemap, table, or Sankey diagram
- **THEN** the graphing extension directs it to prefer `houmao.graphic.template`
- **AND THEN** it does not direct the agent to use Vega-Lite only because Layer 2 exists

#### Scenario: Agent avoids Vega-Lite inside Layer 1
- **WHEN** an agent has a raw Vega-Lite spec
- **THEN** the graphing extension tells it not to place that spec in `houmao.graphic.template.extra`
- **AND THEN** it directs the agent to `houmao.graphic.vegalite`

### Requirement: Graphing extension teaches Vega-Lite freeform graphics authoring
The `houmao-ext-graphing` skill SHALL teach agents that `houmao.graphic.vegalite` is the built-in `freeform-graphics` path for custom declarative Vega-Lite graphics.

The skill SHALL explain that agents may hand-author Vega-Lite JSON or optionally use Python Altair to generate the Vega-Lite `spec` with `chart.to_dict()` or `chart.to_json()`.

The skill SHALL state that agents send the resulting JSON object in a `houmao.graphic.vegalite` payload and SHALL NOT send Python source code, notebook state, pandas objects, Altair objects, or code that expects the gateway or workbench to execute Python.

The skill SHALL teach agents to use Vega-Lite when the requested graphic needs custom declarative structure, layering, encodings, transforms, selections, linked views, or chart shapes outside the Layer 1 Plotly.js trace catalog.

#### Scenario: Agent chooses Vega-Lite for custom declarative graphics
- **WHEN** an agent needs a layered, interactive, or custom chart structure that does not fit Layer 1 template graphics
- **THEN** the graphing extension directs it to inspect and use `houmao.graphic.vegalite`
- **AND THEN** it tells the agent to validate and render the payload before publishing

#### Scenario: Agent uses Altair only as an authoring helper
- **WHEN** an agent uses Python Altair to build a chart
- **THEN** the graphing extension tells it to send `chart.to_dict()` or equivalent Vega-Lite JSON
- **AND THEN** it does not tell the agent to send Python code or rely on runtime Python execution by the gateway or workbench

### Requirement: Graphing extension validates and renders graphing payloads before delivery
The `houmao-ext-graphing` skill SHALL instruct agents to validate graphing payloads with `houmao-mgr ag-ui impl validate <implementation> --input <payload>`.

The skill SHALL instruct agents to render validated graphing payloads with `houmao-mgr ag-ui impl render <implementation> --input <payload>`.

The skill SHALL instruct agents to validate rendered event batches with `houmao-mgr ag-ui protocol events validate --input <events>`.

The skill SHALL tell agents that delivery to the Houmao gateway belongs to the AG-UI interop or gateway workflow after events have been rendered and validated.

The skill SHALL NOT instruct agents to publish raw graphing payloads directly to the gateway.

#### Scenario: Agent validates and renders a Plotly template payload
- **WHEN** an agent has authored a `houmao.graphic.template` payload
- **THEN** the graphing extension tells it to validate the payload through `houmao-mgr ag-ui impl validate houmao.graphic.template`
- **AND THEN** it tells the agent to render standard AG-UI events through `houmao-mgr ag-ui impl render houmao.graphic.template`
- **AND THEN** it does not tell the agent to publish the raw template payload

#### Scenario: Agent hands rendered events to interop delivery
- **WHEN** an agent has a validated AG-UI event batch produced from a graphing payload
- **THEN** the graphing extension points to the AG-UI interop or gateway workflow for Houmao gateway publishing
- **AND THEN** it does not duplicate gateway routing-id guessing rules as graphing-specific behavior

### Requirement: Graphing extension documents graphing-specific safety limits
The `houmao-ext-graphing` skill SHALL warn agents that graphing payloads must avoid unsafe executable, remote-loading, or credential-bearing content.

For Plotly.js templated graphics, the skill SHALL tell agents not to use raw replacement Plotly `data`, raw `traces`, frames, transforms, templates, JavaScript, HTML, iframes, SVG, remote URLs, credential-bearing map settings, Vega-Lite fields, Vega fields, or true 3D scene traces.

For Vega-Lite freeform graphics, the skill SHALL tell agents to use inline data unless a future capability explicitly advertises a safe reference mechanism.

For Vega-Lite freeform graphics, the skill SHALL tell agents not to use remote `data.url`, local file URLs, remote images, arbitrary HTTP(S) strings outside the allowed Vega-Lite `$schema` marker, credentials, private local file contents, arbitrary HTML, script tags, iframes, JavaScript URLs, or scriptable SVG.

#### Scenario: Agent avoids remote Vega-Lite data
- **WHEN** an agent prepares a `houmao.graphic.vegalite` payload
- **THEN** the graphing extension tells it not to use remote `data.url`
- **AND THEN** it tells the agent to validate the payload before rendering AG-UI events

#### Scenario: Agent keeps unsafe Plotly fields out of Layer 1
- **WHEN** an agent prepares a `houmao.graphic.template` payload
- **THEN** the graphing extension tells it not to use raw Plotly replacement specs or executable content
- **AND THEN** it directs the agent to the schema and catalog-backed fields instead

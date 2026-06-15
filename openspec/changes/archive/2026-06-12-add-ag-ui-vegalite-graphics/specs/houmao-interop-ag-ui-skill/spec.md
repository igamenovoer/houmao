## ADDED Requirements

### Requirement: Skill explains Layer 2 Vega-Lite authoring
The `houmao-interop-ag-ui` skill SHALL teach agents that `houmao.graphic.vegalite` is the Layer 2 path for custom declarative Vega-Lite graphics.

The skill SHALL explain that agents may either hand-author Vega-Lite JSON or optionally use Python Altair to generate the Vega-Lite `spec` with `chart.to_dict()` or `chart.to_json()`.

The skill SHALL state that agents send the resulting JSON spec in a `houmao.graphic.vegalite` payload and SHALL NOT send Python source code, notebook state, or Altair objects to the gateway.

#### Scenario: Agent chooses Layer 2 for custom declarative graphics
- **WHEN** an agent needs a layered, interactive, or custom chart structure that does not fit Layer 1 template graphics
- **THEN** the skill directs it to inspect and use `houmao.graphic.vegalite`
- **AND THEN** the skill tells it to validate and render the payload before publishing

#### Scenario: Agent uses Altair only as an authoring helper
- **WHEN** an agent uses Python Altair to build a chart
- **THEN** the skill tells it to send `chart.to_dict()` or equivalent Vega-Lite JSON
- **AND THEN** the skill does not tell it to send Python code or rely on runtime Python execution by the gateway or workbench

### Requirement: Skill preserves least-powerful-layer guidance
The `houmao-interop-ag-ui` skill SHALL teach agents to prefer `houmao.graphic.template` for ordinary Plotly-backed snapshot charts and to use `houmao.graphic.vegalite` only when they need Vega-Lite grammar, custom declarative structure, or Vega-Lite interaction.

The skill SHALL continue to state that Layer 1 does not accept Vega-Lite renderer ids, fallback renderer lists, or `extra.vega-lite`.

#### Scenario: Agent keeps ordinary charts on Layer 1
- **WHEN** an agent needs an ordinary bar, line, scatter, pie, or histogram chart with inline data
- **THEN** the skill directs it to prefer `houmao.graphic.template`
- **AND THEN** it does not direct the agent to use Vega-Lite only because Layer 2 exists

#### Scenario: Agent does not put Vega-Lite inside Layer 1
- **WHEN** an agent has a raw Vega-Lite spec
- **THEN** the skill tells it to use `houmao.graphic.vegalite`
- **AND THEN** the skill tells it not to place the raw spec in `houmao.graphic.template.extra`

### Requirement: Skill explains Vega-Lite safety limits
The `houmao-interop-ag-ui` skill SHALL tell agents that Layer 2 Vega-Lite payloads must use inline data or other explicitly supported safe references and must not use remote `data.url`, arbitrary HTML, script tags, iframes, JavaScript URLs, scriptable SVG, credentials, or private local file contents.

#### Scenario: Agent avoids remote Vega-Lite data
- **WHEN** an agent prepares a `houmao.graphic.vegalite` payload
- **THEN** the skill tells it not to use remote `data.url`
- **AND THEN** it tells the agent to validate the payload before rendering AG-UI events

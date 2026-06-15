## MODIFIED Requirements

### Requirement: Skill preserves least-powerful-layer guidance
The `houmao-interop-ag-ui` skill SHALL teach agents to prefer `houmao.graphic.template` for supported Plotly 2D snapshot charts and to use `houmao.graphic.vegalite` only when they need Vega-Lite grammar, custom declarative structure, Vega-Lite interaction, or a chart shape outside the Layer 1 Plotly 2D trace catalog.

The skill SHALL teach agents that `houmao.graphic.template` schema version `3` uses `figureType: "plotly2d"` and `traces[].type` rather than the previous five-item `chartType` contract.

The skill SHALL tell agents to inspect `houmao-mgr internals ag-ui components schema houmao.graphic.template` or AG-UI capabilities to see the supported Plotly 2D trace catalog before authoring uncommon trace families.

The skill SHALL continue to state that Layer 1 does not accept Vega-Lite renderer ids, fallback renderer lists, or `extra.vega-lite`.

#### Scenario: Agent keeps supported Plotly 2D charts on Layer 1
- **WHEN** an agent needs an ordinary supported Plotly 2D chart with inline data, such as a heatmap, box plot, violin plot, polar chart, financial chart, treemap, table, or Sankey diagram
- **THEN** the skill directs it to prefer `houmao.graphic.template`
- **AND THEN** it does not direct the agent to use Vega-Lite only because Layer 2 exists

#### Scenario: Agent checks catalog coverage for uncommon traces
- **WHEN** an agent wants to emit an uncommon Plotly trace family
- **THEN** the skill tells it to inspect the template graphics schema or capabilities for the supported trace catalog
- **AND THEN** the skill tells it to validate the payload before rendering AG-UI events

#### Scenario: Agent does not put Vega-Lite inside Layer 1
- **WHEN** an agent has a raw Vega-Lite spec
- **THEN** the skill tells it to use `houmao.graphic.vegalite`
- **AND THEN** the skill tells it not to place the raw spec in `houmao.graphic.template.extra`

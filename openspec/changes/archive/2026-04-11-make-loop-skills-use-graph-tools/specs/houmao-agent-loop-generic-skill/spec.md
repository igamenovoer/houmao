## ADDED Requirements

### Requirement: Generic loop authoring uses internal graph tools for structural preflight
The packaged `houmao-agent-loop-generic` guidance SHALL treat `houmao-mgr internals graph high` as the first-class deterministic structural helper surface when a NetworkX node-link graph representation is available for an authored generic loop plan.

For generic loop authoring, the guidance SHALL direct agents to use `houmao-mgr internals graph high analyze` when a graph artifact is available to check structural facts including reachability, leaves, non-leaf participants, cycle posture, branch points, and dependency posture.

For generic loop authoring or revision, the guidance SHALL direct agents to use `houmao-mgr internals graph high slice` when a graph artifact is available and a participant, component, ancestor, descendant, or reachable slice is easier to review separately.

For generic loop graph rendering, the guidance SHALL direct agents to use `houmao-mgr internals graph high render-mermaid` as deterministic Mermaid scaffolding when a graph artifact is available.

The generic loop guidance SHALL keep final semantic review in the skill. Graph-tool output SHALL NOT authorize broader delegation, free forwarding, hidden dependencies, result-routing changes, omission of component type labels, or omission of stop and completion semantics.

The generic loop guidance SHALL keep routine loop-skill authoring on `graph high` and SHALL NOT route normal generic loop planning to `graph low` primitives.

#### Scenario: Generic authoring uses graph high analyze
- **WHEN** a generic loop authoring agent has a node-link graph artifact for a planned typed component topology
- **THEN** the generic guidance points the agent at `houmao-mgr internals graph high analyze`
- **AND THEN** the guidance still requires the agent to review graph policy and result-routing semantics in the generic skill

#### Scenario: Generic authoring uses graph high slice for focused review
- **WHEN** a participant or component slice is easier to review separately and a node-link graph artifact exists
- **THEN** the generic guidance points the agent at `houmao-mgr internals graph high slice`
- **AND THEN** the guidance treats the slice as structural evidence rather than as permission to infer hidden delegation or forwarding

#### Scenario: Generic rendering uses graph high Mermaid scaffolding
- **WHEN** a generic loop plan with a node-link graph artifact needs its final Mermaid graph
- **THEN** the generic guidance points the agent at `houmao-mgr internals graph high render-mermaid`
- **AND THEN** the guidance requires semantic review and revision of the scaffolding before treating the graph as final

#### Scenario: Generic loop guidance stays on high-level graph helpers
- **WHEN** an agent follows routine generic loop authoring guidance
- **THEN** the guidance routes structural checks to `houmao-mgr internals graph high`
- **AND THEN** it does not ask the agent to use `graph low` primitives for normal typed loop planning

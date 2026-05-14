## ADDED Requirements

### Requirement: Advanced usage routes composed loop planning to pro
The advanced-usage pattern skill SHALL route composed topology authoring, generated execplans, graph decomposition, and loop run-control needs to `houmao-agent-loop-pro`.

It SHALL NOT route current composed loop planning to retired pairwise or generic loop package names.

#### Scenario: User needs composed topology
- **WHEN** a user asks for recursive tree-loop, generic-loop, relay, graph, or generated-execplan loop planning beyond an elemental pattern
- **THEN** advanced-usage guidance points to `houmao-agent-loop-pro`
- **AND THEN** it keeps elemental local-close and relay pages as lower-level patterns

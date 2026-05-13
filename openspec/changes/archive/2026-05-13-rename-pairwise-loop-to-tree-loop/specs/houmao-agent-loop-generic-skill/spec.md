## ADDED Requirements

### Requirement: Generic loop skill uses generic loop as canonical wording
The packaged `houmao-agent-loop-generic` skill SHALL use `generic loop` as the canonical user-facing name for directed graph loop planning and run control.

The skill MAY use `generic graph` or `generic loop graph` as compatibility wording when referring to rendered graph artifacts, graph helper commands, or older plans, but it SHALL not present that wording as a separate loop family.

The skill SHALL describe local-close tree-shaped components as tree-loop or local-close components in explanatory text while preserving existing `pairwise` component type values where templates or contracts already require them.

#### Scenario: Generic skill explains its own family
- **WHEN** `houmao-agent-loop-generic` explains what kind of loop it authors
- **THEN** it uses generic loop terminology
- **AND THEN** graph wording is reserved for graph artifacts or compatibility notes

#### Scenario: Generic plan preserves pairwise component compatibility
- **WHEN** a generic loop template or contract uses `component_type = pairwise` or equivalent existing typed-component wording
- **THEN** the value remains valid
- **AND THEN** surrounding prose explains that the component is a local-close tree-loop component or compatibility alias

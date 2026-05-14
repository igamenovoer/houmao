## ADDED Requirements

### Requirement: Internals graph docs route loop consumers to pro
The internals graph CLI reference SHALL describe `houmao-agent-loop-pro` as the current loop-skill consumer for graph helper output.

The reference MAY keep legacy graph mode examples when those modes remain accepted by the CLI, but it SHALL label them as helper modes or legacy aliases rather than current skill packages.

#### Scenario: Reader checks graph high usage
- **WHEN** a reader checks graph high authoring guidance
- **THEN** the reference names `houmao-agent-loop-pro` as the current loop authoring consumer
- **AND THEN** pairwise-v2 wording is not presented as a current skill package route

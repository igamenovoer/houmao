## ADDED Requirements

### Requirement: V4 pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise-v4` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe its template-driven workspace-aware authored topology as a tree loop or local-close tree loop in user-facing explanatory text.

The skill SHALL present `pairwise loop` as a legacy alias for tree loop behavior rather than as the primary concept name.

The skill SHALL not rename existing v4 generated template names, strict document surfaces, runtime paths, or pairwise-named compatibility references as part of this terminology change.

#### Scenario: V4 remains explicitly invokable
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise-v4`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** it explains that v4 authors or operates template-driven workspace-aware tree-loop behavior

#### Scenario: V4 preserves strict template behavior
- **WHEN** v4 guidance describes strict generated document templates or source-constraint coverage
- **THEN** those semantics remain unchanged
- **AND THEN** topology explanation uses tree-loop terminology

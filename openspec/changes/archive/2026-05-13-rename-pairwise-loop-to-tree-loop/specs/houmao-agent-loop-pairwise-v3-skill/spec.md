## ADDED Requirements

### Requirement: V3 pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise-v3` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe its workspace-aware authored topology as a tree loop or local-close tree loop in user-facing explanatory text.

The skill SHALL present `pairwise loop` as a legacy alias for tree loop behavior rather than as the primary concept name.

The skill SHALL not rename existing v3 runtime paths, recovery names, generated field names, or pairwise-named compatibility references as part of this terminology change.

#### Scenario: V3 remains explicitly invokable
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise-v3`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** it explains that v3 authors or operates workspace-aware tree-loop behavior

#### Scenario: V3 preserves workspace behavior
- **WHEN** v3 guidance describes workspace-aware loop preparation
- **THEN** the workspace behavior remains unchanged
- **AND THEN** topology explanation uses tree-loop terminology

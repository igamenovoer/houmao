## ADDED Requirements

### Requirement: V2 pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise-v2` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe its enriched authored topology as a tree loop or local-close tree loop in user-facing explanatory text.

The skill SHALL present `pairwise loop` as a legacy alias for tree loop behavior rather than as the primary concept name.

The skill SHALL not rename existing v2 runtime paths, recovery names, generated field names, or pairwise-named compatibility references as part of this terminology change.

#### Scenario: V2 remains explicitly invokable
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise-v2`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** it explains that v2 authors or operates enriched tree-loop behavior

#### Scenario: V2 preserves existing runtime compatibility
- **WHEN** v2 guidance references existing runtime-owned paths or pairwise-named recovery records
- **THEN** those references remain unchanged
- **AND THEN** surrounding prose uses tree-loop terminology where it explains the topology to users

## ADDED Requirements

### Requirement: Stable pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe its authored topology as a tree loop or local-close tree loop in user-facing explanatory text.

The skill SHALL present `pairwise loop` as a legacy alias for tree loop behavior rather than as the primary concept name.

The skill SHALL keep pairwise-named protocol references only where they identify existing skill handles, compatibility aliases, or elemental local-close edge behavior.

#### Scenario: Stable skill is invoked by legacy name
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** its guidance explains that the run is a tree loop with pairwise loop as an alias

#### Scenario: Stable skill routes to elemental edge protocol
- **WHEN** stable tree-loop guidance points to one immediate driver-worker edge protocol
- **THEN** it uses local-close edge loop terminology
- **AND THEN** it may mention the existing pairwise edge-loop pattern as the compatibility target

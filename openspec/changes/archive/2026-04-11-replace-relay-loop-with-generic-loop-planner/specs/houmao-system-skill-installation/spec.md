## ADDED Requirements

### Requirement: Packaged system-skill catalog replaces relay loop planner with generic loop planner
The packaged current-system-skill catalog SHALL include `houmao-agent-loop-generic` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-agent-loop-generic` as both its catalog key and its packaged `asset_subpath`.

The packaged current-system-skill catalog SHALL NOT include `houmao-agent-loop-relay` as a current installable skill after the generic replacement is introduced.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-agent-loop-pairwise`,
- `houmao-agent-loop-pairwise-v2`,
- `houmao-agent-loop-generic`.

The packaged catalog's `user-control` named set SHALL NOT include `houmao-agent-loop-relay` after this replacement.

Because managed launch, managed join, and CLI-default installation already resolve `user-control`, those fixed auto-install selections SHALL pick up `houmao-agent-loop-generic` through the updated set membership.

#### Scenario: Maintainer sees generic loop skill in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-loop-generic`
- **AND THEN** the current installable skill inventory does not include `houmao-agent-loop-relay`

#### Scenario: User-control expands to the generic loop skill
- **WHEN** a maintainer inspects the packaged `user-control` named set
- **THEN** that set resolves `houmao-agent-loop-generic` alongside the pairwise loop skill variants
- **AND THEN** that set does not resolve `houmao-agent-loop-relay`

#### Scenario: Auto-install picks up the generic loop skill through user-control
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved install lists include `houmao-agent-loop-generic` through `user-control`

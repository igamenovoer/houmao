## ADDED Requirements

### Requirement: Packaged system-skill catalog includes both pairwise skill variants in `user-control`
The packaged current-system-skill catalog SHALL include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` as current installable Houmao-owned skills.

Each packaged skill SHALL use its skill name as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`

alongside the other user-control skills.

Because managed launch, managed join, and CLI-default installation already resolve `user-control`, those fixed auto-install selections SHALL pick up both pairwise skill variants through the expanded set membership.

#### Scenario: Maintainer sees both pairwise skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`
- **AND THEN** each skill uses its own flat packaged asset subpath under the maintained runtime asset root

#### Scenario: User-control expands to both pairwise variants
- **WHEN** a maintainer inspects the packaged `user-control` named set
- **THEN** that set resolves both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`
- **AND THEN** the set does not require a second pairwise-only named set to expose the versioned skill

#### Scenario: Auto-install picks up both pairwise variants through user-control
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved install lists now include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` without further conditional expansion

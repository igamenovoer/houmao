## MODIFIED Requirements

### Requirement: Packaged system-skill catalog includes all pairwise variants in the current install sets
The packaged current-system-skill catalog SHALL include `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-pairwise-v3` as current installable Houmao-owned skills.

Each packaged skill SHALL use its skill name as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `core` named set SHALL include:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`

alongside the other current managed-control skills.

The packaged catalog's `all` named set SHALL also include those three pairwise skills so CLI-default installation continues to expose the same family plus utility skills.

Because managed launch and managed join resolve `core`, and CLI-default installation resolves `all`, those fixed auto-install selections SHALL pick up all three pairwise skill variants through the expanded set membership.

#### Scenario: Maintainer sees all pairwise skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-pairwise-v3`
- **AND THEN** each skill uses its own flat packaged asset subpath under the maintained runtime asset root

#### Scenario: Core and all sets both expose all pairwise variants
- **WHEN** a maintainer inspects the packaged `core` and `all` named sets
- **THEN** each set resolves `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-pairwise-v3`
- **AND THEN** neither set requires a second pairwise-only named set to expose the workspace-aware versioned skill

#### Scenario: Auto-install picks up all pairwise variants through current set membership
- **WHEN** Houmao resolves auto-install skill selection through the packaged `core` and `all` memberships
- **THEN** the resolved install list includes `houmao-agent-loop-pairwise-v3`
- **AND THEN** the workspace-aware pairwise successor is available through the same packaged install path as the other current pairwise skills

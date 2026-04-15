## ADDED Requirements

### Requirement: Packaged system-skill catalog includes managed-memory guidance
The packaged current-system-skill catalog SHALL include `houmao-memory-mgr` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-memory-mgr` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set for managed-agent memory guidance containing `houmao-memory-mgr`.

The packaged catalog's fixed `managed_launch_sets` selection SHALL include that managed-memory named set.

The packaged catalog's fixed `managed_join_sets` selection SHALL include that managed-memory named set.

The packaged catalog's fixed `cli_default_sets` selection SHALL include that managed-memory named set.

When those fixed selections resolve, the resolved installed skill list SHALL include `houmao-memory-mgr`.

#### Scenario: Maintainer sees the packaged memory-management skill and set
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-memory-mgr`
- **AND THEN** a dedicated managed-memory named set resolves that skill

#### Scenario: Managed and default selections include memory-management guidance
- **WHEN** Houmao resolves `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **THEN** the resolved install selection includes `houmao-memory-mgr`
- **AND THEN** the skill is available to managed homes and explicit default external installs


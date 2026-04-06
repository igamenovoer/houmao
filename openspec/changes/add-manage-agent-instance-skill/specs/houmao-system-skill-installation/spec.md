## ADDED Requirements

### Requirement: Packaged system-skill catalog includes agent-instance lifecycle guidance and adds it to CLI-default installs
The packaged current-system-skill catalog SHALL include `houmao-manage-agent-instance` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-manage-agent-instance` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set for the new lifecycle skill instead of folding that skill into `project-easy`.

The packaged catalog's fixed `cli_default_sets` selection SHALL include both:

- the existing specialist-management default path through `project-easy`
- the new agent-instance lifecycle set containing `houmao-manage-agent-instance`

This change SHALL NOT require adding the new agent-instance lifecycle set to `managed_launch_sets` or `managed_join_sets`.

#### Scenario: Maintainer sees the new lifecycle skill in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-manage-agent-instance`
- **AND THEN** that skill uses its own flat asset subpath under the maintained runtime asset root

#### Scenario: CLI-default selection includes both specialist and instance lifecycle guidance
- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes both `project-easy` and the new agent-instance lifecycle set
- **AND THEN** the CLI-default install path resolves both `houmao-manage-specialist` and `houmao-manage-agent-instance`

#### Scenario: Managed auto-install lists remain unchanged in this change
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections do not gain the new agent-instance lifecycle set as part of this change
- **AND THEN** the change limits default-selection broadening to the CLI-default install path

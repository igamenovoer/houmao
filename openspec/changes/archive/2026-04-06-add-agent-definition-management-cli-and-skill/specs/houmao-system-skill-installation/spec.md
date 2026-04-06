## ADDED Requirements

### Requirement: Packaged system-skill catalog includes low-level agent-definition guidance in the user-control set

The packaged current-system-skill catalog SHALL include `houmao-manage-agent-definition` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-manage-agent-definition` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-manage-specialist`
- `houmao-manage-credentials`
- `houmao-manage-agent-definition`

The packaged catalog SHALL keep `houmao-manage-agent-definition` inside `user-control` rather than creating a separate named set just for low-level definition authoring.

Because managed launch and managed join already resolve `user-control`, those fixed auto-install selections SHALL pick up the new packaged skill through the expanded set membership.

#### Scenario: Maintainer sees the packaged agent-definition skill in the user-control inventory

- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-manage-agent-definition`
- **AND THEN** the `user-control` named set resolves that skill alongside `houmao-manage-specialist` and `houmao-manage-credentials`

#### Scenario: Managed auto-install picks up the expanded user-control set

- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved `user-control` install list now includes `houmao-manage-agent-definition` without requiring a new named set

## MODIFIED Requirements

### Requirement: Packaged system-skill catalog includes agent-instance lifecycle guidance and adds it to CLI-default installs

The packaged current-system-skill catalog SHALL include `houmao-manage-agent-instance` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-manage-agent-instance` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set for the lifecycle skill instead of folding that skill into `user-control`.

The packaged catalog's fixed `managed_launch_sets` selection SHALL include:

- `mailbox-full`
- `user-control`

The packaged catalog's fixed `managed_join_sets` selection SHALL include:

- `mailbox-full`
- `user-control`

The packaged catalog's fixed `cli_default_sets` selection SHALL include both:

- the `user-control` set containing `houmao-manage-specialist`, `houmao-manage-credentials`, and `houmao-manage-agent-definition`
- the dedicated agent-instance lifecycle set containing `houmao-manage-agent-instance`

This change SHALL NOT require adding the new agent-instance lifecycle set to `managed_launch_sets` or `managed_join_sets`.

#### Scenario: Maintainer sees the new lifecycle skill in the packaged catalog

- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-manage-agent-instance`
- **AND THEN** that skill uses its own flat asset subpath under the maintained runtime asset root

#### Scenario: CLI-default selection includes user-control and instance lifecycle guidance

- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes both `user-control` and the agent-instance lifecycle set
- **AND THEN** the CLI-default install path resolves `houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, and `houmao-manage-agent-instance`

#### Scenario: Managed auto-install lists use user-control and still exclude the agent-instance set

- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections use `user-control` instead of `project-easy`
- **AND THEN** they resolve the packaged user-control skills without adding the separate agent-instance lifecycle set

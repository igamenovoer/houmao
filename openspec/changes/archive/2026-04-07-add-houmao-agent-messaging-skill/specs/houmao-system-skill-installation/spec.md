## MODIFIED Requirements

### Requirement: Packaged system-skill catalog includes agent-instance lifecycle guidance and adds it to CLI-default installs
The packaged current-system-skill catalog SHALL include `houmao-manage-agent-instance` and `houmao-agent-messaging` as current installable Houmao-owned skills.

That packaged skill SHALL use its skill name as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define dedicated named sets for the lifecycle skill and the messaging skill instead of folding either of those skills into `user-control`.

The packaged catalog's fixed `managed_launch_sets` selection SHALL include:

- `mailbox-full`
- `user-control`
- the dedicated agent-messaging set containing `houmao-agent-messaging`

The packaged catalog's fixed `managed_join_sets` selection SHALL include:

- `mailbox-full`
- `user-control`
- the dedicated agent-messaging set containing `houmao-agent-messaging`

The packaged catalog's fixed `cli_default_sets` selection SHALL include:

- `mailbox-full`
- `user-control`
- the dedicated agent-instance lifecycle set containing `houmao-manage-agent-instance`
- the dedicated agent-messaging set containing `houmao-agent-messaging`

This change SHALL NOT require adding the separate agent-instance lifecycle set to `managed_launch_sets` or `managed_join_sets`.

#### Scenario: Maintainer sees the lifecycle and messaging skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes both `houmao-manage-agent-instance` and `houmao-agent-messaging`
- **AND THEN** each skill uses its own flat asset subpath under the maintained runtime asset root

#### Scenario: CLI-default selection includes lifecycle and messaging guidance
- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes both the agent-instance lifecycle set and the agent-messaging set
- **AND THEN** the CLI-default install path resolves both `houmao-manage-agent-instance` and `houmao-agent-messaging`

#### Scenario: Managed auto-install gains messaging but still excludes the lifecycle-only set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections include the dedicated agent-messaging set
- **AND THEN** they do not add the separate agent-instance lifecycle set as part of this change

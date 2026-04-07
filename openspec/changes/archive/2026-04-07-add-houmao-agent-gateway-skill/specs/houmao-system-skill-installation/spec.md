## MODIFIED Requirements

### Requirement: Packaged system-skill catalog includes agent-instance lifecycle guidance and adds it to CLI-default installs
The packaged current-system-skill catalog SHALL include `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` as current installable Houmao-owned skills.

Each packaged skill SHALL use its skill name as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define dedicated named sets for:

- the lifecycle skill,
- the messaging skill,
- the gateway skill,

instead of folding any of those skills into `user-control`.

The packaged catalog's fixed `managed_launch_sets` selection SHALL include:

- `mailbox-full`
- `user-control`
- the dedicated agent-messaging set containing `houmao-agent-messaging`
- the dedicated agent-gateway set containing `houmao-agent-gateway`

The packaged catalog's fixed `managed_join_sets` selection SHALL include:

- `mailbox-full`
- `user-control`
- the dedicated agent-messaging set containing `houmao-agent-messaging`
- the dedicated agent-gateway set containing `houmao-agent-gateway`

The packaged catalog's fixed `cli_default_sets` selection SHALL include:

- `mailbox-full`
- `user-control`
- the dedicated agent-instance lifecycle set containing `houmao-manage-agent-instance`
- the dedicated agent-messaging set containing `houmao-agent-messaging`
- the dedicated agent-gateway set containing `houmao-agent-gateway`

This change SHALL NOT require adding the separate agent-instance lifecycle set to `managed_launch_sets` or `managed_join_sets`.

#### Scenario: Maintainer sees the lifecycle, messaging, and gateway skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway`
- **AND THEN** each skill uses its own flat asset subpath under the maintained runtime asset root

#### Scenario: CLI-default selection includes lifecycle, messaging, and gateway guidance
- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes the agent-instance lifecycle set, the agent-messaging set, and the agent-gateway set
- **AND THEN** the CLI-default install path resolves `houmao-manage-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway`

#### Scenario: Managed auto-install gains gateway guidance but still excludes the lifecycle-only set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections include both the dedicated agent-messaging set and the dedicated agent-gateway set
- **AND THEN** they do not add the separate agent-instance lifecycle set as part of this change

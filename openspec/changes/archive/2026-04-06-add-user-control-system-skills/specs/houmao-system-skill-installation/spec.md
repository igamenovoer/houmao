## MODIFIED Requirements

### Requirement: Current Houmao-owned system skills are packaged as maintained runtime assets
The system SHALL package the current Houmao-owned `houmao-*` skills under one maintained Houmao-owned runtime asset root that is separate from project starter assets.

The packaged current-skill catalog SHALL live as one authoritative packaged catalog file under that maintained runtime asset root.

That packaged catalog SHALL identify:

- an explicit `schema_version`,
- the full inventory of current installable Houmao-owned skills,
- the packaged asset subpath for each current skill,
- one or more named skill sets whose members are explicit current skill names,
- fixed auto-install set lists used by Houmao-managed homes and CLI default installation.

This change SHALL NOT require conditional rules, profile expansion, or other dynamic catalog evaluation beyond those fixed named sets and auto-install set lists.

The packaged current-skill catalog SHALL have one matching JSON Schema document, and loading SHALL validate the normalized catalog payload against that JSON Schema before any set expansion or install resolution proceeds.

For the current maintained skill set, each packaged skill `asset_subpath` SHALL equal the skill's own directory name under the maintained asset root and SHALL NOT include a family namespace segment such as `mailbox/` or `project/`.

Logical grouping of current skills SHALL be expressed through named skill sets and descriptions rather than through nested packaged skill directories.

For the user-control skill set, the current packaged specialist-management skill SHALL be `houmao-manage-specialist`, the current packaged credential-management skill SHALL be `houmao-manage-credentials`, and the packaged catalog SHALL NOT continue to expose `project-easy` as the active named set for those packaged skills.

#### Scenario: Maintainer inspects the packaged current-skill catalog
- **WHEN** a maintainer inspects the Houmao-owned packaged system-skill assets
- **THEN** the current `houmao-*` skills are available from one maintained runtime asset root
- **AND THEN** project starter assets remain in their own separate asset tree
- **AND THEN** one authoritative packaged catalog file identifies the current installable skill inventory, named skill sets, fixed auto-install set lists, and explicit `schema_version`
- **AND THEN** each current packaged skill directory lives directly under that asset root using its skill name as the relative `asset_subpath`

#### Scenario: User-control set references the current packaged user-control skills
- **WHEN** a maintainer inspects the packaged current-skill catalog
- **THEN** the `user-control` set resolves `houmao-manage-specialist` and `houmao-manage-credentials`
- **AND THEN** the current installable skill inventory does not still expose `project-easy` as the active named set for that packaged skill family

#### Scenario: Loader rejects a schema-invalid packaged catalog
- **WHEN** Houmao loads the packaged current-skill catalog
- **AND WHEN** the normalized catalog payload violates the packaged JSON Schema
- **THEN** catalog loading fails explicitly before set expansion or install resolution begins
- **AND THEN** Houmao does not proceed to filesystem mutation from that invalid packaged catalog

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

- the `user-control` set containing `houmao-manage-specialist` and `houmao-manage-credentials`
- the dedicated agent-instance lifecycle set containing `houmao-manage-agent-instance`

This change SHALL NOT require adding the agent-instance lifecycle set to `managed_launch_sets` or `managed_join_sets`.

#### Scenario: Maintainer sees the new lifecycle skill in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-manage-agent-instance`
- **AND THEN** that skill uses its own flat asset subpath under the maintained runtime asset root

#### Scenario: CLI-default selection includes user-control and instance lifecycle guidance
- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes both `user-control` and the agent-instance lifecycle set
- **AND THEN** the CLI-default install path resolves `houmao-manage-specialist`, `houmao-manage-credentials`, and `houmao-manage-agent-instance`

#### Scenario: Managed auto-install lists use user-control and still exclude the agent-instance set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections use `user-control` instead of `project-easy`
- **AND THEN** they resolve the packaged user-control skills without adding the separate agent-instance lifecycle set

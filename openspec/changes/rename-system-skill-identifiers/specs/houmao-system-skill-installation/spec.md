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

For the user-control skill set, the current packaged specialist-management skill SHALL be `houmao-specialist-mgr`, the current packaged credential-management skill SHALL be `houmao-credential-mgr`, the current packaged low-level definition-management skill SHALL be `houmao-agent-definition`, and the packaged catalog SHALL NOT continue to expose `houmao-manage-specialist`, `houmao-manage-credentials`, or `houmao-manage-agent-definition` as current installable skills.

#### Scenario: Maintainer inspects the packaged current-skill catalog
- **WHEN** a maintainer inspects the Houmao-owned packaged system-skill assets
- **THEN** the current `houmao-*` skills are available from one maintained runtime asset root
- **AND THEN** project starter assets remain in their own separate asset tree
- **AND THEN** one authoritative packaged catalog file identifies the current installable skill inventory, named skill sets, fixed auto-install set lists, and explicit `schema_version`
- **AND THEN** each current packaged skill directory lives directly under that asset root using its skill name as the relative `asset_subpath`

#### Scenario: User-control set references the renamed current packaged user-control skills
- **WHEN** a maintainer inspects the packaged current-skill catalog
- **THEN** the `user-control` set resolves `houmao-specialist-mgr`, `houmao-credential-mgr`, and `houmao-agent-definition`
- **AND THEN** the current installable skill inventory does not still expose `houmao-manage-specialist`, `houmao-manage-credentials`, or `houmao-manage-agent-definition` as active packaged skills

#### Scenario: Loader rejects a schema-invalid packaged catalog
- **WHEN** Houmao loads the packaged current-skill catalog
- **AND WHEN** the normalized catalog payload violates the packaged JSON Schema
- **THEN** catalog loading fails explicitly before set expansion or install resolution begins
- **AND THEN** Houmao does not proceed to filesystem mutation from that invalid packaged catalog

### Requirement: Shared installer records Houmao-owned install state and preserves unrelated content
The shared installer SHALL record Houmao-owned install state under the target home and SHALL use that state to make repeated installation idempotent.

For each recorded installed skill, the install state SHALL record:

- the current skill name,
- the packaged asset subpath,
- the owned projected relative directory inside the tool home,
- the recorded projection mode,
- the recorded content digest.

When the current projected path for one selected skill differs from a previously recorded Houmao-owned path for that same skill, reinstall SHALL remove the previously owned path before or during projection of the new path and SHALL update install state to record only the current owned path for that skill.

When the current projection mode for one selected skill differs from a previously recorded Houmao-owned mode for that same skill, reinstall SHALL replace the previously owned in-home path with the newly requested projection mode and SHALL update install state to record only the current mode for that skill.

When the current packaged skill name supersedes a previously recorded Houmao-owned skill name for the same maintained workflow, reinstall or auto-install SHALL remove the previously owned path for the superseded skill and SHALL update install state to keep only the current renamed skill record.

The installer SHALL preserve unrelated user-authored skill content in the target home.

If a required projected path collides with content that is not recorded as Houmao-owned install state, the installer SHALL fail explicitly rather than overwriting that content silently.

If Houmao encounters a previously recorded copy-only install-state record from before projection mode was tracked explicitly, it SHALL continue to treat that owned record as a copied projection during status and reinstall.

#### Scenario: Reinstalling the same current skill set keeps the flat owned result stable
- **WHEN** Houmao installs the same selected current Houmao-owned skill set into the same target home more than once using the same projection mode
- **THEN** the installer reuses Houmao-owned install state to keep the projected result consistent
- **AND THEN** the target home does not accumulate duplicate Houmao-owned skill trees or duplicate Houmao-owned symlink entries

#### Scenario: Reinstall switches one selected skill from copied projection to symlink projection
- **WHEN** a target tool home already records one selected current Houmao-owned skill as a copied projection
- **AND WHEN** the operator reinstalls that same skill into the same owned tool-native path using symlink projection
- **THEN** the installer replaces the previously owned copied path with the requested symlink entry
- **AND THEN** the recorded Houmao-owned install state is updated to keep only the current symlink projection mode for that skill

#### Scenario: Reinstall migrates a previously owned family-namespaced path
- **WHEN** a target tool home already records a Houmao-owned path such as `skills/mailbox/<houmao-skill>/` or `skills/project/<houmao-skill>/` for one selected skill
- **AND WHEN** the current installer now projects that same skill into the flat top-level tool-native path
- **THEN** reinstall removes the previously owned family-namespaced path before or during projection of the new path
- **AND THEN** the recorded Houmao-owned install state is updated to keep only the current flat owned path for that skill
- **AND THEN** the target home does not retain stale Houmao-owned namespace directories for that migrated skill

#### Scenario: Reinstall migrates the renamed current system-skill identifiers
- **WHEN** a target tool home already records Houmao-owned install state for `houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, or `houmao-manage-agent-instance`
- **AND WHEN** the current packaged catalog now selects `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, or `houmao-agent-instance` for those maintained workflows
- **THEN** reinstall or auto-install removes the previously owned projected directory for each superseded skill before or during projection of the renamed skill
- **AND THEN** the recorded Houmao-owned install state is updated to keep only the renamed current skill identifiers
- **AND THEN** the target home does not retain stale owned directories for the superseded skill names alongside the renamed skills

#### Scenario: Non-owned collision fails closed
- **WHEN** the shared installer needs to project a current Houmao-owned skill path into a target home
- **AND WHEN** that projected path is already occupied by content not recorded as Houmao-owned install state
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not silently overwrite the non-owned content

#### Scenario: Upgrade reads a previously recorded copy-only install-state record
- **WHEN** Houmao reads a previously recorded Houmao-owned install-state record that predates explicit projection-mode tracking
- **THEN** the system treats that record as a copied projection for status and reinstall purposes
- **AND THEN** the existing owned copied skill path remains manageable by the shared installer

### Requirement: Packaged system-skill catalog includes low-level agent-definition guidance in the user-control set
The packaged current-system-skill catalog SHALL include `houmao-agent-definition` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-agent-definition` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`

The packaged catalog SHALL keep `houmao-agent-definition` inside `user-control` rather than creating a separate named set just for low-level definition authoring.

Because managed launch and managed join already resolve `user-control`, those fixed auto-install selections SHALL pick up the renamed packaged skill through the existing set membership.

#### Scenario: Maintainer sees the packaged agent-definition skill in the user-control inventory
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-definition`
- **AND THEN** the `user-control` named set resolves that skill alongside `houmao-specialist-mgr` and `houmao-credential-mgr`

#### Scenario: Managed auto-install picks up the renamed user-control inventory
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved `user-control` install list now includes `houmao-agent-definition` alongside `houmao-specialist-mgr` and `houmao-credential-mgr` without requiring a new named set

### Requirement: Packaged system-skill catalog includes agent-instance lifecycle guidance and adds it to CLI-default installs
The packaged current-system-skill catalog SHALL include `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway` as current installable Houmao-owned skills.

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
- the dedicated agent-instance lifecycle set containing `houmao-agent-instance`
- the dedicated agent-messaging set containing `houmao-agent-messaging`
- the dedicated agent-gateway set containing `houmao-agent-gateway`

This change SHALL NOT require adding the separate agent-instance lifecycle set to `managed_launch_sets` or `managed_join_sets`.

#### Scenario: Maintainer sees the lifecycle, messaging, and gateway skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway`
- **AND THEN** each skill uses its own flat asset subpath under the maintained runtime asset root

#### Scenario: CLI-default selection includes renamed lifecycle, messaging, and gateway guidance
- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes the agent-instance lifecycle set, the agent-messaging set, and the agent-gateway set
- **AND THEN** the CLI-default install path resolves `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway`

#### Scenario: Managed auto-install gains the renamed user-control inventory but still excludes the lifecycle-only set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections include both the dedicated agent-messaging set and the dedicated agent-gateway set
- **AND THEN** they do not add the separate agent-instance lifecycle set as part of this change

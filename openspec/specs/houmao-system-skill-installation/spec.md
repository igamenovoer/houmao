## Purpose
Define packaged catalog, selection, projection, and install-state behavior for the current Houmao-owned system-skill set.
## Requirements
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

### Requirement: Shared installer projects selected current Houmao-owned skills into target tool homes
The system SHALL install only the selected current Houmao-owned skills into a target tool home through one shared installer contract used by both explicit operator installation and Houmao-managed runtime installation.

For the current skill set, the visible projected paths SHALL remain tool-native:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/<houmao-skill>/`
- Gemini: `.gemini/skills/<houmao-skill>/`

The shared installer SHALL support these projection modes:

- `copy` for copied packaged skill trees,
- `symlink` for directory symlinks whose in-home path is the tool-native skill path.

For explicit operator installation, the shared installer SHALL default to `copy` projection mode unless the operator explicitly requests `symlink`.

For Houmao-managed runtime installation, the shared installer SHALL continue to use `copy` projection mode in this change.

When explicit operator installation requests `symlink` mode, the shared installer SHALL create one directory symlink per selected skill at the tool-native destination path and SHALL use the absolute filesystem path of the packaged skill asset directory as the symlink target.

If the packaged skill asset directory cannot be addressed as a stable real filesystem directory path, explicit `symlink` installation SHALL fail explicitly and SHALL NOT silently fall back to copied projection.

The shared installer SHALL NOT require a project-local copied skill mirror or worktree-local `SKILL.md` path for ordinary use of those installed skills.

#### Scenario: Explicit copy installation projects one selected current skill into a Codex home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Codex home without requesting symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as copied content
- **AND THEN** it does not require a copied project-local skill mirror for ordinary use of that installed skill

#### Scenario: Explicit symlink installation projects one selected current skill into a Codex home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Codex home and explicitly requests symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as a directory symlink
- **AND THEN** the symlink target is the absolute filesystem path of the packaged skill asset directory

#### Scenario: Managed home installation preserves the current Gemini skill root with copied projection
- **WHEN** Houmao installs selected current Houmao-owned skills into a managed Gemini home
- **THEN** the installer projects those skills under `.gemini/skills/`
- **AND THEN** it uses copied projection rather than symlink projection in this change
- **AND THEN** it does not require `.agents/skills` as the primary visible projection root for those installed skills

#### Scenario: Explicit symlink installation fails when the packaged skill root is not filesystem-backed
- **WHEN** an operator explicitly requests symlink installation for one selected current Houmao-owned skill
- **AND WHEN** the packaged skill asset directory does not have a stable real filesystem directory path
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not silently replace that request with copied projection

### Requirement: Shared installer supports named set selection and explicit current-skill selection
The shared installer SHALL support two selection modes for the current Houmao-owned skill set:

- one or more named skill sets,
- one or more explicitly selected current skill names.

Whenever Houmao automatically installs its own current skills into a managed home, it SHALL use the packaged catalog’s fixed auto-install set lists.

When installation input includes multiple named sets plus explicit skill names, the resolved install list SHALL preserve first occurrence order and SHALL contain each selected skill at most once.

That automatic or explicit selection SHALL NOT depend on conditional rule evaluation in this change.

#### Scenario: Managed brain construction uses the managed-launch auto-install set list
- **WHEN** Houmao constructs a managed home that performs default Houmao-owned skill installation
- **THEN** it installs the skill list resolved from the packaged current-skill catalog’s managed-launch auto-install set list
- **AND THEN** that automatic selection does not depend on a second mailbox-only default list
- **AND THEN** it does not require conditional catalog expansion in this change

#### Scenario: Explicit installation resolves multiple named sets and explicit skills
- **WHEN** an operator explicitly selects multiple named sets and one current Houmao-owned skill for installation
- **THEN** the installer resolves the final install list by expanding the selected sets in order, appending the explicit skill, and deduplicating by first occurrence
- **AND THEN** it does not silently replace that explicit selection with an internal auto-install set list

#### Scenario: Unknown set fails explicit installation
- **WHEN** an operator explicitly selects one named set for installation
- **AND WHEN** that set name is not defined in the packaged current-skill catalog
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not guess another set or proceed with partial resolution

#### Scenario: Loader rejects a set that references an unknown skill
- **WHEN** Houmao loads the packaged current-skill catalog
- **AND WHEN** one named set references a skill name not present in the packaged skill inventory
- **THEN** catalog loading fails explicitly before installation begins
- **AND THEN** Houmao does not proceed with partial set expansion

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

#### Scenario: Reinstall migrates the renamed specialist-management skill
- **WHEN** a target tool home already records Houmao-owned install state for `houmao-create-specialist`
- **AND WHEN** the current packaged catalog now selects `houmao-manage-specialist`
- **THEN** reinstall or auto-install removes the previously owned `houmao-create-specialist` projected directory before or during projection of `houmao-manage-specialist`
- **AND THEN** the recorded Houmao-owned install state is updated to keep only `houmao-manage-specialist`
- **AND THEN** the target home does not retain the stale owned `houmao-create-specialist` directory alongside the renamed skill

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


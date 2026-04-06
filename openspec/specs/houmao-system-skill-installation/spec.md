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

For the project-easy skill set, the current packaged specialist-management skill SHALL be `houmao-manage-specialist`, and the packaged catalog SHALL NOT continue to list `houmao-create-specialist` as a current installable skill.

#### Scenario: Maintainer inspects the packaged current-skill catalog
- **WHEN** a maintainer inspects the Houmao-owned packaged system-skill assets
- **THEN** the current `houmao-*` skills are available from one maintained runtime asset root
- **AND THEN** project starter assets remain in their own separate asset tree
- **AND THEN** one authoritative packaged catalog file identifies the current installable skill inventory, named skill sets, fixed auto-install set lists, and explicit `schema_version`
- **AND THEN** each current packaged skill directory lives directly under that asset root using its skill name as the relative `asset_subpath`

#### Scenario: Project-easy set references the renamed specialist-management skill
- **WHEN** a maintainer inspects the packaged current-skill catalog
- **THEN** the `project-easy` set resolves `houmao-manage-specialist`
- **AND THEN** the current installable skill inventory does not still list `houmao-create-specialist` as an active packaged skill

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
- Gemini: `.agents/skills/<houmao-skill>/`

The shared installer SHALL NOT require a project-local copied skill mirror or worktree-local `SKILL.md` path for ordinary use of those installed skills.

#### Scenario: Explicit installation projects one selected current skill into a Codex home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Codex home
- **THEN** the installer projects that skill under `skills/<houmao-skill>/`
- **AND THEN** it does not require a copied project-local skill mirror for ordinary use of that installed skill

#### Scenario: Managed home installation preserves the current Gemini skill root
- **WHEN** Houmao installs selected current Houmao-owned skills into a managed Gemini home
- **THEN** the installer projects those skills under `.agents/skills/`
- **AND THEN** it does not require `.gemini/skills` as the primary visible projection root for those installed skills

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

When the current projected path for one selected skill differs from a previously recorded Houmao-owned path for that same skill, reinstall SHALL remove the previously owned path before or during projection of the new path and SHALL update install state to record only the current owned path for that skill.

When the current packaged skill name supersedes a previously recorded Houmao-owned skill name for the same maintained workflow, reinstall or auto-install SHALL remove the previously owned path for the superseded skill and SHALL update install state to keep only the current renamed skill record.

The installer SHALL preserve unrelated user-authored skill content in the target home.

If a required projected path collides with content that is not recorded as Houmao-owned install state, the installer SHALL fail explicitly rather than overwriting that content silently.

#### Scenario: Reinstalling the same current skill set keeps the flat owned result stable
- **WHEN** Houmao installs the same selected current Houmao-owned skill set into the same target home more than once
- **THEN** the installer reuses Houmao-owned install state to keep the projected result consistent
- **AND THEN** the target home does not accumulate duplicate Houmao-owned skill trees

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

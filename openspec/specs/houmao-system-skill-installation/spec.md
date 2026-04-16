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

For the user-control skill set, the current packaged project-management skill SHALL be `houmao-project-mgr`, the current packaged specialist-management skill SHALL be `houmao-specialist-mgr`, the current packaged credential-management skill SHALL be `houmao-credential-mgr`, the current packaged low-level definition-management skill SHALL be `houmao-agent-definition`, and the packaged catalog SHALL NOT continue to expose `project-easy` as the active named set for those packaged skills or `houmao-manage-specialist`, `houmao-manage-credentials`, or `houmao-manage-agent-definition` as current installable skills.

#### Scenario: Maintainer inspects the packaged current-skill catalog
- **WHEN** a maintainer inspects the Houmao-owned packaged system-skill assets
- **THEN** the current `houmao-*` skills are available from one maintained runtime asset root
- **AND THEN** project starter assets remain in their own separate asset tree
- **AND THEN** one authoritative packaged catalog file identifies the current installable skill inventory, named skill sets, fixed auto-install set lists, and explicit `schema_version`
- **AND THEN** each current packaged skill directory lives directly under that asset root using its skill name as the relative `asset_subpath`

#### Scenario: User-control set references the renamed current packaged user-control skills
- **WHEN** a maintainer inspects the packaged current-skill catalog
- **THEN** the `user-control` set resolves `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, and `houmao-agent-definition`
- **AND THEN** the current installable skill inventory does not still expose `project-easy` as the active named set for that packaged skill family
- **AND THEN** the current installable skill inventory does not still expose `houmao-manage-specialist`, `houmao-manage-credentials`, or `houmao-manage-agent-definition` as active packaged skills

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

### Requirement: Packaged system-skill catalog includes low-level agent-definition guidance in the user-control set
The packaged current-system-skill catalog SHALL include `houmao-agent-definition` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-agent-definition` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`

The packaged catalog SHALL keep `houmao-agent-definition` inside `user-control` rather than creating a separate named set just for low-level definition authoring.

Because managed launch and managed join already resolve `user-control`, those fixed auto-install selections SHALL pick up the new packaged skill through the expanded set membership.

#### Scenario: Maintainer sees the packaged agent-definition skill in the user-control inventory
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-definition`
- **AND THEN** the `user-control` named set resolves that skill alongside `houmao-project-mgr`, `houmao-specialist-mgr`, and `houmao-credential-mgr`

#### Scenario: Managed auto-install picks up the expanded user-control set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved `user-control` install list now includes `houmao-agent-definition` without requiring a new named set

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

#### Scenario: CLI-default selection includes lifecycle, messaging, and gateway guidance
- **WHEN** a maintainer inspects the packaged auto-install selection lists
- **THEN** the fixed `cli_default_sets` selection includes the agent-instance lifecycle set, the agent-messaging set, and the agent-gateway set
- **AND THEN** the CLI-default install path resolves `houmao-agent-instance`, `houmao-agent-messaging`, and `houmao-agent-gateway`

#### Scenario: Managed auto-install gains gateway guidance but still excludes the lifecycle-only set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets` and `managed_join_sets`
- **THEN** those fixed auto-install selections include both the dedicated agent-messaging set and the dedicated agent-gateway set
- **AND THEN** they do not add the separate agent-instance lifecycle set as part of this change

### Requirement: Packaged system-skill catalog includes mailbox-administration guidance and expands `mailbox-full`
The packaged current-system-skill catalog SHALL include `houmao-mailbox-mgr` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-mailbox-mgr` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `mailbox-core` named set SHALL continue to include only:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The packaged catalog's `mailbox-full` named set SHALL include:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-mailbox-mgr`

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` selections MAY remain unchanged as named-set lists when those selections already include `mailbox-full`.

When those fixed selections resolve `mailbox-full`, the resolved installed skill list SHALL include `houmao-mailbox-mgr` together with the existing mailbox worker pair.

#### Scenario: Maintainer sees the packaged mailbox-admin skill and expanded full mailbox set
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-mailbox-mgr`
- **AND THEN** `mailbox-core` remains the two-skill mailbox worker pair
- **AND THEN** `mailbox-full` resolves the worker pair plus `houmao-mailbox-mgr`

#### Scenario: Existing fixed auto-install selections pick up the mailbox-admin skill through `mailbox-full`
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **AND WHEN** those fixed set lists still include `mailbox-full`
- **THEN** the resolved install selection includes `houmao-mailbox-mgr`
- **AND THEN** the change does not require a separate fixed auto-install set just to surface mailbox-administration guidance

### Requirement: Packaged system-skill catalog includes the advanced-usage skill and default set selection
The packaged current-system-skill catalog SHALL include `houmao-adv-usage-pattern` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-adv-usage-pattern` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set for that skill rather than folding it silently into an unrelated existing set.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` selections SHALL include that dedicated advanced-usage set so the packaged advanced skill is installed by default in managed homes and default external-home installs.

#### Scenario: Maintainer sees the advanced-usage skill in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-adv-usage-pattern`
- **AND THEN** the catalog defines a dedicated named set for that skill using the same flat packaged asset-path model as the other current skills

#### Scenario: Default install selections include the advanced-usage set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`
- **THEN** each fixed selection includes the dedicated advanced-usage set
- **AND THEN** the default resolved install list for managed homes and CLI-default installs includes `houmao-adv-usage-pattern`

### Requirement: Packaged system-skill catalog includes `houmao-touring` and a dedicated touring set
The packaged current-system-skill catalog SHALL include `houmao-touring` as a current installable Houmao-owned system skill.

That packaged skill SHALL use `houmao-touring` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set `touring` whose only member is `houmao-touring`.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` SHALL include the dedicated `touring` named set.

The packaged catalog SHALL keep `houmao-touring` in the dedicated `touring` set rather than folding it into `user-control`, `advanced-usage`, `agent-instance`, `agent-messaging`, or `agent-gateway`.

#### Scenario: Maintainer inspects the packaged catalog and sees the touring skill
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-touring`
- **AND THEN** the packaged catalog defines a dedicated `touring` named set containing only that skill

#### Scenario: Fixed default selections include the touring set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`
- **THEN** each fixed selection includes the dedicated `touring` named set
- **AND THEN** the touring skill becomes part of the resolved default packaged skill inventory without being folded into another named set

### Requirement: Packaged system-skill catalog includes `houmao-agent-inspect` and a dedicated inspect set
The packaged current-system-skill catalog SHALL include `houmao-agent-inspect` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-agent-inspect` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set `agent-inspect` whose only member is `houmao-agent-inspect`.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` SHALL include the dedicated `agent-inspect` named set.

The packaged catalog SHALL keep `houmao-agent-inspect` in the dedicated `agent-inspect` set rather than folding it into `user-control`, `agent-instance`, `agent-messaging`, or `agent-gateway`.

#### Scenario: Maintainer inspects the packaged catalog and sees the inspect skill
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-inspect`
- **AND THEN** the packaged catalog defines a dedicated `agent-inspect` named set containing only that skill

#### Scenario: Fixed default selections include the inspect set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`
- **THEN** each fixed selection includes the dedicated `agent-inspect` named set
- **AND THEN** the inspect skill becomes part of the resolved default packaged skill inventory without being folded into another named set

### Requirement: Packaged system-skill catalog includes both pairwise skill variants in `user-control`
The packaged current-system-skill catalog SHALL include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` as current installable Houmao-owned skills.

Each packaged skill SHALL use its skill name as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`

alongside the other user-control skills.

Because managed launch, managed join, and CLI-default installation already resolve `user-control`, those fixed auto-install selections SHALL pick up both pairwise skill variants through the expanded set membership.

#### Scenario: Maintainer sees both pairwise skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`
- **AND THEN** each skill uses its own flat packaged asset subpath under the maintained runtime asset root

#### Scenario: User-control expands to both pairwise variants
- **WHEN** a maintainer inspects the packaged `user-control` named set
- **THEN** that set resolves both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`
- **AND THEN** the set does not require a second pairwise-only named set to expose the versioned skill

#### Scenario: Auto-install picks up both pairwise variants through user-control
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved install lists now include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` without further conditional expansion

### Requirement: Packaged system-skill catalog replaces relay loop planner with generic loop planner
The packaged current-system-skill catalog SHALL include `houmao-agent-loop-generic` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-agent-loop-generic` as both its catalog key and its packaged `asset_subpath`.

The packaged current-system-skill catalog SHALL NOT include `houmao-agent-loop-relay` as a current installable skill after the generic replacement is introduced.

The packaged catalog's `user-control` named set SHALL include:

- `houmao-agent-loop-pairwise`,
- `houmao-agent-loop-pairwise-v2`,
- `houmao-agent-loop-generic`.

The packaged catalog's `user-control` named set SHALL NOT include `houmao-agent-loop-relay` after this replacement.

Because managed launch, managed join, and CLI-default installation already resolve `user-control`, those fixed auto-install selections SHALL pick up `houmao-agent-loop-generic` through the updated set membership.

#### Scenario: Maintainer sees generic loop skill in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-loop-generic`
- **AND THEN** the current installable skill inventory does not include `houmao-agent-loop-relay`

#### Scenario: User-control expands to the generic loop skill
- **WHEN** a maintainer inspects the packaged `user-control` named set
- **THEN** that set resolves `houmao-agent-loop-generic` alongside the pairwise loop skill variants
- **AND THEN** that set does not resolve `houmao-agent-loop-relay`

#### Scenario: Auto-install picks up the generic loop skill through user-control
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **THEN** those fixed auto-install selections still reference `user-control`
- **AND THEN** the resolved install lists include `houmao-agent-loop-generic` through `user-control`

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

### Requirement: Shared installer supports Copilot system-skill projection
The shared Houmao system-skill installer SHALL support Copilot as a current explicit installation target without adding Copilot-specific catalog entries.

For Copilot, the visible projected path relative to the resolved target home SHALL be `skills/<houmao-skill>/`.

The shared installer SHALL preserve the same selection, projection-mode, status-discovery, and owned-path replacement semantics for Copilot that it uses for other supported explicit tool homes.

#### Scenario: Explicit copy installation projects one selected current skill into a Copilot home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Copilot home without requesting symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as copied content
- **AND THEN** it does not require a copied project-local skill mirror outside the resolved Copilot home

#### Scenario: Explicit symlink installation projects one selected current skill into a Copilot home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Copilot home and explicitly requests symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as a directory symlink
- **AND THEN** the symlink target is the absolute filesystem path of the packaged skill asset directory

#### Scenario: Copilot status discovers installed current skills
- **WHEN** a resolved Copilot home contains current Houmao-owned system skills under `skills/<houmao-skill>/`
- **THEN** shared status discovery reports those current skill names
- **AND THEN** it reports whether each discovered current skill is projected as `copy` or `symlink`

### Requirement: Shared installer overwrites selected current skill projections without install state
The shared installer SHALL NOT create, read, validate, or update Houmao-owned install-state metadata inside the target tool home when installing current system skills.

For each selected current Houmao-owned skill, the installer SHALL compute the exact current tool-native projected destination path for that skill.

If that selected destination path already exists as a directory, file, or symlink, the installer SHALL remove it before projecting the packaged skill.

The installer SHALL then project the selected packaged skill into that destination using the requested projection mode:

- `copy` SHALL materialize the packaged skill tree as copied content,
- `symlink` SHALL create a directory symlink to the packaged skill asset root.

The installer SHALL limit destructive replacement to selected current skill destination paths. The installer SHALL NOT remove unselected skill directories, parent skill roots, legacy family-namespaced paths, unrelated tool-home content, or stale install-state files.

If explicit symlink projection is requested and the packaged skill asset directory cannot be addressed as a stable real filesystem directory path, installation SHALL fail explicitly and SHALL NOT silently fall back to copied projection.

#### Scenario: Reinstalling copied skills refreshes selected destinations without state
- **WHEN** Houmao installs the same selected current Houmao-owned skill set into the same target home more than once using copied projection
- **THEN** the installer replaces each selected skill's exact destination path with freshly copied packaged content
- **AND THEN** the target home does not require `.houmao/system-skills/install-state.json` for idempotent reinstall
- **AND THEN** the target home does not accumulate duplicate Houmao-owned skill trees

#### Scenario: Reinstall switches one selected skill from copied projection to symlink projection
- **WHEN** a target tool home already contains one selected current Houmao-owned skill as a copied directory
- **AND WHEN** the operator reinstalls that same skill into the same current tool-native path using symlink projection
- **THEN** the installer removes the copied directory
- **AND THEN** the installer creates the requested symlink entry at that same destination
- **AND THEN** no install-state metadata is written into the target home

#### Scenario: Existing selected Houmao skill path is overwritten without ownership proof
- **WHEN** the shared installer needs to project a selected current Houmao-owned skill path into a target home
- **AND WHEN** that projected path is already occupied by existing content
- **THEN** the installer removes the existing selected path without requiring current-schema Houmao-owned install-state proof
- **AND THEN** the installer projects the selected packaged skill into that path

#### Scenario: Unselected and unrelated content is preserved
- **WHEN** a target home contains an unselected skill directory, a legacy family-namespaced skill path, and an obsolete `.houmao/system-skills/install-state.json`
- **AND WHEN** Houmao installs a different selected current Houmao-owned skill
- **THEN** the installer replaces only the selected current skill destination path when needed
- **AND THEN** the unselected skill directory, legacy family-namespaced path, and obsolete install-state file remain untouched


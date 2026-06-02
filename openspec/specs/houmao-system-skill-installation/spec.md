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
- exactly two installable named skill sets, `core` and `all`, whose members are explicit current skill names,
- fixed auto-install set lists used by Houmao-managed homes and CLI default installation.

The `core` set SHALL contain the closed automation and operator-control system-skill surface. The `all` set SHALL contain every `core` skill plus packaged utility skills.

This change SHALL NOT require conditional rules, profile expansion, nested set expansion, aliases for removed set names, or other dynamic catalog evaluation beyond those fixed named sets and auto-install set lists.

The packaged current-skill catalog SHALL have one matching JSON Schema document, and loading SHALL validate the normalized catalog payload against that JSON Schema before any set expansion or install resolution proceeds.

For the current maintained skill set, each packaged skill `asset_subpath` SHALL equal the skill's own directory name under the maintained asset root and SHALL NOT include a family namespace segment such as `mailbox/` or `project/`.

Logical grouping of current skills MAY be expressed through documentation and set descriptions, but the installable named-set surface SHALL remain `core` and `all`.

#### Scenario: Maintainer inspects the packaged current-skill catalog
- **WHEN** a maintainer inspects the Houmao-owned packaged system-skill assets
- **THEN** the current `houmao-*` skills are available from one maintained runtime asset root
- **AND THEN** project starter assets remain in their own separate asset tree
- **AND THEN** one authoritative packaged catalog file identifies the current installable skill inventory, fixed auto-install set lists, explicit `schema_version`, and exactly the `core` and `all` named sets
- **AND THEN** each current packaged skill directory lives directly under that asset root using its skill name as the relative `asset_subpath`

#### Scenario: Catalog exposes closed core and all sets
- **WHEN** a maintainer inspects the packaged current-skill catalog
- **THEN** the `core` set resolves the closed automation and operator-control skill surface
- **AND THEN** the `all` set resolves every `core` skill plus packaged utility skills
- **AND THEN** removed granular set names such as `user-control`, `mailbox-full`, `mailbox-core`, `agent-memory`, `agent-instance`, `agent-messaging`, `agent-gateway`, `touring`, `agent-inspect`, and `utils` are not current installable named sets

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

- one or more current named skill sets,
- one or more explicitly selected current skill names.

The current installable named skill sets SHALL be `core` and `all`.

Whenever Houmao automatically installs its own current skills into a managed home, it SHALL use the packaged catalog's fixed auto-install set lists.

The packaged catalog SHALL set:

- `managed_launch_sets = ["core"]`
- `managed_join_sets = ["core"]`
- `cli_default_sets = ["all"]`

When installation input includes multiple named sets plus explicit skill names, the resolved install list SHALL preserve first occurrence order and SHALL contain each selected skill at most once.

That automatic or explicit selection SHALL NOT depend on conditional rule evaluation in this change.

#### Scenario: Managed brain construction uses the managed-launch auto-install set list
- **WHEN** Houmao constructs a managed home that performs default Houmao-owned skill installation
- **THEN** it installs the skill list resolved from the packaged current-skill catalog's `managed_launch_sets`
- **AND THEN** that fixed list is `["core"]`
- **AND THEN** that automatic selection does not depend on a second mailbox-only default list or any removed granular set

#### Scenario: Explicit installation resolves multiple named sets and explicit skills
- **WHEN** an operator explicitly selects `core` or `all` plus one current Houmao-owned skill for installation
- **THEN** the installer resolves the final install list by expanding the selected sets in order, appending the explicit skill, and deduplicating by first occurrence
- **AND THEN** it does not silently replace that explicit selection with an internal auto-install set list

#### Scenario: Unknown set fails explicit installation
- **WHEN** an operator explicitly selects one named set for installation
- **AND WHEN** that set name is not `core` or `all`
- **THEN** the installation fails explicitly
- **AND THEN** the installer does not guess another set or proceed with partial resolution

#### Scenario: Loader rejects a set that references an unknown skill
- **WHEN** Houmao loads the packaged current-skill catalog
- **AND WHEN** one named set references a skill name not present in the packaged skill inventory
- **THEN** catalog loading fails explicitly before installation begins
- **AND THEN** Houmao does not proceed with partial set expansion

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

### Requirement: Packaged system-skill catalog includes all pairwise variants in the current install sets
The packaged current-system-skill catalog SHALL include `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, and `houmao-agent-loop-pairwise-v4` as current installable Houmao-owned skills.

Each packaged skill SHALL use its skill name as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `core` named set SHALL include:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`
- `houmao-agent-loop-pairwise-v4`

alongside the other current managed-control skills.

The packaged catalog's `all` named set SHALL also include those four pairwise skills so CLI-default installation continues to expose the same family plus utility skills.

Because managed launch and managed join resolve `core`, and CLI-default installation resolves `all`, those fixed auto-install selections SHALL pick up all four pairwise skill variants through the expanded set membership.

#### Scenario: Maintainer sees all pairwise skills in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, and `houmao-agent-loop-pairwise-v4`
- **AND THEN** each skill uses its own flat packaged asset subpath under the maintained runtime asset root

#### Scenario: Core and all sets both expose all pairwise variants
- **WHEN** a maintainer inspects the packaged `core` and `all` named sets
- **THEN** each set resolves `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, and `houmao-agent-loop-pairwise-v4`
- **AND THEN** neither set requires a second pairwise-only named set to expose the workspace-aware versioned skill

#### Scenario: Auto-install picks up all pairwise variants through current set membership
- **WHEN** Houmao resolves auto-install skill selection through the packaged `core` and `all` memberships
- **THEN** the resolved install list includes `houmao-agent-loop-pairwise-v4`
- **AND THEN** the template-driven pairwise successor is available through the same packaged install path as the other current pairwise skills

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

### Requirement: Shared system-skill removal removes all current catalog-known projections
The system SHALL provide a shared removal contract for deleting Houmao-owned system-skill projections from one target tool home.

The removal contract SHALL load the packaged current-system-skill catalog and target every current skill name in catalog order.

For each current catalog-known skill, the removal contract SHALL compute the current tool-native destination path for the selected tool:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/<houmao-skill>/`
- Copilot: `skills/<houmao-skill>/`
- Gemini: `.gemini/skills/<houmao-skill>/`

When a computed target path exists as a directory, file, or symlink, the removal contract SHALL remove that exact path.

When a computed target path is missing, the removal contract SHALL record that path as absent and SHALL NOT fail.

The removal contract SHALL NOT create the target home, parent skill roots, or any missing skill path.

The removal contract SHALL NOT remove parent skill roots, unrelated tool-home content, unrecognized `houmao-*` paths, legacy family-namespaced paths, or obsolete `.houmao/system-skills/install-state.json` files.

The removal contract SHALL return enough structured information for callers to report removed skill names, removed projected relative dirs, absent skill names, and absent projected relative dirs.

#### Scenario: Shared removal deletes copied and symlink projections
- **WHEN** the shared removal contract runs for a Codex home
- **AND WHEN** that home contains current catalog-known Houmao skills under `skills/` as copied directories, symlinks, or files
- **THEN** those exact current skill paths are removed
- **AND THEN** the removal result reports them as removed

#### Scenario: Shared removal preserves unrelated and legacy paths
- **WHEN** the shared removal contract runs for a target home
- **AND WHEN** that home contains a custom user skill, a parent `skills/` root, a legacy family-namespaced Houmao path, and an obsolete install-state file
- **THEN** those paths remain in place
- **AND THEN** only exact current catalog-known Houmao skill projection paths are removed

#### Scenario: Shared removal is a no-op for a missing home
- **WHEN** the shared removal contract runs for a target home path that does not exist
- **THEN** it does not create that home path
- **AND THEN** it reports every current catalog-known Houmao skill projection path for that tool as absent

#### Scenario: Shared removal targets Gemini's `.gemini/skills` projection root
- **WHEN** the shared removal contract runs for a Gemini home
- **THEN** it targets current Houmao-owned skill paths under `.gemini/skills/`
- **AND THEN** it does not target `.agents/skills/` as the primary Houmao-owned system-skill removal root

### Requirement: LLM Wiki utility skill ships the all-in-one payload
The packaged `houmao-utils-llm-wiki` asset SHALL include the adapted all-in-one LLM Wiki skill instructions, references, scripts, subskills, and bundled viewer source.

The packaged skill SHALL keep helper command examples in `python3` form.

The packaged skill SHALL NOT preserve upstream attribution text.

#### Scenario: Maintainer inspects the packaged utility asset
- **WHEN** a maintainer inspects `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`
- **THEN** it contains `SKILL.md`, `references/`, `scripts/`, `subskills/`, and `viewer/`
- **AND THEN** helper examples use `python3`
- **AND THEN** the packaged skill text does not preserve upstream attribution text

### Requirement: Installable system-skill sets are closed over internal skill routing
Each installable named set in the packaged current-system-skill catalog SHALL be closed over internal system-skill routing references.

If a packaged skill included in a named set references another packaged catalog skill as a routing target from its Markdown skill instructions or subskill pages, that referenced skill SHALL also be included in the same set.

This closure requirement SHALL apply to every installable named set, including `core` and `all`.

#### Scenario: Catalog test catches an omitted internal routing target
- **WHEN** a packaged skill in `core` references another catalog skill from its Markdown instructions
- **AND WHEN** the referenced skill is omitted from `core`
- **THEN** catalog validation or regression coverage fails
- **AND THEN** maintainers must either add the referenced skill to `core` or remove the routing reference

### Requirement: Packaged utility skills are available through all
The packaged current-system-skill catalog SHALL include `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr` as current installable utility skills.

The `all` set SHALL include both utility skills.

The `core` set SHALL exclude utility skills unless a future change explicitly promotes a utility into the managed core surface.

The packaged catalog's fixed `cli_default_sets` selection SHALL include `all`, so omitted-selection explicit CLI installs include utility skills by default.

The packaged catalog's fixed `managed_launch_sets` and `managed_join_sets` selections SHALL include `core`, so managed launch and join do not install utility skills by default.

#### Scenario: CLI default includes utility skills
- **WHEN** an operator installs system skills into an external tool home without selecting `--skill-set` or `--skill`
- **THEN** the installer resolves `cli_default_sets = ["all"]`
- **AND THEN** the resolved skill list includes `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`

#### Scenario: Managed auto-install excludes utility skills
- **WHEN** Houmao installs system skills into a managed launch or join home
- **THEN** the installer resolves `core`
- **AND THEN** the resolved skill list excludes `houmao-utils-llm-wiki` and `houmao-utils-workspace-mgr`

### Requirement: Packaged catalog marks unified agent definition as canonical
The packaged current-system-skill catalog SHALL expose `houmao-agent-definition` as the canonical installable skill for pre-launch agent-definition, specialist, project-profile, raw recipe-backed profile, and fast-forward profile-preparation workflows.

The catalog SHALL NOT require default installations to include both canonical `houmao-agent-definition` and a separate canonical specialist-management skill.

If `houmao-specialist-mgr` remains packaged, the catalog SHALL mark or document it as a compatibility skill rather than as the canonical specialist-management surface.

#### Scenario: Maintainer inspects current skill inventory
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** `houmao-agent-definition` is the canonical current skill for specialist and profile authoring
- **AND THEN** `houmao-specialist-mgr`, if present, is not described as an independent canonical owner of those workflows

### Requirement: Packaged catalog exposes pro as the only current loop skill
The packaged current-system-skill catalog SHALL include `houmao-agent-loop-pro` as the only current Houmao-owned loop authoring and generated-loop execution skill.

The packaged current-system-skill catalog SHALL NOT include `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, `houmao-agent-loop-pairwise-v4`, `houmao-agent-loop-pairwise-v5`, or `houmao-agent-loop-generic` as current installable skills.

The `core` and `all` install sets SHALL include `houmao-agent-loop-pro` and SHALL NOT include retired loop skill names.

#### Scenario: Catalog lists only pro for loop authoring
- **WHEN** the packaged system-skill catalog is loaded
- **THEN** the current skill inventory includes `houmao-agent-loop-pro`
- **AND THEN** the current skill inventory does not include any retired pairwise or generic loop skill package

#### Scenario: Auto-install sets include pro
- **WHEN** managed launch, managed join, or CLI-default install selection resolves packaged skill sets
- **THEN** the resolved current skill list includes `houmao-agent-loop-pro`
- **AND THEN** it does not include retired loop skill names

### Requirement: Shared installer cleans known retired loop skill projections
The shared system-skill installer SHALL treat the retired loop skill names as known Houmao-owned retired projections:

- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`
- `houmao-agent-loop-pairwise-v4`
- `houmao-agent-loop-pairwise-v5`
- `houmao-agent-loop-generic`

For a selected target tool home, install and reinstall workflows SHALL remove exact projection paths for known retired loop skills while installing selected current skills.

The cleanup SHALL be limited to the exact tool-native projection paths for known retired Houmao-owned skill names.

#### Scenario: Reinstall removes stale retired loop skills
- **WHEN** one target tool home contains `skills/houmao-agent-loop-pairwise-v3/`
- **AND WHEN** the operator installs the current default Houmao system-skill set into that home
- **THEN** the installer removes the retired `houmao-agent-loop-pairwise-v3` projection
- **AND THEN** the installer creates or refreshes `houmao-agent-loop-pro`

#### Scenario: Cleanup does not remove unrelated user skills
- **WHEN** one target tool home contains an unrelated user skill
- **AND WHEN** current Houmao system skills are installed
- **THEN** the installer does not remove the unrelated user skill

### Requirement: Shared removal includes known retired loop projections
The shared system-skill uninstall workflow SHALL remove current catalog-known Houmao skill projections and known retired loop skill projections from the selected target tool home.

#### Scenario: Uninstall removes current and retired Houmao loop paths
- **WHEN** one target tool home contains `houmao-agent-loop-pro` and a stale `houmao-agent-loop-pairwise-v5`
- **AND WHEN** the operator uninstalls Houmao system skills for that home
- **THEN** both exact Houmao-owned loop projection paths are removed

### Requirement: Retired loop skill sources are preserved only as source legacy references
The repository SHALL preserve retired loop skill source trees under a source-only legacy reference directory below `src/`.

The packaged system-skill catalog, named install sets, auto-install selections, project-scope skill symlinks, and generated managed homes SHALL NOT reference retired loop skill source trees from that legacy directory.

The supported system-skill installer SHALL NOT install retired loop skills from the legacy directory.

#### Scenario: Retired source exists but is not packaged
- **WHEN** the repository contains a retired loop skill under the source-only legacy directory
- **THEN** the packaged current system-skill catalog does not include that retired skill name
- **AND THEN** install-set resolution does not project that legacy skill into target tool homes

#### Scenario: User manually handles legacy source
- **WHEN** a user intentionally copies or symlinks retired legacy skill source outside the supported Houmao installer path
- **THEN** that manual usage is outside current system-skill catalog support
- **AND THEN** current Houmao docs and routing guidance still identify `houmao-agent-loop-pro` as the maintained loop skill

### Requirement: Packaged catalog exposes pro and lite as current loop skills
The packaged current-system-skill catalog SHALL include both `houmao-agent-loop-pro` and `houmao-agent-loop-lite` as current Houmao-owned loop skills.

The packaged current-system-skill catalog SHALL continue to exclude retired loop skill package names such as `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, `houmao-agent-loop-pairwise-v4`, `houmao-agent-loop-pairwise-v5`, and `houmao-agent-loop-generic`.

The `core` and `all` install sets SHALL include both `houmao-agent-loop-pro` and `houmao-agent-loop-lite`.

#### Scenario: Catalog lists both maintained loop skills
- **WHEN** the packaged system-skill catalog is loaded
- **THEN** the current skill inventory includes `houmao-agent-loop-pro`
- **AND THEN** the current skill inventory includes `houmao-agent-loop-lite`
- **AND THEN** the current skill inventory does not include retired pairwise or generic loop package names

#### Scenario: Auto-install sets include both loop skills
- **WHEN** managed launch, managed join, or CLI-default install selection resolves packaged skill sets
- **THEN** the resolved current skill list includes `houmao-agent-loop-pro`
- **AND THEN** the resolved current skill list includes `houmao-agent-loop-lite`

### Requirement: Shared installer projects the lite skill as a normal current system skill
The shared system-skill installer SHALL project `houmao-agent-loop-lite` into target tool homes using the same current-skill projection rules as other catalog-known Houmao system skills.

The status and uninstall workflows SHALL treat `houmao-agent-loop-lite` as a current catalog-known skill.

Retired loop cleanup behavior SHALL remain limited to the known retired loop names and SHALL NOT treat `houmao-agent-loop-lite` as retired.

#### Scenario: Install projects lite into a Codex home
- **WHEN** an operator installs the current `core` set into a Codex home
- **THEN** the installer projects `skills/houmao-agent-loop-lite/`
- **AND THEN** status reports `houmao-agent-loop-lite` as a current installed skill

#### Scenario: Uninstall removes lite as current
- **WHEN** a resolved target home contains `houmao-agent-loop-lite`
- **AND WHEN** the operator uninstalls Houmao system skills for that home
- **THEN** the uninstall workflow removes the `houmao-agent-loop-lite` projection

### Requirement: Managed launch system-skill installation accepts resolved source policy
The managed-home system-skill installer SHALL support a resolved managed-launch selection policy derived from stored specialist, recipe, and launch-profile configuration.

When no stored policy is supplied, managed launch installation SHALL preserve the existing default behavior by resolving the packaged catalog's `auto_install.managed_launch_sets`.

The policy SHALL support additive, exact replacement, and disabled installation modes while continuing to validate all named set and explicit skill selectors against the packaged current system-skill catalog.

For reused managed homes, applying an exact replacement or disabled selection SHALL remove exact catalog-known current Houmao-owned system-skill projection paths that are not in the resolved selection, and SHALL preserve unrelated user skill paths.

#### Scenario: Omitted managed policy preserves core default
- **WHEN** Houmao constructs a managed home without a stored system-skill policy
- **THEN** it installs the skill list resolved from the packaged catalog's `managed_launch_sets`
- **AND THEN** existing managed-launch defaults remain unchanged

#### Scenario: Additive managed policy installs one utility skill
- **WHEN** managed launch resolves an additive system-skill policy containing explicit skill `houmao-utils-llm-wiki`
- **THEN** the installer resolves the packaged managed-launch default selection
- **AND THEN** it appends `houmao-utils-llm-wiki` to the installed skill list without duplicating any skill name

#### Scenario: Replacement managed policy installs exact all set
- **WHEN** managed launch resolves an exact replacement system-skill policy containing set `all`
- **THEN** the installer installs the skills resolved from `all`
- **AND THEN** it does not implicitly add the packaged `managed_launch_sets` selection a second time

#### Scenario: Disabled managed policy removes stale Houmao-owned system skills
- **WHEN** a reused Codex managed home contains `skills/houmao-utils-llm-wiki/` from an earlier launch
- **AND WHEN** managed launch resolves disabled system-skill installation for that home
- **THEN** the managed-home sync removes exact current Houmao-owned system-skill paths from the home
- **AND THEN** it preserves unrelated non-Houmao skill paths under the tool skill root

#### Scenario: Unknown managed policy selector fails before mutation
- **WHEN** managed launch resolves a system-skill policy containing unknown set `utilities`
- **THEN** validation fails before mutating the managed home
- **AND THEN** the error identifies the unknown system-skill set selector

### Requirement: Packaged catalog includes the operator messaging skill in default control sets
The packaged current-system-skill catalog SHALL include `houmao-operator-messaging` as a current installable Houmao-owned system skill.

That packaged skill SHALL use `houmao-operator-messaging` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `core` named set SHALL include `houmao-operator-messaging` because it is part of the closed operator-control skill surface.

The packaged catalog's `all` named set SHALL include `houmao-operator-messaging` because `all` includes every `core` skill plus packaged utility skills.

The packaged catalog SHALL NOT add a dedicated named set for `houmao-operator-messaging`; the current installable named-set surface SHALL remain `core` and `all`.

Because managed launch and managed join resolve `core`, and CLI-default installation resolves `all`, those fixed auto-install selections SHALL include `houmao-operator-messaging` through existing set membership.

#### Scenario: Maintainer sees operator messaging in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-operator-messaging`
- **AND THEN** the skill uses `houmao-operator-messaging` as its flat packaged asset subpath under the maintained runtime asset root

#### Scenario: Core and all sets expose operator messaging
- **WHEN** a maintainer inspects the packaged `core` and `all` named sets
- **THEN** both sets include `houmao-operator-messaging`
- **AND THEN** no additional operator-messaging-specific named set is present

#### Scenario: Default installs include operator messaging through existing sets
- **WHEN** Houmao resolves packaged skill installation for managed launch, managed join, or CLI-default installation
- **THEN** the resolved install list includes `houmao-operator-messaging`
- **AND THEN** that inclusion comes from the existing `core` or `all` set expansion


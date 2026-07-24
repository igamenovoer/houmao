## Purpose
Define packaged catalog, selection, projection, and install-state behavior for the current Houmao-owned system-skill set.
## Requirements
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

### Requirement: Shared installer supports the universal Agent Skills projection target
The shared system-skill installer SHALL support `universal` as an explicit installation target for Houmao-owned system skills.

For the `universal` target, the visible projected paths SHALL use the cross-client Agent Skills root:

- Universal: `skills/<houmao-skill>/` under the resolved universal home root, which defaults to `~/.agents` for the operator CLI.

The shared installer SHALL apply the same current-skill selection, retired-skill cleanup, status discovery, uninstall, copied projection, and symlink projection behavior to the `universal` target that it applies to existing `skills/`-root targets.

The `universal` target SHALL NOT imply a runtime tool adapter, credential home, launch backend, or managed-agent provider.

Houmao-managed launch and managed join flows SHALL continue installing managed system skills into the selected runtime tool home and SHALL NOT silently duplicate those skills into the `universal` target.

#### Scenario: Explicit universal copy installation projects selected skills under skills root
- **WHEN** Houmao installs selected current system skills for target `universal` into resolved home `/home/alice/.agents` without symlink projection
- **THEN** each selected skill is copied under `/home/alice/.agents/skills/<houmao-skill>/`
- **AND THEN** the result reports projected relative directories under `skills/`

#### Scenario: Explicit universal symlink installation uses existing projection mode
- **WHEN** Houmao installs one selected current system skill for target `universal` with symlink projection
- **THEN** the projected path is `skills/<houmao-skill>/`
- **AND THEN** that path is a directory symlink to the packaged skill asset root

#### Scenario: Universal uninstall removes only universal projections
- **WHEN** Houmao uninstalls system skills for target `universal` with resolved home `/home/alice/.agents`
- **THEN** it removes current and retired Houmao-owned projections under `/home/alice/.agents/skills/`
- **AND THEN** it does not remove projections from `.codex/skills/`, `.kimi-code/skills/`, `.gemini/skills/`, `.github/skills/`, or `.claude/skills/`

#### Scenario: Managed runtime install does not write universal target
- **WHEN** Houmao builds or joins a managed runtime home for one concrete agent tool
- **THEN** managed system skills are installed into that runtime tool home's native projection root
- **AND THEN** Houmao does not also install those skills into `~/.agents/skills`

### Requirement: Kimi system-skill projection targets Kimi Code CLI homes
The shared system-skill target `kimi` SHALL refer to Kimi Code CLI.

For the `kimi` target, the visible projected paths SHALL use `skills/<houmao-skill>/` under the resolved Kimi Code home, including `$KIMI_CODE_HOME/skills/<houmao-skill>/` when Kimi Code is launched with that home and the project default `.kimi-code/skills/<houmao-skill>/` when Houmao resolves a project-scoped Kimi Code home.

The `kimi` target SHALL NOT represent the legacy MoonshotAI `kimi-cli` project as a separate installation profile.

#### Scenario: Kimi projection uses the resolved Kimi Code home skills root
- **WHEN** Houmao installs selected current system skills for target `kimi` into resolved Kimi Code home `/tmp/kimi-home`
- **THEN** each selected skill is projected under `/tmp/kimi-home/skills/<houmao-skill>/`
- **AND THEN** the projected relative directory is `skills/<houmao-skill>`

#### Scenario: Kimi and universal targets remain separate
- **WHEN** Houmao installs selected current system skills for target `kimi`
- **THEN** it does not install those skills into `~/.agents/skills`
- **AND WHEN** Houmao installs selected current system skills for target `universal`
- **THEN** it does not install those skills into the resolved Kimi Code home

### Requirement: Removed LLM Wiki system skill is outside Houmao-owned inventory
The packaged system-skill catalog SHALL NOT include `houmao-utils-llm-wiki` as a current skill, set member, auto-install selection member, or retired Houmao-owned skill name.

System-skill install, sync, status, and uninstall workflows SHALL NOT treat `skills/houmao-utils-llm-wiki/` or equivalent tool-native projection paths as current or retired Houmao-owned projections.

#### Scenario: Catalog omits the removed LLM Wiki skill
- **WHEN** the packaged system-skill catalog is loaded
- **THEN** `houmao-utils-llm-wiki` is absent from the current skill inventory
- **AND THEN** `houmao-utils-llm-wiki` is absent from every named set and auto-install selection
- **AND THEN** `houmao-utils-llm-wiki` is absent from `retired_skill_names`

#### Scenario: Stale LLM Wiki projection is outside automatic cleanup
- **WHEN** a target tool home contains `skills/houmao-utils-llm-wiki/`
- **AND WHEN** Houmao installs, syncs, inspects, or uninstalls Houmao-owned system skills for that home
- **THEN** the stale LLM Wiki path is not reported as a current or retired Houmao-owned skill
- **AND THEN** the stale LLM Wiki path is not removed by Houmao-owned system-skill cleanup

### Requirement: System-skill policy does not control managed auto skills
Houmao system-skill installation, status, sync, and removal workflows SHALL manage only catalog-known Houmao system skills.

Managed auto skills SHALL remain outside system-skill catalog selection, named sets, CLI-default installation, managed-launch system-skill policy, and explicit uninstall behavior.

Disabling or replacing system-skill selection for a managed launch SHALL NOT disable a required managed auto skill.

#### Scenario: Disabled system-skill selection leaves auto skill eligible
- **WHEN** managed launch resolves disabled system-skill installation for a home
- **AND WHEN** launch policy requires `houmao-auto-system-prompt`
- **THEN** system-skill installation resolves no system skills
- **AND THEN** auto-skill projection remains eligible through the separate managed auto-skill projection path

#### Scenario: System-skill uninstall does not remove auto skill by catalog sweep
- **WHEN** an operator runs a Houmao system-skill uninstall workflow for a tool home
- **THEN** the workflow targets catalog-known current or retired system-skill projections
- **AND THEN** it does not treat `houmao-auto-system-prompt` as a system-skill catalog entry

#### Scenario: System-skill status omits auto-skill inventory
- **WHEN** an operator inspects system-skill status for a tool home
- **THEN** the status reports catalog-known Houmao system skills
- **AND THEN** it does not report `houmao-auto-system-prompt` as an installed system skill

### Requirement: Shared system-skill projection has no Gemini destination
The shared system-skill installer, status discovery, synchronization, and removal contracts SHALL NOT recognize Gemini or `.gemini/skills` as a Houmao target.

#### Scenario: Gemini projection root is absent from destination resolution
- **WHEN** the system resolves supported tool-native skill destinations
- **THEN** no mapping points to `.gemini/skills`
- **AND THEN** Gemini is rejected before filesystem mutation

### Requirement: Lifecycle operations do not enforce skill release metadata
System-skill install, sync, upgrade, status, uninstall, managed launch, rebuild, relaunch, join, prompt generation, and skill invocation SHALL NOT require or compare installed `houmao_version` values.

Copy projection SHALL preserve the checked-in frontmatter bytes. Symlink projection SHALL expose the checked-in source unchanged. The manifest, skill config, content digest, ownership, policy, and transaction rules SHALL remain authoritative for lifecycle operations.

#### Scenario: Existing installation has no version field
- **WHEN** a lifecycle operation encounters an installed root without `houmao_version`
- **THEN** it applies the current config, content, ownership, and conflict rules
- **AND THEN** it does not fail solely because version metadata is missing

#### Scenario: Installed version differs from running Houmao
- **WHEN** managed launch or synchronization encounters a version mismatch
- **THEN** version equality does not become a lifecycle precondition
- **AND THEN** only an explicit doctor invocation reports the mismatch as version evidence

### Requirement: Version metadata remains diagnostic in lifecycle configuration
The v4 system-skill manifest SHALL remain the static collection authority. `houmao-skill-config.v1` SHALL record one collection-level `houmao_version` and complete-tree digests without duplicating a required per-skill release field.

Doctor SHALL read each installed root's frontmatter directly and SHALL NOT migrate or rewrite the skill config while diagnosing versions.

#### Scenario: Current pack is installed with release metadata
- **WHEN** install projects a versioned standalone root
- **THEN** its complete-tree digest naturally covers the frontmatter bytes
- **AND THEN** the config records the installing Houmao release separately from per-root frontmatter

#### Scenario: Doctor reads a current config
- **WHEN** doctor examines a lifecycle-managed home
- **THEN** it leaves the config bytes unchanged
- **AND THEN** it reads observed skill versions from installed `SKILL.md` files

### Requirement: Houmao stores minimal system-skill ownership configuration
The system SHALL store manager-owned system-skill lifecycle state at `<tool-home>/.houmao/system-skills/<tool>/houmao-skill-config.json` using schema `houmao-skill-config.v1`.

The top-level payload SHALL contain exactly `schema_version`, `houmao_version`, `projection_mode`, and `skills`. Each installed-skill record SHALL contain exactly `name`, `relative_path`, `content_digest`, and `owning_pack_ids`. The configuration SHALL NOT duplicate its tool, home path, manifest schema, selected pack set, timestamps, operation history, skill role, activation posture, per-skill projection mode, per-skill release version, or source path.

The selected installed pack set SHALL be derived from the manifest-ordered union of per-skill `owning_pack_ids`. The parser SHALL reject malformed, unknown, duplicate, unsafe, empty, or internally inconsistent state.

#### Scenario: Fresh admin symlink installation writes minimal config
- **WHEN** Houmao installs the static admin pack into a clean Kimi home in symlink mode
- **THEN** it writes `houmao-skill-config.json` below the Kimi tool-scoped Houmao state directory
- **AND THEN** the config records the installing Houmao release and `symlink` collection mode
- **AND THEN** its skill records identify the five installed roots, their relative paths, content digests, and admin ownership
- **AND THEN** it contains no field outside the strict minimal schema

#### Scenario: Combined installation derives both packs
- **WHEN** a valid config contains the six unique roots belonging to the installed admin and agent packs
- **THEN** the lifecycle derives `admin` and `agent` from the member owner sets
- **AND THEN** the three shared roots record both owners without a serialized selected-pack field

### Requirement: Skill config is the sole source of manager ownership
Install, sync, status, upgrade, and uninstall SHALL treat only a valid `houmao-skill-config.json` as persisted manager ownership evidence. A same-name destination without that config ownership SHALL remain an unowned collision and SHALL NOT be overwritten or deleted implicitly.

Lifecycle mutations SHALL commit and validate affected projections before atomically writing the config. Rollback SHALL restore the preceding new-format config and affected projection state. Partial uninstall SHALL subtract the requested pack owner and retain roots that have another owner; final uninstall SHALL remove the config rather than persist an empty skill list.

#### Scenario: Partial uninstall retains shared roots
- **WHEN** admin and agent ownership are installed and the operator uninstalls agent
- **THEN** the agent entrypoint is removed if unchanged
- **AND THEN** shared routines and both loop roots remain owned by admin
- **AND THEN** the rewritten config derives only the admin pack

#### Scenario: Final uninstall removes config
- **WHEN** the last installed pack is uninstalled from an unchanged managed collection
- **THEN** its final-owner projections are removed
- **AND THEN** `houmao-skill-config.json` is removed
- **AND THEN** no empty config is written

### Requirement: Receipt persistence is unsupported
The system SHALL NOT probe, read, parse, migrate, delete, or report any `receipt.json` as current system-skill lifecycle state. Receipt schema identifiers and receipt-specific inspection states SHALL NOT be part of the current lifecycle model.

Users with a receipt-based installation MUST remove or uninstall that installation and perform a clean reinstall before the new lifecycle can manage it.

#### Scenario: Old receipt and projected roots remain unowned
- **WHEN** a tool home contains `receipt.json` and old projected Houmao skill roots but no `houmao-skill-config.json`
- **THEN** the current lifecycle ignores `receipt.json`
- **AND THEN** it treats the projected roots as unowned collisions
- **AND THEN** installation fails without overwriting or deleting them

#### Scenario: Old receipt alone is ignored
- **WHEN** a tool home contains `receipt.json` but no projected Houmao skill roots and no new config
- **THEN** status reports no current config ownership
- **AND THEN** the lifecycle does not remove or rewrite the old file

### Requirement: Shared installer resolves audience packs rather than peer skill sets
The shared system-skill installer SHALL accept one or more pack ids and SHALL resolve each id to its complete static standalone membership.

CLI-default external-home installation SHALL resolve the five-member `admin` pack. Managed launch, rebuild, relaunch, and join SHALL resolve the four-member `agent` pack. Explicit repeated selection MAY resolve both packs, but SHALL NOT merge their actor identities or create duplicate shared destinations.

#### Scenario: External install omits selectors
- **WHEN** an operator installs Houmao system skills into an external supported tool home without a pack selector
- **THEN** the installer resolves the complete admin pack
- **AND THEN** it installs welcome, admin entrypoint, shared routines, pro loop, and lite loop

#### Scenario: Managed launch uses agent default
- **WHEN** managed launch resolves default Houmao system-skill installation
- **THEN** it resolves only the agent pack
- **AND THEN** it installs agent entrypoint, shared routines, pro loop, and lite loop without either admin root

### Requirement: Shared installer projects complete public skills into supported tool homes
The shared installer SHALL project complete standalone public skill directories at the tool-native top-level skill root for Claude, Codex, Copilot, Kimi, and the universal Agent Skills target.

Shared routines and both loop skills SHALL remain top-level siblings of the selected actor entrypoint. The sixteen shared children SHALL remain parent-scoped below `houmao-shared-routines/subskills/`. Copy SHALL remain the default mode, managed homes SHALL use copy, and explicit symlink mode SHALL link each complete standalone source directory.

#### Scenario: Codex admin pack uses static top-level paths
- **WHEN** the admin pack is installed into a Codex home
- **THEN** all five admin-pack members appear as top-level siblings under `skills/`
- **AND THEN** no entrypoint-local composition tree is created

#### Scenario: Kimi managed home receives the static agent pack
- **WHEN** Houmao installs the managed default into a Kimi Code CLI home
- **THEN** all four agent-pack members appear as top-level siblings under `skills/`
- **AND THEN** shared children remain below the shared-routines sibling

### Requirement: Managed system-skill policy selects packs
Stored source and launch-profile system-skill policy SHALL retain the supported policy modes `default`, `inherit`, `extend`, `replace`, and `none` where each lane permits them, but SHALL store and resolve `packs` rather than `sets` and `skills`.

The policy resolver SHALL reject unknown pack ids, invalid mode and selector combinations, and any attempt to select a protected logical id as an install unit. System-skill policy SHALL continue to exclude managed auto skills.

#### Scenario: Profile extends source policy with admin pack
- **WHEN** a valid profile policy extends a source selection with the admin pack
- **THEN** the resolver returns complete, deduplicated pack ids in first-occurrence order
- **AND THEN** protected members are derived from the manifest rather than persisted as selectors

#### Scenario: Policy selects a protected logical id
- **WHEN** stored policy names `houmao-agent-inspect` as if it were an installable pack
- **THEN** policy validation fails
- **AND THEN** managed home construction does not begin

### Requirement: Shared installer resolves packs to static standalone members
The shared system-skill installer SHALL resolve the `admin` and `agent` pack ids to deduplicated standalone skill records from the v4 manifest.

The admin pack SHALL resolve to `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`. The agent pack SHALL resolve to `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`.

#### Scenario: Both packs are selected
- **WHEN** an operator explicitly selects both admin and agent packs
- **THEN** the installer resolves six unique standalone skills
- **AND THEN** shared routines and both loop skills occur once in first-occurrence order

### Requirement: Installation stages complete static directories
Copy installation SHALL stage an unmodified recursive copy of each selected public source directory. Symlink installation SHALL link each top-level destination directly to the corresponding complete public source directory.

The installer SHALL NOT call a Markdown composer, create nested mounts, render actor names, filter shared children, or create a hidden materialized skill tree. It SHALL validate the complete static union before committing any destination change.

#### Scenario: Static source contains an invalid child link
- **WHEN** validation finds a broken local link in one selected static skill
- **THEN** installation fails before committing any destination path
- **AND THEN** no partially installed pack or skill config is written

### Requirement: One installed collection uses one projection mode
A config-owned static collection SHALL use one projection mode for all owned members. A later operation requesting a different mode SHALL perform an explicit transactional replacement of the selected installed union or fail before mutation.

#### Scenario: Agent pack shares copied dependencies with admin
- **WHEN** admin is already installed in copy mode and agent is added in copy mode
- **THEN** the three shared paths remain copied once
- **AND THEN** their config owner sets include both packs

### Requirement: Managed defaults install the complete static agent pack
Managed launch, rebuild, relaunch, and join SHALL install or synchronize the complete static agent pack in copy mode unless valid policy disables or replaces that selection.

The managed home SHALL contain the agent entrypoint, shared routines, pro loop, and lite loop as top-level siblings. Admin welcome and admin entrypoint SHALL remain absent by default.

#### Scenario: Managed launch uses omitted system-skill policy
- **WHEN** a new managed home is built with the default selection
- **THEN** all four static agent-pack members are copied into the tool-native root
- **AND THEN** no runtime composition directory or admin public skill is created

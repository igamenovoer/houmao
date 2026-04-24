# houmao-mgr-project-migrate-cli Specification

## Purpose
TBD - created by archiving change source-aware-project-assets. Update Purpose after archive.
## Requirements
### Requirement: `houmao-mgr project migrate` provides an explicit project-structure migration surface
`houmao-mgr` SHALL expose `project migrate` as the supported command for upgrading known legacy project structures into the current `houmao-mgr project` model.

`project migrate` SHALL resolve the active project overlay using the same project-aware overlay selection rules as other project commands.

The command SHALL support a non-destructive planning path and an explicit apply path.

The plan output SHALL identify:

- the selected overlay root,
- the detected legacy project state or migration steps,
- the planned writes, moves, removals, or replacements,
- whether the migration can be applied automatically.

#### Scenario: Project migrate shows a plan before mutation
- **WHEN** the selected project overlay contains one supported legacy project structure
- **AND WHEN** an operator runs `houmao-mgr project migrate`
- **THEN** the command reports the detected migration plan without mutating project files
- **AND THEN** the reported plan identifies the affected project paths and migration steps

### Requirement: Successful migration refreshes the overlay in place without preserving legacy project files
When `houmao-mgr project migrate --apply` succeeds, the selected project overlay SHALL be refreshed to the latest supported project structure in place.

The command SHALL NOT keep migrated legacy project files or directories as a second supported mirror after successful migration.

The command SHALL NOT provide a built-in project-backup workflow as part of the maintained migration contract.

#### Scenario: Successful migration removes replaced legacy project state
- **WHEN** the selected project overlay contains one supported legacy specialist metadata file or compatibility-tree-first project skill path
- **AND WHEN** an operator runs `houmao-mgr project migrate --apply`
- **THEN** the command writes the current supported project state
- **AND THEN** it removes the replaced legacy project files or directories instead of keeping them as a second live mirror

#### Scenario: Migration contract does not include built-in backup
- **WHEN** an operator checks the supported `project migrate` behavior
- **THEN** the command contract does not include automatic backup creation
- **AND THEN** the operator remains responsible for taking any desired backup before applying migration

### Requirement: `project migrate` applies only named supported migrations
`houmao-mgr project migrate --apply` SHALL execute only the named supported project-structure migrations recognized by the current Houmao version.

At minimum, the initial supported migration set SHALL include:

- legacy `.houmao/easy/specialists/*.toml` specialist metadata into the current catalog-backed specialist model,
- compatibility-tree-first project skill state into canonical `.houmao/content/skills/<name>` entries plus derived `.houmao/agents/skills/` projection.

The command SHALL NOT attempt best-effort migration for unknown or unsupported project layouts.

#### Scenario: Project migrate imports legacy easy-specialist metadata
- **WHEN** the selected project overlay contains legacy `.houmao/easy/specialists/researcher.toml`
- **AND WHEN** an operator runs `houmao-mgr project migrate --apply`
- **THEN** the command imports that specialist into the current catalog-backed specialist model
- **AND THEN** the command reports that the legacy specialist metadata was migrated explicitly through `project migrate`

#### Scenario: Project migrate upgrades canonical project skill storage explicitly
- **WHEN** the selected project overlay contains compatibility-tree-first project skill content that maps to current project skill registrations
- **AND WHEN** an operator runs `houmao-mgr project migrate --apply`
- **THEN** the command creates canonical `.houmao/content/skills/<name>` entries for the migrated skills
- **AND THEN** later compatibility projection treats `.houmao/agents/skills/` as derived state only
- **AND THEN** the migration does not keep the previous compatibility-tree-first project skill layout as a second supported source-of-truth mirror

### Requirement: Unsupported project states fail clearly during migration
When the selected project overlay does not match one supported migration shape, `project migrate` SHALL fail clearly instead of attempting an unbounded in-place rewrite.

The failure SHALL distinguish unsupported migration state from ordinary missing-overlay cases.

#### Scenario: Project migrate rejects unknown legacy structure
- **WHEN** the selected project overlay contains one structurally incompatible or unknown legacy project state
- **AND WHEN** an operator runs `houmao-mgr project migrate --apply`
- **THEN** the command fails clearly
- **AND THEN** the diagnostic explains that the current Houmao version does not support automatic migration for that project state

### Requirement: `project migrate` preserves external source trees during canonicalization
When `houmao-mgr project migrate --apply` imports legacy project skill or related content into the current overlay model, the command SHALL treat repo-owned or otherwise external source paths as read-only inputs.

`project migrate` SHALL mutate only Houmao-managed overlay artifact paths while canonicalizing content under `.houmao/`.

#### Scenario: Canonicalizing a legacy symlink-backed skill preserves the repo source directory
- **WHEN** the selected project overlay still exposes one legacy compatibility-tree skill entry that resolves to one repo-owned source directory
- **AND WHEN** an operator runs `houmao-mgr project migrate --apply`
- **THEN** the command creates or refreshes canonical managed skill content under `.houmao/content/skills/`
- **AND THEN** the repo-owned source directory remains intact

#### Scenario: Failed migration does not consume source content
- **WHEN** one supported migration step reads legacy compatibility-tree content from one external or repo-owned source path
- **AND WHEN** `houmao-mgr project migrate --apply` fails after mutating only Houmao-managed overlay artifacts
- **THEN** the source path remains intact

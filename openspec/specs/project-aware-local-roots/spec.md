# project-aware-local-roots Specification

## Purpose
TBD - created by archiving change make-operations-project-aware. Update Purpose after archive.
## Requirements
### Requirement: Project-aware local commands resolve one active overlay before using local Houmao-owned state
Maintained local Houmao command flows that need Houmao-owned local state SHALL resolve one active project overlay using this precedence:

1. explicit CLI overlay selection,
2. `HOUMAO_PROJECT_OVERLAY_DIR`,
3. nearest ancestor discovered project overlay within the current Git worktree boundary,
4. bootstrap `<cwd>/.houmao` when no overlay exists and the command requires local Houmao-owned state.

The current Git worktree boundary SHALL be inferred by walking ancestors from the invocation directory until the nearest ancestor containing a `.git` file or directory. When no ancestor contains `.git`, discovery MAY continue to the filesystem root.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When explicit CLI selection is supplied, it SHALL win over env and discovery.
Commands that only need to report selection state MAY report the selected overlay root without forcing bootstrap.
When a command bootstraps an overlay through rule 4, it SHALL surface the created overlay root in operator-facing output or structured payload data for that invocation.

#### Scenario: Explicit CLI overlay selection wins
- **WHEN** an operator supplies an explicit CLI overlay root
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is also set
- **THEN** the command uses the explicitly selected overlay root
- **AND THEN** it does not replace that selection with the env-selected overlay

#### Scenario: Nearest ancestor overlay is reused when no override exists
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs a maintained local Houmao command from `/repo/subdir/nested`
- **THEN** the command uses `/repo/.houmao` as the active overlay
- **AND THEN** it does not bootstrap `/repo/subdir/nested/.houmao`

#### Scenario: Discovery does not cross the current Git worktree boundary
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/parent/.houmao/houmao-config.toml` exists
- **AND WHEN** `/parent/nested-repo/.git` exists
- **AND WHEN** no `.houmao/houmao-config.toml` exists between `/parent/nested-repo` and its Git worktree root
- **AND WHEN** an operator runs a maintained local Houmao command from `/parent/nested-repo/app`
- **THEN** the command does not reuse `/parent/.houmao`
- **AND THEN** it bootstraps or selects `/parent/nested-repo/.houmao` according to the normal precedence rules

#### Scenario: Missing overlay bootstraps under the current working directory
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** no ancestor project overlay exists
- **AND WHEN** an operator runs a maintained local Houmao command that requires local Houmao-owned state from `/repo/app`
- **THEN** the command bootstraps `/repo/app/.houmao`
- **AND THEN** that bootstrapped overlay becomes the active project overlay for the command
- **AND THEN** the command reports that `/repo/app/.houmao` was created for the invocation

### Requirement: Project-aware local roots default under the active overlay except registry
When a maintained local Houmao command runs in project context without a stronger explicit or env-var override, the effective local roots SHALL derive from the active project overlay as:

- agent-definition root: `<overlay>/agents`
- runtime root: `<overlay>/runtime`
- jobs root: `<overlay>/jobs`
- mailbox root: `<overlay>/mailbox`
- easy root: `<overlay>/easy`

The shared registry SHALL remain outside the project overlay by default at `~/.houmao/registry`, unless the existing registry env override redirects it.
For this change, `runtime/`, `jobs/`, `mailbox/`, and `easy/` SHALL remain convention-derived overlay subpaths rather than new configurable `houmao-config.toml` path keys.

#### Scenario: Project-aware runtime and jobs roots derive from the overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** no explicit runtime-root or jobs-root override is supplied
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** the effective jobs root is `/repo/.houmao/jobs`

#### Scenario: Shared registry remains global by default
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** no registry override is supplied
- **THEN** the effective shared registry root remains `~/.houmao/registry`
- **AND THEN** the command does not relocate the registry under `/repo/.houmao/registry`

#### Scenario: Project config can still customize agents without changing the fixed overlay subpaths
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` sets `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** no stronger runtime-root, jobs-root, or mailbox-root override exists
- **THEN** the effective agent-definition root resolves under `/repo/.houmao/custom-agents`
- **AND THEN** the effective runtime, jobs, mailbox, and easy roots remain `/repo/.houmao/runtime`, `/repo/.houmao/jobs`, `/repo/.houmao/mailbox`, and `/repo/.houmao/easy`


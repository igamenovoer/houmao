## MODIFIED Requirements

### Requirement: Project-aware agent-definition defaults discover the nearest project config
Project-aware command paths that need an effective local Houmao project overlay or an effective filesystem agent-definition root and are invoked without explicit local-root overrides SHALL resolve that state in this order:

1. explicit CLI overlay or agent-definition override,
2. `HOUMAO_PROJECT_OVERLAY_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml` within the current Git worktree boundary,
4. bootstrap `<cwd>/.houmao` when no project overlay exists and the command requires local Houmao-owned state.

The current Git worktree boundary SHALL be inferred by walking ancestors until the nearest directory containing a `.git` file or directory. When no ancestor contains `.git`, discovery MAY continue to the filesystem root.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When a project overlay is selected, the effective default agent-definition root SHALL be `<overlay-root>/agents` unless a discovered config resolves a different compatibility-projection path.
When a project config is discovered, relative paths stored in that config SHALL resolve relative to the config file directory.
When a project config is discovered for a catalog-backed overlay, pair-native build and launch paths SHALL materialize the compatibility projection from that overlay's catalog and managed content store before reading presets, role prompts, or tool content.
Pure discovery and status paths MAY report the resolved compatibility-projection root without forcing materialization.

At minimum, this project-aware defaulting SHALL apply to:

- `houmao-mgr project ...`
- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`
- maintained local mailbox, cleanup, and server command flows that need local Houmao-owned roots

#### Scenario: Nearest discovered overlay remains the default project anchor
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs a project-aware local command from `/repo/subdir`
- **THEN** the command resolves `/repo/.houmao` as the active project overlay
- **AND THEN** it does not bootstrap `/repo/subdir/.houmao`

#### Scenario: Nested Git repos do not inherit a parent repo overlay implicitly
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/parent/.houmao/houmao-config.toml` exists
- **AND WHEN** `/parent/child/.git` exists
- **AND WHEN** an operator runs a project-aware local command from `/parent/child/subdir`
- **AND WHEN** `/parent/child/.houmao/houmao-config.toml` does not exist
- **THEN** the command does not resolve `/parent/.houmao` as the active project overlay
- **AND THEN** it bootstraps `/parent/child/.houmao` if the command requires local Houmao-owned state

#### Scenario: Missing overlay bootstraps under the current working directory
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs a project-aware local command that needs local Houmao-owned state from `/repo/app`
- **THEN** the command bootstraps `/repo/app/.houmao`
- **AND THEN** it uses `/repo/app/.houmao/agents` as the effective default agent-definition root

## ADDED Requirements

### Requirement: Maintained local project-aware commands no longer require prior manual project init
Maintained local command flows that require Houmao-owned project-local state SHALL ensure the active overlay exists before performing their primary work instead of requiring the operator to run `houmao-mgr project init` as a separate prerequisite step.

This change SHALL NOT remove `houmao-mgr project init`; the command remains the explicit bootstrap and validation surface.

#### Scenario: Build or launch can create the missing overlay on demand
- **WHEN** no active project overlay exists for the caller
- **AND WHEN** an operator runs a maintained local Houmao build or launch command that needs project-local state
- **THEN** the command ensures the selected overlay exists before continuing
- **AND THEN** the operator does not need to run `houmao-mgr project init` manually first

### Requirement: `houmao-mgr project status` remains a read-only reporting surface
`houmao-mgr project status` SHALL report the selected project overlay root and derived project-aware local roots without bootstrapping a missing overlay.

When no overlay exists yet, the command SHALL report the would-bootstrap overlay root for the current invocation context rather than creating it.

#### Scenario: Project status reports the would-bootstrap overlay without creating it
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/app`
- **THEN** the command reports `/repo/app/.houmao` as the selected or would-bootstrap overlay root
- **AND THEN** it does not create `/repo/app/.houmao` during that status command

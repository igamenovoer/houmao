## MODIFIED Requirements

### Requirement: Project-aware agent-definition defaults discover the nearest project config
Project-aware command paths that need an effective local Houmao project overlay or an effective filesystem agent-definition root and are invoked without explicit local-root overrides SHALL resolve that state in this order:

1. explicit CLI overlay or agent-definition override,
2. `HOUMAO_PROJECT_OVERLAY_DIR`,
3. ambient project-overlay discovery under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`,
4. bootstrap `<cwd>/.houmao` when no project overlay exists and the command requires local Houmao-owned state.

`HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` when set SHALL be one of:

- `ancestor`
- `cwd_only`

When `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset, the effective mode SHALL be `ancestor`.
When the effective mode is `ancestor`, ambient discovery SHALL resolve the nearest ancestor `.houmao/houmao-config.toml` within the current Git worktree boundary.
When the effective mode is `cwd_only`, ambient discovery SHALL inspect only `<cwd>/.houmao/houmao-config.toml` and SHALL NOT search parent directories.

The current Git worktree boundary SHALL be inferred by walking ancestors until the nearest directory containing a `.git` file or directory. When no ancestor contains `.git`, `ancestor` mode MAY continue to the filesystem root.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` SHALL NOT change the selected overlay root for that invocation.
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
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs a project-aware local command from `/repo/subdir`
- **THEN** the command resolves `/repo/.houmao` as the active project overlay
- **AND THEN** it does not bootstrap `/repo/subdir/.houmao`

#### Scenario: Cwd-only mode ignores a parent overlay and bootstraps locally
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** `/repo/subdir/.houmao/houmao-config.toml` does not exist
- **AND WHEN** an operator runs a project-aware local command that needs local Houmao-owned state from `/repo/subdir`
- **THEN** the command does not resolve `/repo/.houmao` as the active project overlay
- **AND THEN** it bootstraps `/repo/subdir/.houmao`

#### Scenario: Explicit overlay-dir override still wins over cwd-only discovery mode
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** an operator runs a project-aware local command from `/repo/subdir`
- **THEN** the command resolves `/tmp/ci-overlay` as the active project overlay
- **AND THEN** it does not instead bootstrap `/repo/subdir/.houmao` merely because cwd-only mode is active

#### Scenario: Invalid discovery mode fails clearly
- **WHEN** no explicit CLI overlay root is supplied
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=sideways`
- **AND WHEN** an operator runs a project-aware local command
- **THEN** the command fails explicitly
- **AND THEN** the error explains that `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` must be `ancestor` or `cwd_only`

### Requirement: `houmao-mgr project status` reports discovered local project state
`houmao-mgr project status` SHALL resolve the active overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. ambient discovery from the caller's current working directory under `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`.

When `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset, the effective mode SHALL be `ancestor`.
When the effective mode is `ancestor`, status SHALL use nearest-ancestor project discovery from the caller's current working directory.
When the effective mode is `cwd_only`, status SHALL inspect only `<cwd>/.houmao/houmao-config.toml` and SHALL NOT search parent directories.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
The command SHALL report whether a repo-local Houmao overlay was discovered under the selected overlay root rather than only under the caller's current working directory.

At minimum, the reported payload SHALL include:

- whether a project overlay was found,
- the resolved overlay root when selected or discovered,
- the source of the resolved overlay root,
- the effective overlay discovery mode,
- the resolved config path when found,
- the resolved project-local catalog path when found,
- the effective agent-definition root,
- the effective agent-definition-root source.

When no project overlay is discovered under the selected overlay root, the command SHALL report that local project state is not initialized instead of silently pretending a project config exists.

#### Scenario: Status reports the env-selected catalog-backed overlay even when cwd-only mode is active
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/tmp/ci-overlay` as the resolved overlay root
- **AND THEN** it reports `env` as the overlay-root source
- **AND THEN** it reports `cwd_only` as the effective overlay discovery mode
- **AND THEN** it reports `/tmp/ci-overlay/houmao-config.toml` as the discovered config path

#### Scenario: Status reports the nearest discovered catalog-backed overlay by default
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo/.houmao` as the resolved overlay root
- **AND THEN** it reports `ancestor` as the effective overlay discovery mode
- **AND THEN** it reports `/repo/.houmao/houmao-config.toml` as the discovered config path

#### Scenario: Status reports the cwd-local overlay candidate in cwd-only mode
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE=cwd_only`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** `/repo/subdir/.houmao/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo/subdir/.houmao` as the selected overlay root
- **AND THEN** it reports that no local Houmao project overlay was discovered
- **AND THEN** it reports `cwd_only` as the effective overlay discovery mode

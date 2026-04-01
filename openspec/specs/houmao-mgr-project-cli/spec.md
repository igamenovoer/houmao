# houmao-mgr-project-cli Specification

## Purpose
Define the repo-local `houmao-mgr project` workflow for bootstrapping and inspecting one local `.houmao/` project overlay.
## Requirements
### Requirement: `houmao-mgr project` exposes repo-local project administration commands
`houmao-mgr` SHALL expose a top-level `project` command family for repo-local Houmao overlay administration.

At minimum, that family SHALL include:

- `init`
- `status`
- `agents`
- `easy`
- `mailbox`

The `project` family SHALL be presented as a local operator workflow for repo-local Houmao state rather than as a pair-authority or server-backed control surface.

#### Scenario: Operator sees the project command family
- **WHEN** an operator runs `houmao-mgr project --help`
- **THEN** the help output lists `init`, `status`, `agents`, `easy`, and `mailbox`
- **AND THEN** the help output presents `project` as a local project-overlay workflow

### Requirement: `houmao-mgr project init` bootstraps one repo-local `.houmao` overlay
`houmao-mgr project init` SHALL resolve the target overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. default `<cwd>/.houmao`.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set, `project init` SHALL bootstrap the overlay directly under that selected directory rather than under the caller's current working directory.

A successful init SHALL create:

- `<overlay-root>/`
- `<overlay-root>/houmao-config.toml`
- `<overlay-root>/.gitignore`
- `<overlay-root>/catalog.sqlite`
- managed project-local content roots required by the catalog-backed overlay contract

The generated `.gitignore` SHALL ignore all content under the selected overlay root and the command SHALL NOT modify a repository root `.gitignore` merely because the overlay root lives inside that repository.

The generated `houmao-config.toml` SHALL remain the lightweight discovery anchor for project-aware Houmao defaults, but the generated project-local catalog SHALL become the canonical semantic project-local configuration store.
The generated `houmao-config.toml` SHALL carry `paths.agent_def_dir` as compatibility-projection configuration for file-tree consumers, and when the config is first created `project init` SHALL set `paths.agent_def_dir = "agents"`.

The generated project-local content roots SHALL provide the managed file-backed storage needed for large text and tree-shaped payloads such as prompts, auth files, setup bundles, and skill packages.

When the target project overlay already exists and remains compatible, `project init` SHALL validate the existing overlay and preserve compatible local payload content rather than overwriting it.
When `houmao-config.toml` already exists and remains compatible, `project init` SHALL resolve `paths.agent_def_dir` relative to the selected overlay root and use that resolved compatibility-projection root for validation and optional compatibility-profile bootstrap instead of assuming only `<overlay-root>/agents/`.

#### Scenario: Operator initializes the default local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Env override redirects init to the selected overlay directory
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** an operator runs `houmao-mgr project init` from `/repo/app`
- **THEN** the command creates `/tmp/ci-overlay/houmao-config.toml`
- **AND THEN** it creates `/tmp/ci-overlay/catalog.sqlite`
- **AND THEN** it does not instead bootstrap `/repo/app/.houmao/`

#### Scenario: Relative env override fails clearly
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=relative/overlay`
- **AND WHEN** an operator runs `houmao-mgr project init`
- **THEN** the command fails explicitly
- **AND THEN** the error explains that `HOUMAO_PROJECT_OVERLAY_DIR` must be an absolute path

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has a compatible local overlay and `/repo/app/.houmao/custom-agents/tools/claude/auth/personal/`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
- **AND WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that existing local auth bundle only because init was re-run

### Requirement: `houmao-mgr project init` bootstraps project source roots but does not create optional project workflow state by default
`houmao-mgr project init` SHALL bootstrap the base project overlay, the project-local catalog, and the managed content roots required by the catalog-backed project contract without creating optional compatibility metadata or mailbox state by default.

At minimum, `project init` SHALL NOT create:

- `.houmao/agents/compatibility-profiles/`
- `.houmao/mailbox/`
- optional compatibility projection trees only because init was run

The catalog-backed overlay MAY create the managed content roots required by the base project-local storage contract even though those roots are not optional workflow state.

#### Scenario: Project init leaves optional roots opt-in
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates the base `.houmao/` overlay, the project-local catalog, and the managed content roots required by that overlay contract
- **AND THEN** it does not create `/repo/app/.houmao/agents/compatibility-profiles/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/mailbox/` only because init was run
- **AND THEN** it does not create an optional compatibility projection tree only because init was run

#### Scenario: Existing config with a custom relative compatibility root is respected
- **WHEN** `/repo/app/.houmao/houmao-config.toml` already exists
- **AND WHEN** that config resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command uses `/repo/app/.houmao/custom-agents/` as the resolved compatibility-projection root for validation
- **AND THEN** it does not silently replace that configured root with `/repo/app/.houmao/agents/`

#### Scenario: Operator explicitly enables compatibility-profile bootstrap
- **WHEN** an operator runs `houmao-mgr project init --with-compatibility-profiles` inside `/repo/app`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` resolves `paths.agent_def_dir = "custom-agents"`
- **THEN** the command creates `compatibility-profiles/` under `/repo/app/.houmao/custom-agents/`
- **AND THEN** it still creates the default `skills/`, `roles/`, and `tools/` roots there

### Requirement: Project-aware agent-definition defaults discover the nearest project config
Project-aware command paths that need an effective filesystem agent-definition root or compatibility-projection path and are invoked without explicit `--agent-def-dir` SHALL resolve that path in this order:

1. explicit CLI `--agent-def-dir`,
2. `HOUMAO_AGENT_DEF_DIR`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. nearest ancestor `.houmao/houmao-config.toml`,
5. default fallback `<cwd>/.houmao/agents`.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set and `<overlay-root>/houmao-config.toml` exists, the command SHALL use that config as the active project discovery anchor and SHALL NOT prefer nearest-ancestor discovery from the caller's current working directory.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set and `<overlay-root>/houmao-config.toml` does not exist, the command SHALL use `<overlay-root>/agents` as the project-aware fallback and SHALL NOT prefer nearest-ancestor discovery from the caller's current working directory.

When a project config is discovered, relative paths stored in that config SHALL resolve relative to the config file directory.
When a project config is discovered for a catalog-backed overlay, pair-native build and launch paths SHALL materialize the compatibility projection from that overlay's catalog and managed content store before reading presets, role prompts, or tool content.
Pure discovery and status paths MAY report the resolved compatibility-projection root without forcing materialization.

At minimum, this project-aware defaulting SHALL apply to:

- `houmao-mgr project status`
- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`

#### Scenario: Env-selected overlay uses its project config
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** that config resolves `agent_def_dir = "team-agents"`
- **AND WHEN** an operator runs `houmao-mgr brains build ...` from `/repo/subdir/nested` without `--agent-def-dir`
- **THEN** the command discovers `/tmp/ci-overlay` as the active project overlay
- **AND THEN** it resolves the compatibility-projection root as `/tmp/ci-overlay/team-agents`
- **AND THEN** it materializes that compatibility projection before reading presets or role content

#### Scenario: Env-selected overlay falls back to its local agents root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** `HOUMAO_AGENT_DEF_DIR` is unset
- **AND WHEN** an operator runs a project-aware build or launch path from `/repo`
- **THEN** the effective fallback agent-definition root is `/tmp/ci-overlay/agents`
- **AND THEN** the command does not prefer nearest-ancestor project discovery from `/repo`

#### Scenario: Explicit agent-definition override wins over env-selected overlay
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr brains build --agent-def-dir /tmp/custom-agents ...` from `/repo`
- **THEN** the command uses `/tmp/custom-agents` as the effective agent-definition root
- **AND THEN** it does not replace that explicit override with the env-selected overlay root

#### Scenario: Missing project config falls back to `.houmao`
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** `HOUMAO_AGENT_DEF_DIR` is unset
- **AND WHEN** an operator runs a project-aware build or launch path from `/repo`
- **THEN** the effective fallback agent-definition root is `/repo/.houmao/agents`
- **AND THEN** the command does not fall back to `/repo/.agentsys/agents`

### Requirement: `houmao-mgr project status` reports discovered local project state
`houmao-mgr project status` SHALL resolve the active overlay root in this order:

1. `HOUMAO_PROJECT_OVERLAY_DIR` when set,
2. nearest-ancestor project discovery from the caller's current working directory.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
The command SHALL report whether a repo-local Houmao overlay was discovered under the selected overlay root rather than only under the caller's current working directory.

At minimum, the reported payload SHALL include:

- whether a project overlay was found,
- the resolved overlay root when selected or discovered,
- the source of the resolved overlay root,
- the resolved config path when found,
- the resolved project-local catalog path when found,
- the effective agent-definition root,
- the effective agent-definition-root source.

When no project overlay is discovered under the selected overlay root, the command SHALL report that local project state is not initialized instead of silently pretending a project config exists.

#### Scenario: Status reports the env-selected catalog-backed overlay
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/tmp/ci-overlay` as the resolved overlay root
- **AND THEN** it reports `env` as the overlay-root source
- **AND THEN** it reports `/tmp/ci-overlay/houmao-config.toml` as the discovered config path
- **AND THEN** it reports the resolved project-local catalog path under that overlay

#### Scenario: Status reports missing overlay under the env-selected overlay root clearly
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project status`
- **THEN** the command reports `/tmp/ci-overlay` as the selected overlay root
- **AND THEN** it reports `env` as the overlay-root source
- **AND THEN** it reports that no local Houmao project overlay was discovered
- **AND THEN** it does not claim that a project-local catalog already exists

#### Scenario: Status reports the nearest discovered catalog-backed overlay
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR` is unset
- **AND WHEN** `/repo/.houmao/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo/.houmao` as the resolved overlay root
- **AND THEN** it reports `/repo/.houmao/houmao-config.toml` as the discovered config path
- **AND THEN** it reports the resolved project-local catalog path under that overlay

### Requirement: Maintained project-local source creation flows bootstrap the active overlay on demand
Maintained `houmao-mgr project agents ...` commands that create or update project-local tool, auth, role, or preset state SHALL resolve the active overlay through the shared ensure-or-bootstrap project-aware resolver instead of requiring a previously initialized overlay.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL ensure the selected overlay exists before writing project-local state.

At minimum, this requirement SHALL apply to:

- `houmao-mgr project agents tools <tool> setups add`
- `houmao-mgr project agents tools <tool> auth add`
- `houmao-mgr project agents tools <tool> auth set`
- `houmao-mgr project agents roles init`
- `houmao-mgr project agents roles scaffold`
- `houmao-mgr project agents roles presets add`

#### Scenario: Tool auth add bootstraps the missing overlay on demand
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools codex auth add --name personal --api-key sk-test`
- **THEN** the command ensures `<cwd>/.houmao` exists before writing the auth bundle
- **AND THEN** the resulting auth bundle is stored under that active project overlay

#### Scenario: Role init uses the env-selected overlay when bootstrapping
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** an operator runs `houmao-mgr project agents roles init --name reviewer`
- **THEN** the command ensures `/tmp/ci-overlay` exists before creating the role
- **AND THEN** the created role root is stored under `/tmp/ci-overlay/agents/roles/reviewer`

### Requirement: Maintained project-local inspection and existing-state flows remain non-creating
Maintained `houmao-mgr project agents ...` commands that inspect existing project-local source content or remove existing project-local state SHALL resolve overlay selection through the shared non-creating project-aware resolver.

When no active project overlay exists for the caller and no stronger overlay selection override applies, these commands SHALL fail clearly without bootstrapping the selected or would-bootstrap overlay root.

At minimum, this requirement SHALL apply to:

- `houmao-mgr project agents tools <tool> get`
- `houmao-mgr project agents tools <tool> setups list`
- `houmao-mgr project agents tools <tool> setups get`
- `houmao-mgr project agents tools <tool> setups remove`
- `houmao-mgr project agents tools <tool> auth list`
- `houmao-mgr project agents tools <tool> auth get`
- `houmao-mgr project agents tools <tool> auth remove`
- `houmao-mgr project agents roles list`
- `houmao-mgr project agents roles get`
- `houmao-mgr project agents roles remove`
- `houmao-mgr project agents roles presets list`
- `houmao-mgr project agents roles presets get`
- `houmao-mgr project agents roles presets remove`

#### Scenario: Tool get fails clearly without bootstrapping a missing overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools codex get`
- **THEN** the command fails clearly because no project overlay was discovered for the current invocation
- **AND THEN** it does not create `<cwd>/.houmao` as a side effect of that inspection command

#### Scenario: Role preset remove does not create an empty overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr project agents roles presets remove --role reviewer --tool codex`
- **THEN** the command fails clearly before attempting removal
- **AND THEN** it does not bootstrap a new project overlay only to report missing existing state

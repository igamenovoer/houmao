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
`houmao-mgr project init` SHALL treat the caller's current working directory as the target project root in v1.

A successful init SHALL create:

- `<project-root>/.houmao/`
- `<project-root>/.houmao/houmao-config.toml`
- `<project-root>/.houmao/.gitignore`
- `<project-root>/.houmao/catalog.sqlite`
- managed project-local content roots required by the catalog-backed overlay contract

The generated `.houmao/.gitignore` SHALL ignore all content under `.houmao/` and the command SHALL NOT modify the repository root `.gitignore`.

The generated `.houmao/houmao-config.toml` SHALL remain the lightweight discovery anchor for project-aware Houmao defaults, but the generated project-local catalog SHALL become the canonical semantic project-local configuration store.
The generated `.houmao/houmao-config.toml` SHALL carry `paths.agent_def_dir` as compatibility-projection configuration for file-tree consumers, and when the config is first created `project init` SHALL set `paths.agent_def_dir = "agents"`.

The generated project-local content roots SHALL provide the managed file-backed storage needed for large text and tree-shaped payloads such as prompts, auth files, setup bundles, and skill packages.

When the target project overlay already exists and remains compatible, `project init` SHALL validate the existing overlay and preserve compatible local payload content rather than overwriting it.
When `.houmao/houmao-config.toml` already exists and remains compatible, `project init` SHALL resolve `paths.agent_def_dir` relative to `.houmao/` and use that resolved compatibility-projection root for validation and optional compatibility-profile bootstrap instead of assuming only `<project-root>/.houmao/agents/`.

#### Scenario: Operator initializes a catalog-backed local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/catalog.sqlite`
- **AND THEN** it creates the managed project-local content roots required by the catalog-backed overlay contract

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has a compatible local overlay and `/repo/app/.houmao/custom-agents/tools/claude/auth/personal/`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
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
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml`,
4. default fallback `<cwd>/.houmao/agents`.

When a project config is discovered, relative paths stored in that config SHALL resolve relative to the config file directory `.houmao/`.
When a project config is discovered for a catalog-backed overlay, pair-native build and launch paths SHALL materialize the compatibility projection from that overlay's catalog and managed content store before reading presets, role prompts, or tool content.
Pure discovery and status paths MAY report the resolved compatibility-projection root without forcing materialization.

At minimum, this project-aware defaulting SHALL apply to:

- `houmao-mgr project status`
- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`

#### Scenario: Build from a repo subdirectory uses the discovered project overlay
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** that config resolves `agent_def_dir = "team-agents"`
- **AND WHEN** an operator runs `houmao-mgr brains build ...` from `/repo/subdir/nested` without `--agent-def-dir`
- **THEN** the command discovers `/repo/.houmao/` as the active project overlay
- **AND THEN** it resolves the compatibility-projection root as `/repo/.houmao/team-agents`
- **AND THEN** it materializes that compatibility projection before reading presets or role content

#### Scenario: Explicit agent-definition override wins over discovered project config
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr brains build --agent-def-dir /tmp/custom-agents ...` from `/repo`
- **THEN** the command uses `/tmp/custom-agents` as the effective agent-definition root
- **AND THEN** it does not replace that explicit override with the discovered project-local root

#### Scenario: Missing project config falls back to `.houmao`
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is unset
- **AND WHEN** an operator runs a project-aware build or launch path from `/repo`
- **THEN** the effective fallback agent-definition root is `/repo/.houmao/agents`
- **AND THEN** the command does not fall back to `/repo/.agentsys/agents`

### Requirement: `houmao-mgr project status` reports discovered local project state
`houmao-mgr project status` SHALL report whether a repo-local Houmao overlay was discovered from the caller's current working directory.

At minimum, the reported payload SHALL include:

- whether a project overlay was found,
- the resolved project root when found,
- the resolved config path when found,
- the resolved project-local catalog path when found.

When no project overlay is discovered, the command SHALL report that local project state is not initialized instead of silently pretending a project config exists.

#### Scenario: Status reports the nearest discovered catalog-backed overlay
- **WHEN** `/repo/.houmao/houmao-config.toml` exists for a catalog-backed overlay
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo` as the resolved project root
- **AND THEN** it reports `/repo/.houmao/houmao-config.toml` as the discovered config path
- **AND THEN** it reports the resolved project-local catalog path under that overlay

#### Scenario: Status reports missing project overlay clearly
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists for the caller
- **AND WHEN** an operator runs `houmao-mgr project status`
- **THEN** the command reports that no local Houmao project overlay was discovered
- **AND THEN** it does not claim that a project-local catalog already exists

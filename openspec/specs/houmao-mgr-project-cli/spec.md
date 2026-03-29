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
- `<project-root>/.houmao/agents/`

The generated `.houmao/.gitignore` SHALL ignore all content under `.houmao/` and the command SHALL NOT modify the repository root `.gitignore`.

The generated `.houmao/houmao-config.toml` SHALL be the project-local source of truth for project-aware Houmao defaults.

The generated `.houmao/agents/` tree SHALL include the canonical local source layout:

- `skills/`
- `roles/`
- `tools/`
- optional `compatibility-profiles/`

The generated `tools/` subtree SHALL include the packaged secret-free adapter and setup content needed for current supported tools.

When the target project overlay already exists and remains compatible, `project init` SHALL validate and preserve existing local auth bundles instead of overwriting them.

#### Scenario: Operator initializes a local Houmao overlay
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** it creates `/repo/app/.houmao/.gitignore` without editing `/repo/app/.gitignore`
- **AND THEN** it creates `/repo/app/.houmao/agents/` with canonical local source directories and packaged tool starter content

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has `/repo/app/.houmao/agents/tools/claude/auth/personal/`
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that existing local auth bundle only because init was re-run

### Requirement: `houmao-mgr project init` bootstraps project source roots but does not create optional project workflow state by default
`houmao-mgr project init` SHALL bootstrap the base project overlay and canonical `.houmao/agents/` tree without creating optional mailbox or `easy` metadata state by default.

At minimum, `project init` SHALL NOT create:

- `.houmao/mailbox/`
- `.houmao/easy/`

only because init was run.

#### Scenario: Project init leaves mailbox and easy state opt-in
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **THEN** the command creates the base `.houmao/` overlay and `.houmao/agents/` tree
- **AND THEN** it does not create `/repo/app/.houmao/mailbox/` only because init was run
- **AND THEN** it does not create `/repo/app/.houmao/easy/` only because init was run

### Requirement: Project-aware agent-definition defaults discover the nearest project config
Project-aware command paths that need an effective agent-definition root and are invoked without explicit `--agent-def-dir` SHALL resolve that root in this order:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml`,
4. legacy fallback `<cwd>/.agentsys/agents`.

At minimum, this project-aware defaulting SHALL apply to:

- `houmao-mgr project status`
- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`

When a project config is discovered, relative paths stored in that config SHALL resolve relative to the config file directory `.houmao/`.

#### Scenario: Build from a repo subdirectory uses the discovered project overlay
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** that config resolves `agent_def_dir = "agents"`
- **AND WHEN** an operator runs `houmao-mgr brains build ...` from `/repo/subdir/nested` without `--agent-def-dir`
- **THEN** the command resolves the effective agent-definition root as `/repo/.houmao/agents`

#### Scenario: Explicit agent-definition override wins over discovered project config
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr brains build --agent-def-dir /tmp/custom-agents ...` from `/repo`
- **THEN** the command uses `/tmp/custom-agents` as the effective agent-definition root
- **AND THEN** it does not replace that explicit override with `/repo/.houmao/agents`

#### Scenario: Missing project config falls back to legacy `.agentsys`
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is unset
- **AND WHEN** an operator runs a project-aware build or launch path from `/repo`
- **THEN** the effective fallback agent-definition root remains `/repo/.agentsys/agents`

### Requirement: `houmao-mgr project status` reports discovered local project state
`houmao-mgr project status` SHALL report whether a repo-local Houmao overlay was discovered from the caller's current working directory.

At minimum, the reported payload SHALL include:

- whether a project overlay was found,
- the resolved project root when found,
- the resolved config path when found,
- the effective agent-definition root.

When no project overlay is discovered, the command SHALL report that local project state is not initialized instead of silently pretending a project config exists.

#### Scenario: Status reports the nearest discovered overlay
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project status` from `/repo/subdir`
- **THEN** the command reports `/repo` as the resolved project root
- **AND THEN** it reports `/repo/.houmao/houmao-config.toml` as the discovered config path

#### Scenario: Status reports missing project overlay clearly
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists for the caller
- **AND WHEN** an operator runs `houmao-mgr project status`
- **THEN** the command reports that no local Houmao project overlay was discovered
- **AND THEN** it does not claim that `.houmao/houmao-config.toml` already exists

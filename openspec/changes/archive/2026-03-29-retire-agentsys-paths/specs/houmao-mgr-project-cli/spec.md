## MODIFIED Requirements

### Requirement: `houmao-mgr project init` bootstraps one repo-local `.houmao` overlay
`houmao-mgr project init` SHALL treat the caller's current working directory as the target project root in v1.

`project init` SHALL continue to bootstrap the catalog-backed `.houmao` overlay described by the base capability.

The generated `.houmao/houmao-config.toml` SHALL continue to carry `paths.agent_def_dir` as compatibility-projection configuration for file-tree consumers. When `.houmao/houmao-config.toml` does not already exist, `project init` SHALL create the default config with `paths.agent_def_dir = "agents"`.

Base init SHALL continue to create the base overlay, the project-local catalog, and the managed content roots without materializing optional compatibility projection trees only because init ran.

When `.houmao/houmao-config.toml` already exists and remains compatible, `project init` SHALL resolve `paths.agent_def_dir` relative to `.houmao/` and SHALL use that resolved compatibility-projection root for validation and optional compatibility-profile bootstrap instead of assuming only `<project-root>/.houmao/agents/`.

#### Scenario: Operator initializes a local Houmao overlay with the default config
- **WHEN** an operator runs `houmao-mgr project init` inside `/repo/app`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` does not already exist
- **THEN** the command creates `/repo/app/.houmao/houmao-config.toml`
- **AND THEN** the written config sets `paths.agent_def_dir = "agents"`
- **AND THEN** the command creates the base catalog-backed overlay roots
- **AND THEN** it does not materialize `/repo/app/.houmao/agents/` only because init ran

#### Scenario: Re-running init preserves compatible local auth state
- **WHEN** an operator already has a compatible local overlay and `/repo/app/.houmao/custom-agents/tools/claude/auth/personal/`
- **AND WHEN** `/repo/app/.houmao/houmao-config.toml` resolves `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** they run `houmao-mgr project init` again inside `/repo/app`
- **THEN** the command validates the existing project overlay
- **AND THEN** it does not delete or overwrite that existing local auth bundle only because init was re-run

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

At minimum, this project-aware defaulting SHALL apply to:

- `houmao-mgr project status`
- `houmao-mgr brains build`
- preset-backed `houmao-mgr agents launch`

When a project config is discovered, relative paths stored in that config SHALL resolve relative to the config file directory `.houmao/`.

When a project config is discovered for a catalog-backed overlay, pair-native build and launch paths SHALL materialize the compatibility projection from that overlay's catalog and managed content store before reading presets, role prompts, or tool content. Pure discovery/status paths MAY report the resolved compatibility-projection root without forcing materialization.

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

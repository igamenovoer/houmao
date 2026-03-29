## MODIFIED Requirements

### Requirement: Deprecated standalone build and start entrypoints use config-first `.houmao` agent-definition resolution
Deprecated standalone compatibility entrypoints that accept `--agent-def-dir` and otherwise resolve agent-definition content from the current working directory SHALL resolve the effective agent-definition root in this order:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml`,
4. default fallback `<cwd>/.houmao/agents`.

When a project config is discovered, the runtime SHALL resolve `paths.agent_def_dir` relative to the `.houmao/` directory that contains that config.

When a discovered project overlay is catalog-backed, these deprecated compatibility entrypoints SHALL follow the same compatibility-projection path contract used by current pair-native build/launch code before reading presets, blueprints, or role packages.

At minimum, this ambient resolution contract SHALL apply to `build-brain` and `start-session` when they resolve presets, blueprints, or role packages through the agent-definition root.

The deprecated standalone ambient resolution contract SHALL NOT fall back to `<cwd>/.agentsys/agents`.

#### Scenario: Deprecated `build-brain` uses the discovered configured project root
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** that config resolves `agent_def_dir = "specialists"`
- **AND WHEN** a developer invokes deprecated `houmao-cli build-brain ...` from `/repo/nested`
- **THEN** the command resolves the effective agent-definition root as `/repo/.houmao/specialists`

#### Scenario: Deprecated `start-session` falls back to `.houmao/agents` when no config is discovered
- **WHEN** no ancestor `.houmao/houmao-config.toml` exists for `/workspace/demo`
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is unset
- **AND WHEN** a developer invokes deprecated `houmao-cli start-session ...` from `/workspace/demo`
- **THEN** the command resolves the effective agent-definition root as `/workspace/demo/.houmao/agents`
- **AND THEN** it does not fall back to `/workspace/demo/.agentsys/agents`

#### Scenario: Explicit environment override still wins over discovered project config
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR=/tmp/agents`
- **AND WHEN** a developer invokes deprecated `houmao-cli build-brain ...` from `/repo`
- **THEN** the command resolves the effective agent-definition root as `/tmp/agents`
- **AND THEN** it does not replace that env override with the discovered project-local root

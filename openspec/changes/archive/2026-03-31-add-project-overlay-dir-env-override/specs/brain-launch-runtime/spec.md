## MODIFIED Requirements

### Requirement: Deprecated standalone build and start entrypoints use config-first `.houmao` agent-definition resolution
Deprecated standalone compatibility entrypoints that accept `--agent-def-dir` and otherwise resolve agent-definition content from the current working directory SHALL resolve the effective agent-definition root in this order:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. the overlay directory selected by `HOUMAO_PROJECT_OVERLAY_DIR`,
4. nearest ancestor `.houmao/houmao-config.toml`,
5. default fallback `<cwd>/.houmao/agents`.

When `HOUMAO_PROJECT_OVERLAY_DIR` is set, it SHALL be an absolute path.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set and `<overlay-root>/houmao-config.toml` exists, the runtime SHALL use that config as the project discovery anchor and SHALL NOT prefer nearest-ancestor discovery from the caller's current working directory.
When `HOUMAO_PROJECT_OVERLAY_DIR` is set and `<overlay-root>/houmao-config.toml` does not exist, the runtime SHALL derive the effective fallback agent-definition root as `<overlay-root>/agents` and SHALL NOT fall back to nearest-ancestor discovery from the caller's current working directory.

When a project config is discovered, the runtime SHALL resolve `paths.agent_def_dir` relative to the directory that contains that config.
When a discovered project overlay is catalog-backed, these deprecated compatibility entrypoints SHALL follow the same compatibility-projection path contract used by current pair-native build and launch code before reading presets, blueprints, or role packages.
At minimum, this ambient resolution contract SHALL apply to `build-brain` and `start-session` when they resolve presets, blueprints, or role packages through the agent-definition root.
The deprecated standalone ambient resolution contract SHALL NOT fall back to `<cwd>/.agentsys/agents`.

#### Scenario: Deprecated `build-brain` uses the env-selected configured overlay
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** that config resolves `agent_def_dir = "specialists"`
- **AND WHEN** a developer invokes deprecated `houmao-cli build-brain ...` from `/repo/nested`
- **THEN** the command resolves the effective agent-definition root as `/tmp/ci-overlay/specialists`

#### Scenario: Deprecated `start-session` falls back to the env-selected agents root
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` does not exist
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is unset
- **AND WHEN** a developer invokes deprecated `houmao-cli start-session ...` from `/workspace/demo`
- **THEN** the command resolves the effective agent-definition root as `/tmp/ci-overlay/agents`
- **AND THEN** it does not fall back to `/workspace/demo/.agentsys/agents`

#### Scenario: Explicit environment override still wins over env-selected overlay
- **WHEN** `HOUMAO_PROJECT_OVERLAY_DIR=/tmp/ci-overlay`
- **AND WHEN** `/tmp/ci-overlay/houmao-config.toml` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR=/tmp/agents`
- **AND WHEN** a developer invokes deprecated `houmao-cli build-brain ...` from `/repo`
- **THEN** the command resolves the effective agent-definition root as `/tmp/agents`
- **AND THEN** it does not replace that env override with the env-selected overlay root

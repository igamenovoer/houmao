# houmao-mgr-project-agent-tools Specification

## Purpose
Define the project-local `houmao-mgr internals native-agent tools` workflow for managing tool-scoped setup content in the active project-local overlay.
## Requirements
### Requirement: `houmao-mgr internals native-agent tools` mirrors the project-local tool tree
`houmao-mgr` SHALL expose a project-local tool administration subtree shaped as:

```text
houmao-mgr internals native-agent tools <tool> get
houmao-mgr internals native-agent tools <tool> setups <verb>
```

At minimum, `internals native-agent tools` and `project agents tools` SHALL expose Houmao-owned tool families for:

- `claude`
- `codex`
- `kimi`
- `dsh`

At minimum, each supported tool family SHALL expose:

- `get`
- `setups`

The help text for this subtree SHALL present it as management for project-local tool content under `.houmao/agents/tools/<tool>/`.

This subtree SHALL NOT own credential CRUD, which SHALL route through `houmao-mgr project credentials <tool> ...`.

#### Scenario: Operator sees the internals native-agent tools tree
- **WHEN** an operator runs `houmao-mgr internals native-agent tools --help`
- **THEN** the help output lists the supported tool families
- **AND THEN** the help output presents `internals native-agent tools` as management for `.houmao/agents/tools/`

#### Scenario: Operator sees the setup verbs for one tool
- **WHEN** an operator runs `houmao-mgr internals native-agent tools claude --help`
- **THEN** the help output presents `get` and `setups`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/claude/`

#### Scenario: Operator sees the Kimi tool family
- **WHEN** an operator runs `houmao-mgr internals native-agent tools kimi --help`
- **THEN** the help output presents `get` and `setups`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/kimi/`

#### Scenario: Operator inspects and clones DSH setups
- **WHEN** an operator runs `houmao-mgr project agents tools dsh setups list` or `setups add --name custom --from default`
- **THEN** the command lists or clones project-local DSH setup bundles under `.houmao/agents/tools/dsh/setups/`

### Requirement: Starter Kimi adapter defines managed home, launch, skills, and auth projection

The starter agent definition SHALL include a Kimi tool adapter and default setup bundle suitable for managed headless launches.

#### Scenario: Starter Kimi content declares the managed provider startup inputs

- **GIVEN** a project initializes or refreshes its starter Kimi tool content
- **THEN** the adapter and default setup describe the provider's managed home, executable, skill destination, setup destination, and auth inputs

The Kimi adapter SHALL declare `tool: kimi`, `KIMI_CODE_HOME` as its home selector, `kimi` as its default executable, `skills` as its skill destination, `.` as its setup destination, and auth projections for native config and credential storage. Its env allowlist SHALL cover private input bindings supported by managed Kimi startup. The executable declaration SHALL be portable across owners.

#### Scenario: Starter Kimi adapter uses portable executable by default

- **WHEN** a project initializes or refreshes starter agent tool content
- **THEN** the Kimi adapter declares launch executable `kimi`
- **AND THEN** the starter template requires no host-specific executable path

#### Scenario: Kimi auth projection accepts OAuth token storage

- **WHEN** a selected Kimi auth bundle provides `config.toml` and `credentials/kimi-code.json`
- **THEN** the build incorporates the config into the effective runtime config and projects the token file according to the adapter mapping
- **AND THEN** the build manifest records the credential input paths without exposing token values

### Requirement: `internals native-agent tools <tool> get` and `setups` inspect and manage setup bundles
`houmao-mgr internals native-agent tools <tool> get` SHALL report the discovered project root, tool root, adapter path, and setup names for the selected tool family.

`houmao-mgr internals native-agent tools <tool> setups` SHALL expose:

- `list`
- `get`
- `add`
- `remove`

`setups add --name <setup>` SHALL clone an existing setup within the same tool family, defaulting to `default` when `--from` is omitted.

#### Scenario: Tool get reports summary metadata for one tool family
- **WHEN** an operator runs `houmao-mgr internals native-agent tools codex get`
- **THEN** the command reports the Codex tool root, adapter path, and setup names
- **AND THEN** the operator does not need to inspect the tool subtree manually to discover those paths

#### Scenario: Setups add clones a new setup from default
- **WHEN** an operator runs `houmao-mgr internals native-agent tools claude setups add --name research`
- **THEN** the command clones `.houmao/agents/tools/claude/setups/default/` into `.houmao/agents/tools/claude/setups/research/`
- **AND THEN** the new setup becomes available for later role presets

### Requirement: Project agent-tool administration excludes Gemini
Project agent-tool inspection and setup administration SHALL expose only maintained tool subtrees and SHALL NOT expose Gemini.

#### Scenario: Gemini project tool lookup is unavailable
- **WHEN** an operator requests `project agents tools gemini get`
- **THEN** command validation rejects the tool
- **AND THEN** no Gemini starter subtree is materialized

### Requirement: Starter Kimi environment projection matches current Kimi Code model variables

The starter Kimi adapter SHALL include `KIMI_MODEL_API_KEY` for private native config references and retain the supported sampling and global completion-cap variables as private inputs. It SHALL omit the env-model selector, config-owned provider and model fields, thinking defaults, telemetry, managed provider endpoint overrides, and obsolete thinking-mode variables.

#### Scenario: Current Kimi thinking and sampling variables survive projection

- **WHEN** the selected Kimi bundle declares a native model and an allowlisted `KIMI_MODEL_TEMPERATURE`, `KIMI_MODEL_TOP_P`, `KIMI_MODEL_MAX_TOKENS`, or `KIMI_MODEL_MAX_COMPLETION_TOKENS` value
- **THEN** the native process receives the selected value through its private launch environment
- **AND THEN** thinking defaults come from native config
- **AND THEN** the value is absent from the tmux session environment

#### Scenario: Obsolete Kimi thinking variables are not advertised

- **WHEN** a maintainer inspects the starter Kimi adapter
- **THEN** the allowlist excludes `KIMI_MODEL_NAME`, `KIMI_MODEL_THINKING_EFFORT`, `KIMI_MODEL_THINKING_KEEP`, `KIMI_DISABLE_TELEMETRY`, `KIMI_MODEL_DEFAULT_THINKING`, and `KIMI_MODEL_THINKING_MODE`

### Requirement: Tool setup bundles support optional per-tool parameter seed files

A setup directory under `tools/<tool>/setups/<name>/` MAY include an optional `tool-params.yaml` file containing secret-free partial `tool_params` for `<tool>`. During brain construction, `<setup>/tool-params.yaml` SHALL be validated against `<tool>`'s partial schema, applied above `adapter.yaml` `launch.default_tool_params` and below specialist or preset `tool_params`, and excluded from raw native setup file copying into the runtime home.

#### Scenario: Setup tool-params.yaml seeds defaults without copying Houmao metadata as a native tool file
- **WHEN** `tools/dsh/setups/openai-compatible/tool-params.yaml` defines baseline DSH `provider` settings and a specialist supplies `tool_params.models`
- **THEN** brain construction merges the setup `provider` defaults with the specialist `models` catalog
- **AND THEN** `tool-params.yaml` is consumed by Houmao's tool-params pipeline rather than copied verbatim as an unvalidated native config file

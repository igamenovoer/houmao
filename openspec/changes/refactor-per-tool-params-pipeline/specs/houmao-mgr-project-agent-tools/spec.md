# houmao-mgr-project-agent-tools Specification

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Tool setup bundles support optional per-tool parameter seed files

A setup directory under `tools/<tool>/setups/<name>/` MAY include an optional `tool-params.yaml` file containing secret-free partial `tool_params` for `<tool>`. During brain construction, `<setup>/tool-params.yaml` SHALL be validated against `<tool>`'s partial schema, applied above `adapter.yaml` `launch.default_tool_params` and below specialist or preset `tool_params`, and excluded from raw native setup file copying into the runtime home.

#### Scenario: Setup tool-params.yaml seeds defaults without copying Houmao metadata as a native tool file
- **WHEN** `tools/dsh/setups/openai-compatible/tool-params.yaml` defines baseline DSH `provider` settings and a specialist supplies `tool_params.models`
- **THEN** brain construction merges the setup `provider` defaults with the specialist `models` catalog
- **AND THEN** `tool-params.yaml` is consumed by Houmao's tool-params pipeline rather than copied verbatim as an unvalidated native config file

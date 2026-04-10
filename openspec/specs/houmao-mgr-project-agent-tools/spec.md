# houmao-mgr-project-agent-tools Specification

## Purpose
Define the project-local `houmao-mgr project agents tools` workflow for managing tool-scoped setup content in the active project-local overlay.

## Requirements

### Requirement: `houmao-mgr project agents tools` mirrors the project-local tool tree
`houmao-mgr` SHALL expose a project-local tool administration subtree shaped as:

```text
houmao-mgr project agents tools <tool> get
houmao-mgr project agents tools <tool> setups <verb>
```

At minimum, `project agents tools` SHALL expose Houmao-owned tool families for:

- `claude`
- `codex`
- `gemini`

At minimum, each supported tool family SHALL expose:

- `get`
- `setups`

The help text for this subtree SHALL present it as management for project-local tool content under `.houmao/agents/tools/<tool>/`.

This subtree SHALL NOT own credential CRUD, which SHALL route through `houmao-mgr project credentials <tool> ...`.

#### Scenario: Operator sees the project agents tools tree
- **WHEN** an operator runs `houmao-mgr project agents tools --help`
- **THEN** the help output lists the supported tool families
- **AND THEN** the help output presents `project agents tools` as management for `.houmao/agents/tools/`

#### Scenario: Operator sees the setup verbs for one tool
- **WHEN** an operator runs `houmao-mgr project agents tools claude --help`
- **THEN** the help output presents `get` and `setups`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/claude/`

### Requirement: `project agents tools <tool> get` and `setups` inspect and manage setup bundles
`houmao-mgr project agents tools <tool> get` SHALL report the discovered project root, tool root, adapter path, and setup names for the selected tool family.

`houmao-mgr project agents tools <tool> setups` SHALL expose:

- `list`
- `get`
- `add`
- `remove`

`setups add --name <setup>` SHALL clone an existing setup within the same tool family, defaulting to `default` when `--from` is omitted.

#### Scenario: Tool get reports summary metadata for one tool family
- **WHEN** an operator runs `houmao-mgr project agents tools codex get`
- **THEN** the command reports the Codex tool root, adapter path, and setup names
- **AND THEN** the operator does not need to inspect the tool subtree manually to discover those paths

#### Scenario: Setups add clones a new setup from default
- **WHEN** an operator runs `houmao-mgr project agents tools claude setups add --name research`
- **THEN** the command clones `.houmao/agents/tools/claude/setups/default/` into `.houmao/agents/tools/claude/setups/research/`
- **AND THEN** the new setup becomes available for later role presets

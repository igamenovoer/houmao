## REMOVED Requirements

### Requirement: `houmao-mgr project agent-tools` mirrors the project-local tool auth tree
**Reason**: The public project tool surface moves under `houmao-mgr project agents tools ...` so the CLI mirrors `.houmao/agents/tools/` directly instead of using a synthetic `agent-tools` namespace.
**Migration**: Use `houmao-mgr project agents tools <tool> ...` for project-local tool inspection, setup management, and auth management.

### Requirement: `project agent-tools <tool> auth` manages the existing on-disk auth-bundle layout
**Reason**: The auth-bundle contract remains, but the supported public path moves under `project agents tools <tool> auth ...`.
**Migration**: Use `houmao-mgr project agents tools <tool> auth ...` against the same `.houmao/agents/tools/<tool>/auth/<name>/` layout.

### Requirement: `auth get` reports one bundle safely and `auth set` uses patch semantics
**Reason**: The safe-reporting and patch-update behavior is retained under the renamed `project agents tools <tool> auth` surface.
**Migration**: Use `houmao-mgr project agents tools <tool> auth get|set ...` with the same secret-redaction and patch semantics.

## ADDED Requirements

### Requirement: `houmao-mgr project agents tools` mirrors the project-local tool tree
`houmao-mgr` SHALL expose a project-local tool administration subtree shaped as:

```text
houmao-mgr project agents tools <tool> get
houmao-mgr project agents tools <tool> setups <verb>
houmao-mgr project agents tools <tool> auth <verb>
```

At minimum, `project agents tools` SHALL expose Houmao-owned tool families for:

- `claude`
- `codex`
- `gemini`

At minimum, each supported tool family SHALL expose:

- `get`
- `setups`
- `auth`

The help text for this subtree SHALL present it as management for project-local tool content under `.houmao/agents/tools/<tool>/`.

#### Scenario: Operator sees the project agents tools tree
- **WHEN** an operator runs `houmao-mgr project agents tools --help`
- **THEN** the help output lists the supported tool families
- **AND THEN** the help output presents `project agents tools` as management for `.houmao/agents/tools/`

#### Scenario: Operator sees the setup and auth verbs for one tool
- **WHEN** an operator runs `houmao-mgr project agents tools claude --help`
- **THEN** the help output presents `get`, `setups`, and `auth`
- **AND THEN** those commands are described as operations on `.houmao/agents/tools/claude/`

### Requirement: `project agents tools <tool> get` and `setups` inspect and manage setup bundles
`houmao-mgr project agents tools <tool> get` SHALL report the discovered project root, tool root, adapter path, setup names, and auth bundle names for the selected tool family.

`houmao-mgr project agents tools <tool> setups` SHALL expose:

- `list`
- `get`
- `add`
- `remove`

`setups add --name <setup>` SHALL clone an existing setup within the same tool family, defaulting to `default` when `--from` is omitted.

#### Scenario: Tool get reports summary metadata for one tool family
- **WHEN** an operator runs `houmao-mgr project agents tools codex get`
- **THEN** the command reports the Codex tool root, adapter path, setup names, and auth bundle names
- **AND THEN** the operator does not need to inspect the tool subtree manually to discover those paths

#### Scenario: Setups add clones a new setup from default
- **WHEN** an operator runs `houmao-mgr project agents tools claude setups add --name research`
- **THEN** the command clones `.houmao/agents/tools/claude/setups/default/` into `.houmao/agents/tools/claude/setups/research/`
- **AND THEN** the new setup becomes available for later role presets

### Requirement: `project agents tools <tool> auth` manages the existing on-disk auth-bundle layout
`houmao-mgr project agents tools <tool> auth` SHALL create, inspect, update, list, and remove auth bundles directly under:

```text
<project-root>/.houmao/agents/tools/<tool>/auth/<name>/
```

`auth add --name <name>` SHALL create a new auth bundle and SHALL fail if that named bundle already exists.

`auth set --name <name>` SHALL update an existing auth bundle and SHALL fail if that named bundle does not exist.

`auth list` SHALL enumerate existing bundle names for the selected tool.

`auth remove --name <name>` SHALL delete the named auth bundle.

Tool-specific flags SHALL continue mapping onto the adapter-defined env/file contract for the selected tool, including `env/vars.env` and any supported `files/*` content.

#### Scenario: Add creates a new Claude auth bundle in the existing storage model
- **WHEN** an operator runs `houmao-mgr project agents tools claude auth add --name work --base-url https://api.example.test --api-key sk-test`
- **THEN** the command creates `.houmao/agents/tools/claude/auth/work/env/vars.env` under the discovered project root
- **AND THEN** it stores the selected Claude-compatible auth inputs using the current Claude adapter contract

#### Scenario: Add rejects duplicate auth bundle names
- **WHEN** `.houmao/agents/tools/gemini/auth/work/` already exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name work --oauth-creds /tmp/oauth.json`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently reinterpret `add` as an update

### Requirement: `project agents tools <tool> auth get` reports one bundle safely and `auth set` uses patch semantics
`houmao-mgr project agents tools <tool> auth get --name <name>` SHALL report one existing auth bundle as structured data.

By default, `auth get` SHALL redact secret-like values such as API keys or auth tokens instead of printing them verbatim.

File-backed auth material SHALL be reported through presence and path metadata rather than by dumping raw file content by default.

`auth set` SHALL only update fields explicitly provided by the operator. Omitted fields SHALL remain unchanged unless the operator uses an explicit clear-style option for that field.

#### Scenario: Get redacts secret values by default
- **WHEN** `.houmao/agents/tools/claude/auth/work/env/vars.env` contains both `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL`
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth get --name work`
- **THEN** the command reports that the API key is present without printing its raw value
- **AND THEN** the command may still report non-secret metadata such as the bundle path or configured base URL

#### Scenario: Set preserves unspecified fields
- **WHEN** `.houmao/agents/tools/claude/auth/work/env/vars.env` already contains both `ANTHROPIC_API_KEY=sk-test` and `ANTHROPIC_BASE_URL=https://api.example.test`
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth set --name work --base-url https://proxy.example.test`
- **THEN** the command updates the stored base URL
- **AND THEN** it does not delete the existing API key only because `--api-key` was omitted

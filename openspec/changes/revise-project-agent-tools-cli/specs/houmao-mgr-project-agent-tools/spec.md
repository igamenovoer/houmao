## ADDED Requirements

### Requirement: `houmao-mgr project agent-tools` mirrors the project-local tool auth tree
`houmao-mgr` SHALL expose a project-local tool administration subtree shaped as:

```text
houmao-mgr project agent-tools <tool> auth <verb>
```

At minimum, `project agent-tools` SHALL expose Houmao-owned tool families for:

- `claude`
- `codex`
- `gemini`

At minimum, each supported tool family SHALL expose an `auth` subtree containing:

- `list`
- `add`
- `get`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for project-local auth bundles stored under `.houmao/agents/tools/<tool>/auth/`.

#### Scenario: Operator sees the tool-oriented project auth tree
- **WHEN** an operator runs `houmao-mgr project agent-tools --help`
- **THEN** the help output lists the supported tool families
- **AND THEN** the help output presents `agent-tools` as management for project-local tool content rather than as a separate credential registry

#### Scenario: Operator sees auth verbs for one supported tool
- **WHEN** an operator runs `houmao-mgr project agent-tools claude auth --help`
- **THEN** the help output lists `list`, `add`, `get`, `set`, and `remove`
- **AND THEN** the help output presents those commands as operations on `.houmao/agents/tools/claude/auth/<name>/`

### Requirement: `project agent-tools <tool> auth` manages the existing on-disk auth-bundle layout
`houmao-mgr project agent-tools <tool> auth` SHALL create, inspect, update, list, and remove auth bundles directly under:

```text
<project-root>/.houmao/agents/tools/<tool>/auth/<name>/
```

`auth add --name <name>` SHALL create a new auth bundle and SHALL fail if that named bundle already exists.

`auth set --name <name>` SHALL update an existing auth bundle and SHALL fail if that named bundle does not exist.

`auth list` SHALL enumerate existing bundle names for the selected tool.

`auth remove --name <name>` SHALL delete the named auth bundle.

Tool-specific flags SHALL continue mapping onto the adapter-defined env/file contract for the selected tool, including `env/vars.env` and any supported `files/*` content.

#### Scenario: Add creates a new Claude auth bundle in the existing storage model
- **WHEN** an operator runs `houmao-mgr project agent-tools claude auth add --name work --base-url https://api.example.test --api-key sk-test`
- **THEN** the command creates `.houmao/agents/tools/claude/auth/work/env/vars.env` under the discovered project root
- **AND THEN** it stores the selected Claude-compatible auth inputs using the current Claude adapter contract

#### Scenario: Set updates an existing auth bundle without changing its location
- **WHEN** `.houmao/agents/tools/codex/auth/personal/` already exists
- **AND WHEN** an operator runs `houmao-mgr project agent-tools codex auth set --name personal --base-url https://proxy.example.test/v1`
- **THEN** the command updates that existing auth bundle in place
- **AND THEN** it does not create a separate credential registry or move the bundle outside `.houmao/agents/tools/codex/auth/personal/`

#### Scenario: Add rejects duplicate auth bundle names
- **WHEN** `.houmao/agents/tools/gemini/auth/work/` already exists
- **AND WHEN** an operator runs `houmao-mgr project agent-tools gemini auth add --name work --oauth-creds /tmp/oauth.json`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently reinterpret `add` as an update

### Requirement: `auth get` reports one bundle safely and `auth set` uses patch semantics
`houmao-mgr project agent-tools <tool> auth get --name <name>` SHALL report one existing auth bundle as structured data.

By default, `auth get` SHALL redact secret-like values such as API keys or auth tokens instead of printing them verbatim.

File-backed auth material SHALL be reported through presence and path metadata rather than by dumping raw file content by default.

`auth set` SHALL only update fields explicitly provided by the operator. Omitted fields SHALL remain unchanged unless the operator uses an explicit clear-style option for that field.

#### Scenario: Get redacts secret values by default
- **WHEN** `.houmao/agents/tools/claude/auth/work/env/vars.env` contains both `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL`
- **AND WHEN** an operator runs `houmao-mgr project agent-tools claude auth get --name work`
- **THEN** the command reports that the API key is present without printing its raw value
- **AND THEN** the command may still report non-secret metadata such as the bundle path or configured base URL

#### Scenario: Set preserves unspecified fields
- **WHEN** `.houmao/agents/tools/claude/auth/work/env/vars.env` already contains both `ANTHROPIC_API_KEY=sk-test` and `ANTHROPIC_BASE_URL=https://api.example.test`
- **AND WHEN** an operator runs `houmao-mgr project agent-tools claude auth set --name work --base-url https://proxy.example.test`
- **THEN** the command updates the stored base URL
- **AND THEN** it does not delete the existing API key only because `--api-key` was omitted

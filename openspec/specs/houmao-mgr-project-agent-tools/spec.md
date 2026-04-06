# houmao-mgr-project-agent-tools Specification

## Purpose
Define the project-local `houmao-mgr project agents tools` workflow for managing tool-scoped setup and auth content inside the repo-local `.houmao/agents/tools/` tree.

## Requirements

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

### Requirement: Gemini auth bundles support API key, optional endpoint override, and OAuth inputs
`houmao-mgr project agents tools gemini auth` SHALL support Gemini auth bundles that can represent:

- API-key-based Gemini access through `GEMINI_API_KEY`
- optional Gemini endpoint override through `GOOGLE_GEMINI_BASE_URL`
- OAuth-backed Gemini access through `oauth_creds.json`

The command surface SHALL preserve patch semantics so operators can configure one of these lanes without implicitly deleting other unspecified Gemini auth inputs.

#### Scenario: Add creates a Gemini API-key auth bundle with an endpoint override
- **WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name proxy --api-key gm-test --base-url https://gemini.example.test`
- **THEN** the command creates `.houmao/agents/tools/gemini/auth/proxy/env/vars.env`
- **AND THEN** that bundle stores `GEMINI_API_KEY` and `GOOGLE_GEMINI_BASE_URL` using the Gemini adapter contract

#### Scenario: Set updates the Gemini endpoint override without removing the API key
- **WHEN** `.houmao/agents/tools/gemini/auth/proxy/env/vars.env` already contains `GEMINI_API_KEY=gm-test`
- **AND WHEN** an operator runs `houmao-mgr project agents tools gemini auth set --name proxy --base-url https://gemini-alt.example.test`
- **THEN** the command updates the stored `GOOGLE_GEMINI_BASE_URL`
- **AND THEN** it does not delete the existing `GEMINI_API_KEY` only because `--api-key` was omitted

#### Scenario: Add creates a Gemini OAuth auth bundle with the OAuth credential file
- **WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name personal --oauth-creds /tmp/oauth_creds.json`
- **THEN** the command creates `.houmao/agents/tools/gemini/auth/personal/files/oauth_creds.json`
- **AND THEN** the resulting Gemini auth bundle remains valid even when no API key is configured

### Requirement: Claude auth bundles support vendor OAuth token and imported login state
`houmao-mgr project agents tools claude auth` SHALL support Claude auth bundles that can represent:

- API-key-based Claude access through `ANTHROPIC_API_KEY`
- auth-token-based Claude access through `ANTHROPIC_AUTH_TOKEN`
- OAuth-token-based Claude access through `CLAUDE_CODE_OAUTH_TOKEN`
- optional endpoint and model env values already supported by the Claude adapter contract
- imported vendor login state through `.credentials.json` and optional `.claude.json` copied from a Claude config root

The command surface SHALL accept a Claude config-dir import input for the vendor login-state lane and SHALL preserve patch semantics across both env-backed and file-backed Claude auth inputs.

`claude_state.template.json` MAY remain supported as optional Claude runtime-state template content inside the auth bundle, but it SHALL NOT be treated, counted, or documented as a Claude credential-providing lane.

#### Scenario: Add creates a Claude OAuth-token auth bundle
- **WHEN** an operator runs `houmao-mgr project agents tools claude auth add --name personal --oauth-token token123`
- **THEN** the command creates `.houmao/agents/tools/claude/auth/personal/env/vars.env`
- **AND THEN** that bundle stores `CLAUDE_CODE_OAUTH_TOKEN` without requiring `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`

#### Scenario: Add imports Claude login state from a config root
- **WHEN** `/tmp/claude-home` contains `.credentials.json` and `.claude.json`
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth add --name logged-in --config-dir /tmp/claude-home`
- **THEN** the command copies `.credentials.json` into `.houmao/agents/tools/claude/auth/logged-in/files/.credentials.json`
- **AND THEN** it also copies `.claude.json` into `.houmao/agents/tools/claude/auth/logged-in/files/.claude.json`

#### Scenario: Set refreshes imported Claude login files without deleting other explicit settings
- **WHEN** `.houmao/agents/tools/claude/auth/logged-in/env/vars.env` already contains `ANTHROPIC_MODEL=claude-sonnet`
- **AND WHEN** that bundle already contains imported Claude login-state files
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth set --name logged-in --config-dir /tmp/claude-home-2`
- **THEN** the command updates the copied vendor login-state files from `/tmp/claude-home-2`
- **AND THEN** it does not delete the stored `ANTHROPIC_MODEL` only because `--model` was omitted

#### Scenario: Claude state template remains optional and separate from credentials
- **WHEN** an operator creates or updates a Claude auth bundle using a supported credential lane
- **AND WHEN** no `claude_state.template.json` is provided
- **THEN** the resulting credential bundle remains valid for that selected credential lane
- **AND THEN** the operator-facing contract does not describe the missing template as missing credentials

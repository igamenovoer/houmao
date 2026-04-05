## ADDED Requirements

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

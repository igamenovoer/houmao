## ADDED Requirements

### Requirement: Claude easy specialists support vendor OAuth token and imported login state
`houmao-mgr project easy specialist create --tool claude` SHALL accept Claude vendor-auth inputs for:

- `CLAUDE_CODE_OAUTH_TOKEN`
- imported Claude login state from a Claude config root

When provided, the command SHALL persist those inputs into the selected or derived Claude credential bundle using the same Claude auth-bundle contract as `houmao-mgr project agents tools claude auth`.

These Claude vendor-auth lanes SHALL remain valid even when `--api-key`, `--claude-auth-token`, and `--claude-state-template-file` are omitted.

`--claude-state-template-file` MAY remain as an optional Claude runtime-state template input, but it SHALL NOT be described as one of the Claude credential-providing methods on this surface.

#### Scenario: Easy specialist create persists the Claude OAuth-token lane
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-oauth-token token123`
- **THEN** the derived Claude credential bundle `reviewer-creds` stores `CLAUDE_CODE_OAUTH_TOKEN`
- **AND THEN** the specialist persists successfully without requiring `--api-key`

#### Scenario: Easy specialist create imports Claude login state from a config root
- **WHEN** `/tmp/claude-home` contains vendor Claude login-state files
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-config-dir /tmp/claude-home`
- **THEN** the derived Claude credential bundle copies the supported vendor Claude login-state files
- **AND THEN** the specialist persists successfully without requiring `--claude-state-template-file`

#### Scenario: Easy specialist create preserves other explicit Claude settings with imported login state
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-config-dir /tmp/claude-home --claude-model claude-opus`
- **THEN** the derived Claude credential bundle copies the vendor Claude login-state files
- **AND THEN** it also preserves `ANTHROPIC_MODEL=claude-opus` in that credential bundle

#### Scenario: Claude state template remains optional on the easy-specialist surface
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --claude-oauth-token token123`
- **AND WHEN** `--claude-state-template-file` is omitted
- **THEN** the specialist persists successfully
- **AND THEN** the operator-facing contract does not describe the omitted template as missing Claude credentials

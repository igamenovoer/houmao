## ADDED Requirements

### Requirement: `houmao-create-specialist` treats vendor-supported Claude login state and OAuth tokens as importable
When the selected tool is Claude and the active credential-source mode permits discovery, the packaged `houmao-create-specialist` skill SHALL treat these discovered Claude auth shapes as importable:

- `CLAUDE_CODE_OAUTH_TOKEN`
- Claude login state rooted at `CLAUDE_CONFIG_DIR` or the maintained default Claude config root when that root contains the vendor files needed for the Claude login-state lane

The skill SHALL map those discovered Claude auth shapes only into supported create-command inputs for the Claude lane, including the Claude OAuth-token input and the Claude config-dir import input.

The skill SHALL continue to report non-importable Claude auth shapes, such as `apiKeyHelper`-only setups without separately reusable credential material, as unsupported instead of guessing.

An explicit or discovered `claude_state.template.json` MAY still be used as optional Claude runtime-state template input, but the skill SHALL classify that file separately from credential-providing Claude auth methods.

#### Scenario: Auto discovery imports Claude OAuth token from environment
- **WHEN** the user explicitly requests `auto credentials` for `--tool claude`
- **AND WHEN** discovery finds `CLAUDE_CODE_OAUTH_TOKEN` in the supported Claude env lookup surfaces
- **THEN** the skill treats that token as importable Claude auth
- **AND THEN** it maps that result into the supported Claude OAuth-token create input rather than rejecting it as unsupported

#### Scenario: Auto discovery imports Claude login state from the maintained config root
- **WHEN** the user explicitly requests `auto credentials` for `--tool claude`
- **AND WHEN** discovery finds a maintained Claude config root containing the vendor login-state files required by the Claude login-state lane
- **THEN** the skill treats that Claude login state as importable for specialist creation
- **AND THEN** it maps that result into the supported Claude config-dir create input rather than reporting "logged in but unsupported"

#### Scenario: Claude apiKeyHelper-only auth remains unsupported
- **WHEN** the user explicitly requests `auto credentials` for `--tool claude`
- **AND WHEN** discovery determines that the current Claude auth depends only on `apiKeyHelper` without separately reusable import material
- **THEN** the skill reports that the current Claude auth is not directly importable for specialist creation
- **AND THEN** it asks the user for another supported Claude auth input instead of guessing

#### Scenario: State template alone does not count as discovered Claude credentials
- **WHEN** the user explicitly requests `auto credentials` for `--tool claude`
- **AND WHEN** discovery finds only a reusable `claude_state.template.json` and no supported Claude credential or login-state material
- **THEN** the skill reports that usable Claude credentials were not discovered for specialist creation
- **AND THEN** it may mention the reusable state template only as optional bootstrap input rather than as a credential method

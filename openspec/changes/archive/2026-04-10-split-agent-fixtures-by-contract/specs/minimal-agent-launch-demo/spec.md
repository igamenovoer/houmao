## MODIFIED Requirements

### Requirement: The demo creates provider-specific local auth aliases at run time
The demo run workflow SHALL create a generated working tree under the demo output root and SHALL materialize one demo-local auth alias named `default` for the selected provider by symlinking to the corresponding local fixture auth bundle under `tests/fixtures/auth-bundles/<tool>/`.

#### Scenario: Claude run aliases local fixture auth
- **WHEN** an operator runs the demo for provider `claude_code`
- **THEN** the generated working tree contains `tools/claude/auth/default` as a symlink to one maintained Claude bundle under `tests/fixtures/auth-bundles/claude/`
- **AND THEN** the tracked Claude preset may continue to declare `auth: default`

#### Scenario: Codex run aliases local fixture auth
- **WHEN** an operator runs the demo for provider `codex`
- **THEN** the generated working tree contains `tools/codex/auth/default` as a symlink to one maintained Codex bundle under `tests/fixtures/auth-bundles/codex/`
- **AND THEN** the tracked Codex preset may continue to declare `auth: default`

#### Scenario: Missing fixture auth fails during preflight
- **WHEN** an operator runs the demo for one provider
- **AND WHEN** the expected source fixture auth bundle for that provider is absent on the host
- **THEN** the demo fails before launch with a clear error identifying the missing fixture auth path

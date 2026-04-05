## ADDED Requirements

### Requirement: Orchestrated Claude launches support `CLAUDE_CODE_OAUTH_TOKEN`
The system SHALL support `CLAUDE_CODE_OAUTH_TOKEN` as a maintained Claude auth env var for orchestrated Claude launches.

When the effective Claude launch environment includes `CLAUDE_CODE_OAUTH_TOKEN`, the Claude adapter projection and launch preparation SHALL preserve that env var for the Claude process instead of rewriting it into a different Claude auth lane.

#### Scenario: Runtime launch preserves `CLAUDE_CODE_OAUTH_TOKEN`
- **WHEN** the selected Claude auth bundle defines `CLAUDE_CODE_OAUTH_TOKEN`
- **AND WHEN** Houmao constructs an orchestrated Claude runtime launch
- **THEN** the effective Claude launch environment includes `CLAUDE_CODE_OAUTH_TOKEN`
- **AND THEN** launch preparation does not require `ANTHROPIC_AUTH_TOKEN` as a replacement for that lane

### Requirement: Claude auth bundles may provide vendor login-state files for isolated runtime homes
The Claude auth bundle SHALL support optional vendor login-state files for the isolated runtime Claude home, including:

- `.credentials.json`
- `.claude.json`

When those files are present in the selected Claude auth bundle, auth projection SHALL place them at the runtime Claude config root under the same filenames.

Launch preparation SHALL treat a projected `.claude.json` as existing Claude runtime state, SHALL NOT require `claude_state.template.json` solely because that projected runtime state came from imported vendor login state, and SHALL preserve projected `.credentials.json` without rewriting it.

`claude_state.template.json` remains optional Claude bootstrap seed state on this surface and SHALL NOT be treated as a credential-providing method.

#### Scenario: Projected Claude login-state files appear in the isolated runtime home
- **WHEN** the selected Claude auth bundle contains `.credentials.json` and `.claude.json`
- **THEN** Claude runtime construction projects those files into the isolated runtime `CLAUDE_CONFIG_DIR`
- **AND THEN** the Claude process sees them under the same filenames it would use in a vendor-owned Claude config root

#### Scenario: Projected `.claude.json` removes the need for a state template
- **WHEN** an orchestrated Claude launch uses an auth bundle with projected vendor `.claude.json`
- **AND WHEN** that auth bundle does not provide `claude_state.template.json`
- **THEN** launch preparation continues without treating the missing template as a configuration error
- **AND THEN** unattended startup uses the projected `.claude.json` as the seed Claude runtime state

#### Scenario: Bootstrap preserves projected `.credentials.json`
- **WHEN** an orchestrated Claude launch uses an auth bundle with projected `.credentials.json`
- **AND WHEN** unattended launch preparation applies strategy-owned trust or onboarding mutations
- **THEN** launch preparation leaves `.credentials.json` intact as projected vendor login state
- **AND THEN** it does not rewrite that file as though it were strategy-owned bootstrap state

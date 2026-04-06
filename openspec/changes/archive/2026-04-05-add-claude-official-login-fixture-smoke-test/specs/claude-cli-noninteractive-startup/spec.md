## MODIFIED Requirements

### Requirement: Claude auth bundles may provide vendor login-state files for isolated runtime homes
The Claude auth bundle SHALL support optional vendor login-state files for the isolated runtime Claude home, including:

- `.credentials.json`
- `.claude.json`

When those files are present in the selected Claude auth bundle, auth projection SHALL place them at the runtime Claude config root under the same filenames.

Launch preparation SHALL treat a projected `.claude.json` as existing Claude runtime state, SHALL NOT require `claude_state.template.json` solely because that projected runtime state came from imported vendor login state, and SHALL preserve projected `.credentials.json` without rewriting it.

For this lane, the projected `.claude.json` MAY be a minimized valid JSON object, including `{}`, rather than a full copy of vendor-global state. Unrelated absent vendor-global fields SHALL NOT by themselves make unattended startup invalid when strategy-owned startup, trust, or approval state can be merged at launch time.

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

#### Scenario: Minimal projected `.claude.json` still supports unattended startup
- **WHEN** an orchestrated Claude launch uses an auth bundle with projected `.credentials.json`
- **AND WHEN** that auth bundle provides `.claude.json` only as a minimized valid JSON object such as `{}`
- **AND WHEN** unattended launch preparation needs to seed strategy-owned trust, onboarding, or approval state
- **THEN** launch preparation treats the minimized `.claude.json` as valid existing runtime state
- **AND THEN** it merges the strategy-owned state it needs without failing only because unrelated vendor-global fields are absent

#### Scenario: Bootstrap preserves projected `.credentials.json`
- **WHEN** an orchestrated Claude launch uses an auth bundle with projected `.credentials.json`
- **AND WHEN** unattended launch preparation applies strategy-owned trust or onboarding mutations
- **THEN** launch preparation leaves `.credentials.json` intact as projected vendor login state
- **AND THEN** it does not rewrite that file as though it were strategy-owned bootstrap state

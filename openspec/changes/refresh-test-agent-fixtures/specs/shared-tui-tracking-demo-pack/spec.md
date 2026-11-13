# Spec Delta

## MODIFIED Requirements

### Requirement: The restored demo SHALL materialize a demo-local `default` auth alias for the selected tool

Each credential-bearing demo run SHALL prepare an external private working tree and a selected-tool `default` credential alias from the configured generic API case or an explicitly selected imported native bundle. It SHALL materialize a run-local copy rather than link the live runtime to a reusable source bundle. Tracked presets MAY retain `auth: default`. Missing selected inputs SHALL fail preflight.

#### Scenario: Claude run creates a local default auth alias
- **WHEN** an operator starts a configured Claude demo run
- **THEN** its generated tree receives a run-local Claude `default` credential selection
- **AND THEN** the material derives from the selected API case or external imported bundle without a repository-local credential source

#### Scenario: Codex run creates a local default auth alias
- **WHEN** an operator starts a configured Codex demo run
- **THEN** its generated tree receives a run-local Codex `default` credential selection and matching provider routing
- **AND THEN** it does not require the fixed Yunwu bundle or endpoint

#### Scenario: Missing local auth source fails during preflight
- **WHEN** a selected credential source or required API reference is absent
- **THEN** the demo fails before launching the client
- **AND THEN** the error names the missing input and supported discovery/import or configuration action

### Requirement: The restored demo SHALL materialize a Kimi default auth alias from host-local state

The Kimi demo SHALL prepare its `default` credential from the selected API configuration or an explicit external imported Kimi bundle. Native imports SHALL cover supported `config.toml`, `credentials/kimi-code.json`, and allowlisted env values without copying unrelated home state. API runs SHALL require no OAuth file. Missing selected inputs SHALL fail before tmux launch.

#### Scenario: Kimi run creates a local default auth alias
- **WHEN** an operator starts a Kimi demo with an available selected credential source
- **THEN** its external generated tree contains a run-local Kimi `default` credential selection
- **AND THEN** native credentials are copied from the selected imported bundle or API credentials are resolved from the configured case

#### Scenario: Missing Kimi auth source fails during preflight
- **WHEN** the selected Kimi credential source or required API input is unavailable
- **THEN** the demo fails before launching tmux
- **AND THEN** it identifies the missing input without requiring `tests/fixtures/auth-bundles/kimi/personal-a-default/`

## ADDED Requirements

### Requirement: Live tracker workflows accept explicit prepared fixture inputs

Live-watch and recorded-capture entrypoints SHALL accept a prepared run selection through `--prepared-run`. They SHALL validate its selected tool and usable external assets before launching. Missing or incompatible prepared inputs SHALL produce an actionable error without falling back to personal auth paths. Offline validation without client execution SHALL remain credential-free.

#### Scenario: Prepared configuration reaches the selected tracker workflow
- **WHEN** a live tracker workflow receives compatible prepared inputs for its selected tool
- **THEN** it copies the selected setup/auth material into its own private generated tree and retains its existing capture ownership

#### Scenario: Prepared tool differs from requested capture tool
- **WHEN** a capture selects Kimi but receives prepared inputs for another tool
- **THEN** the workflow fails before client launch and identifies the mismatch

#### Scenario: Offline validation needs no credentials
- **WHEN** recorded evidence is validated without launching a client
- **THEN** the workflow requires neither a prepared authenticated run nor a local credential store

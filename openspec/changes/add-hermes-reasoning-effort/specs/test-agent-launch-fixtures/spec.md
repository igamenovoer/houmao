# Spec Delta

## ADDED Requirements

### Requirement: Hermes Fixtures Apply Exact Reasoning Effort

Raw and manager Hermes fixtures SHALL accept the native effort from `--reasoning-effort` or the selected model-pool entry's `reasoning_effort` field and validate it using the managed Hermes Chat Completions vocabulary. Raw runs SHALL project the effort directly into their private Hermes config. Manager runs SHALL carry it as a native default through the managed launch path.

#### Scenario: One Model-Pool Effort Works in Both Lanes

- **WHEN** a developer selects a Hermes pool entry with `reasoning_effort = "xhigh"` for raw and manager runs
- **THEN** each launch's own private config contains `agent.reasoning_effort: xhigh`
- **AND THEN** the result matches direct fixture preparation with `--reasoning-effort xhigh`

#### Scenario: Fixture Validation Rejects Unsupported Reasoning Metadata

- **WHEN** a Hermes fixture supplies an invalid native effort or a reasoning option specific to a different client
- **THEN** `fixture.py check` and `fixture.py prepare` report the unsupported input before allocating a run directory

### Requirement: Manager Hermes Fixtures Select an Exact Launch Preset

A manager Hermes fixture SHALL accept a numeric `reasoning_level` from its selected model-pool entry or `--reasoning-level` from the command line. The explicit CLI level SHALL override the pool level. `check` and `prepare` SHALL require a valid exact index from the Hermes ladder before allocating run state. The generated profile SHALL carry that level to the managed launch.

#### Scenario: The Manager Profile Selects Xhigh

- **WHEN** a developer prepares a Hermes manager fixture with `--reasoning-level 5`
- **THEN** the generated `fixture-agent` profile contains level `5`
- **AND THEN** the actual managed runtime home contains `agent.reasoning_effort: xhigh` after launch

#### Scenario: An Out-of-Range Fixture Preset Fails Preflight

- **WHEN** a Hermes manager fixture resolves a level above `6`
- **THEN** `fixture.py check` and `fixture.py prepare` report the supported range before allocating a run directory

#### Scenario: A Raw Fixture Requires a Native Effort Label

- **WHEN** a raw Hermes fixture resolves a numeric reasoning level from the CLI or a pool entry
- **THEN** `fixture.py check` and `fixture.py prepare` reject the level before allocating a run directory
- **AND THEN** the error directs the developer to use the native effort label for a raw run

### Requirement: Hermes Reasoning Qualification Observes the Main Model Request

Hermes fixture qualification SHALL verify explicit reasoning projection on a main-model Chat Completions request to a controlled endpoint using synthetic credentials.

#### Scenario: The Synthetic Endpoint Receives the Selected Effort

- **WHEN** qualification sends main-model prompts through fixtures launched with `xhigh` and with reasoning explicitly disabled
- **THEN** the peer observes top-level `reasoning_effort` values of `xhigh` and `none`, respectively
- **AND THEN** the qualification records the observed effort without credentials

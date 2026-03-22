## ADDED Requirements

### Requirement: Live watch SHALL resolve launch and observation defaults from the demo-owned config
The live watch workflow under `scripts/demo/shared-tui-tracking-demo-pack/` SHALL load demo-owned defaults from `demo-config.toml` for tool launch posture, output layout, tmux observation cadence, tracker-semantic timing, and dashboard-related presentation settings unless a later override source is applied.

The default live observation cadence SHALL use the same `sample_interval_seconds = 0.2` baseline as the recorded-validation workflow unless explicitly overridden.

#### Scenario: Live watch starts with demo-owned defaults
- **WHEN** a developer starts a live watch run without overriding observation cadence
- **THEN** the workflow resolves its defaults from the demo-owned config
- **AND THEN** the live observation path uses the demo-owned `0.2s` sampling baseline by default

### Requirement: Live watch SHALL persist the resolved demo config with the run
Each live watch run SHALL persist the resolved demo configuration that governed the run after defaults and overrides are merged.

The retained config artifact SHALL allow developers to inspect which tool-launch, evidence, semantic, and presentation knobs were active for that run when reviewing the live dashboard output or the finalized offline analysis.

#### Scenario: Completed live watch run records its governing config
- **WHEN** a developer stops a live watch run
- **THEN** the run output contains the resolved demo configuration for that run
- **AND THEN** the persisted config can be used to reason about how the observed state behavior relates to the run’s launch and capture settings

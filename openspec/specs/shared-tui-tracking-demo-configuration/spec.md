# shared-tui-tracking-demo-configuration Specification

## Purpose
Define the demo-owned configuration contract for the shared tracked-TUI demo pack, including visible defaults, deterministic config resolution, and capture-frequency sweep definitions.

## Requirements

### Requirement: Demo pack SHALL expose a checked-in demo-owned configuration file
The shared tracked-TUI demo pack SHALL expose a checked-in configuration file at `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml` that defines the demo’s supported defaults and named profiles.

The configuration contract SHALL be developer-facing and SHALL document configurable launch, capture, semantic, presentation, and output-path knobs without requiring developers to inspect Python constants or scenario JSON files to discover them.

#### Scenario: Developer inspects the demo’s supported defaults
- **WHEN** a developer opens the shared tracked-TUI demo pack
- **THEN** a checked-in `demo-config.toml` exists under the demo directory
- **AND THEN** that file exposes the supported defaults and named profiles for the demo workflow

### Requirement: Demo config SHALL distinguish evidence, semantics, presentation, and launch controls
The demo-owned configuration SHALL separate knobs by semantic role so developers can reason about whether a setting changes the evidence stream, the standalone tracker’s public-state timing, or only human-facing artifact rendering.

At minimum, the configuration SHALL expose distinct sections or equivalents for:

- tool launch defaults,
- output and fixture paths,
- evidence production controls,
- tracker-semantic controls,
- review-video presentation controls,
- named profiles, and
- sweep definitions.

The default evidence cadence SHALL set tmux sampling to `0.2s`.

#### Scenario: Default capture cadence aligns with Houmao baseline
- **WHEN** a developer runs the shared tracked-TUI demo without overriding evidence cadence
- **THEN** the resolved configuration uses `sample_interval_seconds = 0.2`
- **AND THEN** that default is visible as a demo-owned config value rather than only as an implementation constant

### Requirement: Demo config resolution SHALL be deterministic and persisted with run artifacts
The shared tracked-TUI demo workflow SHALL resolve effective configuration values in a deterministic order that includes demo defaults and any selected overrides such as profile selection, scenario overrides, and CLI overrides.

Each run SHALL persist the resolved configuration inside the run output so later comparison, reporting, and debugging can identify which launch, evidence, semantic, and presentation settings governed that run.

#### Scenario: Run artifacts explain which settings actually governed the run
- **WHEN** a developer completes a recorded-validation or live-watch run
- **THEN** the run output includes the resolved demo configuration that governed that run
- **AND THEN** the persisted config reflects the deterministic merge order of defaults and overrides

### Requirement: Demo config SHALL support capture-frequency robustness sweeps through transition contracts
The demo-owned configuration SHALL support named sweep definitions that vary tmux capture cadence for the same scenario or fixture workflow.

Robustness sweeps SHALL evaluate the standalone tracker against transition-level contracts such as required transition families, terminal-result expectations, forbidden terminal outcomes, and timing tolerances, rather than assuming one canonical per-sample ground-truth timeline remains valid across all sampling cadences.

#### Scenario: Frequency sweep evaluates robustness without reusing per-sample GT as a cadence-invariant oracle
- **WHEN** a developer runs a capture-frequency sweep from the demo-owned configuration
- **THEN** the workflow executes the configured cadence variants
- **AND THEN** each variant is evaluated against transition-contract expectations rather than only against one canonical sample-aligned ground-truth timeline

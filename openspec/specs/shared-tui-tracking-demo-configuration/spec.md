# shared-tui-tracking-demo-configuration Specification

## Purpose
Define the demo-owned configuration contract for the shared tracked-TUI demo pack, including visible defaults, deterministic config resolution, and capture-frequency sweep definitions.

## Requirements

### Requirement: Demo pack SHALL expose a checked-in demo-owned configuration file
The shared tracked-TUI demo pack SHALL expose a checked-in configuration file at `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml` that defines the demo’s supported defaults and named profiles.

The demo pack SHALL also expose a dedicated developer-facing configuration reference document under `scripts/demo/shared-tui-tracking-demo-pack/` that explains the supported config sections, merge behavior, profile behavior, sweep behavior, and config selection workflow.

The configuration contract SHALL be developer-facing and SHALL document configurable launch, capture, semantic, presentation, and output-path knobs without requiring developers to inspect Python constants or scenario JSON files to discover them.

#### Scenario: Developer inspects the demo’s supported defaults
- **WHEN** a developer opens the shared tracked-TUI demo pack
- **THEN** a checked-in `demo-config.toml` exists under the demo directory
- **AND THEN** a dedicated config reference document exists under the same demo directory
- **AND THEN** the config file and reference doc together expose the supported defaults and named profiles for the demo workflow

#### Scenario: Developer needs a human-readable explanation of config groups
- **WHEN** a developer reads the dedicated config reference document
- **THEN** the document explains the meaning of the demo’s config sections, profiles, sweeps, and config selection behavior
- **AND THEN** the developer does not need to inspect Python parsing code to understand the supported settings

### Requirement: Demo config SHALL expose live-watch recorder capture as an explicit debug control
The shared tracked-TUI demo config SHALL expose whether live-watch runs retain terminal-recorder capture as an explicit operator-facing control independent from recorded-validation capture.

The checked-in default config SHALL disable live-watch recorder capture.

The operator-facing live-watch start workflow SHALL support an explicit override that enables recorder capture for replay debugging without requiring a code change.

#### Scenario: Default demo config keeps live watch in non-recorder mode
- **WHEN** a developer inspects the checked-in shared tracked-TUI demo config
- **THEN** the config exposes the live-watch recorder control
- **AND THEN** the default value disables recorder capture for live-watch runs

#### Scenario: Developer opts into replay-debug capture
- **WHEN** a developer starts live watch with explicit recorder enablement
- **THEN** the workflow resolves the live-watch configuration with recorder capture enabled for that run
- **AND THEN** the resulting run retains recorder-backed artifacts for later replay debugging

### Requirement: Demo config SHALL distinguish evidence, semantics, presentation, and launch controls
The demo-owned configuration SHALL separate knobs by semantic role so developers can reason about whether a setting changes the evidence stream, the standalone tracker’s public-state timing, or only human-facing artifact rendering.

At minimum, the configuration SHALL expose distinct sections or equivalents for:

- tool launch defaults,
- output and fixture paths,
- evidence production controls, including live-watch recorder enablement and observation cadence,
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
The shared tracked-TUI demo workflow SHALL resolve effective configuration values in a deterministic order that includes the selected demo-config file, any selected profile overrides, any selected scenario overrides, and any CLI overrides.

The workflow SHALL support the checked-in `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml` as the default config source and SHALL also support an alternate config path selected through operator-facing demo commands.

Before a config influences launch, capture, validation, or sweep behavior, the workflow SHALL reject malformed or unsupported config payloads with an error that identifies the selected config file.

Each run SHALL persist the resolved configuration inside the run output so later comparison, reporting, and debugging can identify which launch, evidence, semantic, and presentation settings governed that run.

The persisted resolved config SHALL identify the source config path that governed the run.

#### Scenario: Run artifacts explain which settings actually governed the run
- **WHEN** a developer completes a recorded-validation or live-watch run
- **THEN** the run output includes the resolved demo configuration that governed that run
- **AND THEN** the persisted config reflects the deterministic merge order of defaults and overrides
- **AND THEN** the persisted config identifies the source config path that governed the run

#### Scenario: Developer selects an alternate demo config file
- **WHEN** a developer launches an operator-facing demo command with an alternate demo-config path
- **THEN** the workflow resolves settings from that selected config file instead of the companion default config
- **AND THEN** any config-derived path roots and defaults follow the selected config
- **AND THEN** the resolved source config path is persisted with the run artifacts

#### Scenario: Invalid demo config is rejected before workflow behavior begins
- **WHEN** a developer selects a malformed or unsupported demo-config file
- **THEN** the command fails before starting or replaying the demo workflow
- **AND THEN** the error identifies the selected config file and the invalid field or section

### Requirement: Demo config SHALL publish a machine-readable schema
The shared tracked-TUI demo pack SHALL publish a machine-readable JSON Schema under the demo source package that describes the supported demo-config structure, including top-level config sections and the nested structures used by profiles, scenario overrides, and sweeps.

The schema SHALL be maintained as a developer-facing contract artifact rather than only as an implementation detail of the TOML loader.

#### Scenario: Developer inspects the demo source package for the config contract
- **WHEN** a developer looks in the demo source package for the demo-config contract
- **THEN** a packaged JSON Schema for the demo config is present
- **AND THEN** the schema describes the supported config structure and value shapes for the demo workflow

#### Scenario: Schema covers sweep and override structures
- **WHEN** a developer or test inspects the packaged demo-config schema
- **THEN** the schema covers the sections used for profiles, scenario overrides, and named sweeps
- **AND THEN** those structures are described as part of the supported demo-config contract

### Requirement: Demo config SHALL support capture-frequency robustness sweeps through transition contracts
The demo-owned configuration SHALL support named sweep definitions that vary tmux capture cadence for the same scenario or fixture workflow.

Robustness sweeps SHALL evaluate the standalone tracker against transition-level contracts such as required transition families, terminal-result expectations, forbidden terminal outcomes, and timing tolerances, rather than assuming one canonical per-sample ground-truth timeline remains valid across all sampling cadences.

#### Scenario: Frequency sweep evaluates robustness without reusing per-sample GT as a cadence-invariant oracle
- **WHEN** a developer runs a capture-frequency sweep from the demo-owned configuration
- **THEN** the workflow executes the configured cadence variants
- **AND THEN** each variant is evaluated against transition-contract expectations rather than only against one canonical sample-aligned ground-truth timeline

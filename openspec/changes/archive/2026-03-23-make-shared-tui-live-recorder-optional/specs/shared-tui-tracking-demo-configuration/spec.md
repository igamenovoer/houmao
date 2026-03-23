## ADDED Requirements

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

## MODIFIED Requirements

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

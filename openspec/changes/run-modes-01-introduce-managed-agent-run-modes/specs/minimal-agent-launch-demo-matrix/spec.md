# Spec Delta

## MODIFIED Requirements

### Requirement: The demo runner accepts provider and optional headless selection

The supported runner interface for `scripts/demo/minimal-agent-launch/` SHALL require a provider selector, SHALL default to the TUI lane when `--headless` is absent, and SHALL use `--headless` to select the headless lane.

#### Scenario: Runner accepts `--headless` for the headless lane
- **WHEN** an operator invokes the demo runner with `--headless`
- **THEN** the runner translates that selection into a managed-agent launch that uses `--mode headless`

#### Scenario: Runner defaults to the TUI lane
- **WHEN** an operator invokes the demo runner without `--headless`
- **THEN** the runner translates that invocation into a managed-agent launch selecting `tui` explicitly or using that provider's TUI project default

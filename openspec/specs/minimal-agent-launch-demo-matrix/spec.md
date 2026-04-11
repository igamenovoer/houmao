# minimal-agent-launch-demo-matrix Specification

## Purpose
Define the supported provider and transport matrix for the minimal managed-agent launch demo.

## Requirements

### Requirement: The minimal launch demo supports the full Claude/Codex × TUI/headless matrix

The supported `scripts/demo/minimal-agent-launch/` surface SHALL support these four launch lanes while defaulting to TUI for a selected provider:

- `claude_code` + `headless`
- `claude_code` + `tui`
- `codex` + `headless`
- `codex` + `tui`

#### Scenario: Claude headless lane is supported
- **WHEN** an operator runs the demo selecting provider `claude_code` with `--headless`
- **THEN** the demo launches a managed agent on the Claude headless runtime surface
- **AND THEN** the run is treated as part of the supported demo contract

#### Scenario: Claude TUI lane is supported
- **WHEN** an operator runs the demo selecting provider `claude_code` without `--headless`
- **THEN** the demo launches a managed agent on the local interactive Claude TUI runtime surface
- **AND THEN** the run is treated as part of the supported demo contract

#### Scenario: Codex headless lane is supported
- **WHEN** an operator runs the demo selecting provider `codex` with `--headless`
- **THEN** the demo launches a managed agent on the Codex headless runtime surface
- **AND THEN** the run is treated as part of the supported demo contract

#### Scenario: Codex TUI lane is supported
- **WHEN** an operator runs the demo selecting provider `codex` without `--headless`
- **THEN** the demo launches a managed agent on the local interactive Codex TUI runtime surface
- **AND THEN** the run is treated as part of the supported demo contract

### Requirement: The demo runner accepts provider and optional headless selection

The supported runner interface for `scripts/demo/minimal-agent-launch/` SHALL require a provider selector, SHALL default to the TUI lane when `--headless` is absent, and SHALL use `--headless` to select the headless lane.

#### Scenario: Runner accepts `--headless` for the headless lane
- **WHEN** an operator invokes the demo runner with `--headless`
- **THEN** the runner translates that selection into a managed-agent launch that uses `--headless`

#### Scenario: Runner defaults to the TUI lane
- **WHEN** an operator invokes the demo runner without `--headless`
- **THEN** the runner translates that invocation into a managed-agent launch without `--headless`

### Requirement: Generated outputs are partitioned by lane

The demo SHALL write reproducible outputs under lane-specific generated output roots so that repeated runs for different provider/transport combinations do not overwrite each other ambiguously.

#### Scenario: Headless and TUI outputs do not collide for one provider
- **WHEN** an operator runs both the headless lane and the TUI lane for the same provider
- **THEN** the generated outputs for those two runs live under distinct lane-specific output roots

#### Scenario: Claude and Codex outputs do not collide across the matrix
- **WHEN** an operator runs multiple provider/transport combinations
- **THEN** the generated outputs for each lane live under distinct lane-specific output roots

### Requirement: TUI launches surface terminal handoff outputs explicitly

For supported TUI lanes, the demo SHALL treat tmux identity and attach guidance as part of the expected outputs.

#### Scenario: Non-interactive caller receives attach guidance for a TUI lane
- **WHEN** an operator runs a supported TUI lane from a non-interactive caller
- **THEN** the launch result surfaces the tmux session identity
- **AND THEN** it surfaces an attach command the operator can run later

#### Scenario: TUI lane publishes transport as `tui`
- **WHEN** an operator inspects the managed-agent state for a supported TUI lane
- **THEN** the state reports transport `tui`
- **AND THEN** the managed agent remains available for follow-up control through its published identity

### Requirement: The tutorial documents the matrix and verification flow

The minimal launch tutorial SHALL document all four supported lanes, their run commands, and the expected verification posture for both headless and TUI launches.

#### Scenario: Reader finds all four lanes in the tutorial
- **WHEN** a reader opens the minimal launch tutorial
- **THEN** the tutorial lists Claude headless, Claude TUI, Codex headless, and Codex TUI as supported demo lanes

#### Scenario: Tutorial explains TUI verification from non-interactive callers
- **WHEN** a reader follows the TUI workflow from a non-interactive shell or automation context
- **THEN** the tutorial explains that Houmao may skip terminal handoff and return an attach command instead

# shared-tui-tracking-live-watch Specification

## Purpose
Define the restored shared TUI tracking live-watch workflow, including demo-local launch assets, dashboard behavior, and retained run artifacts.
## Requirements
### Requirement: Live watch SHALL launch demo-local Claude and Codex sessions with a standalone tracker dashboard

The repository SHALL provide a live interactive watch workflow for the standalone shared TUI tracker under `scripts/demo/shared-tui-tracking-demo-pack/` that can launch either Claude or Codex from the restored demo-local launch assets and bring up a separate tmux-backed dashboard that shows live tracked state.

Recorder-backed observation SHALL be optional for live watch and SHALL only start when the selected live-watch recorder control explicitly enables it.

The workflow SHALL create run roots under a repo-owned subtree such as `tmp/demo/shared-tui-tracking-demo-pack/live/<tool>/<run-id>/`.

#### Scenario: Default live watch starts without recorder capture
- **WHEN** a maintainer starts the restored live-watch workflow for Claude or Codex without enabling recorder capture
- **THEN** the workflow builds a fresh runtime home from a generated run-local agent-definition tree derived from the demo-local launch assets
- **AND THEN** it launches the tool in tmux together with a separate dashboard session
- **AND THEN** it does not start terminal-recorder for that run

#### Scenario: Replay-debug live watch starts with recorder enabled
- **WHEN** a maintainer starts the restored live-watch workflow for Claude or Codex with recorder capture explicitly enabled
- **THEN** the workflow builds a fresh runtime home from a generated run-local agent-definition tree derived from the demo-local launch assets
- **AND THEN** it launches the tool in tmux together with recorder-backed observation and a separate dashboard session
- **AND THEN** it retains recorder metadata for that run together with the normal tool and dashboard attach information

### Requirement: Live watch SHALL resolve launch and observation defaults from the demo-owned config

The restored live-watch workflow SHALL load demo-owned defaults from `demo-config.toml` for tool launch posture, output layout, tmux observation cadence, tracker-semantic timing, dashboard-related presentation settings, and live-watch recorder enablement unless a later override source is applied.

The default live observation cadence SHALL use the same `sample_interval_seconds = 0.2` baseline as the recorded-validation workflow unless explicitly overridden.

The checked-in default live-watch config SHALL disable recorder capture unless a later override source explicitly enables it.

#### Scenario: Live watch starts with demo-owned defaults
- **WHEN** a maintainer starts a restored live-watch run without overriding observation cadence or recorder mode
- **THEN** the workflow resolves its defaults from the demo-owned config
- **AND THEN** the live observation path uses the demo-owned `0.2s` sampling baseline by default
- **AND THEN** the run starts without recorder capture

### Requirement: Live dashboard SHALL derive state from recorder or direct pane evidence through the standalone tracker

The live dashboard SHALL derive displayed state through the standalone shared TUI tracker using runtime liveness observations plus one pane-text evidence source for the watched run.

When recorder capture is enabled, the pane-text evidence source SHALL be recorder pane snapshots for that run. When recorder capture is disabled, the pane-text evidence source SHALL be direct visible-pane tmux captures for that run.

At minimum, the dashboard SHALL present:

- diagnostics availability,
- `surface_accepting_input`,
- `surface_editing_input`,
- `surface_ready_posture`,
- `turn.phase`,
- `last_turn.result`,
- `last_turn.source`,
- detector identity, and
- recent transition information.

#### Scenario: Dashboard updates during a non-recorder run
- **WHEN** a maintainer interacts with the watched Claude or Codex session during a restored live-watch run without recorder capture
- **THEN** the dashboard consumes direct visible-pane tmux captures and runtime observations for that run
- **AND THEN** the displayed state reflects the standalone shared-tracker reduction of those observations

#### Scenario: Dashboard updates during a recorder-enabled run
- **WHEN** a maintainer interacts with the watched Claude or Codex session during a restored live-watch run with recorder capture enabled
- **THEN** the dashboard consumes appended recorder pane snapshots and runtime observations for that run
- **AND THEN** the displayed state reflects the standalone shared-tracker reduction of those observations

### Requirement: Live watch SHALL persist machine-readable artifacts and finalize run analysis

Each restored live-watch run SHALL persist machine-readable state artifacts.

At minimum, every live-watch run SHALL retain:

- `latest_state.json`,
- `state_samples.ndjson`, and
- `transitions.ndjson`.

When recorder capture is enabled, the run SHALL also retain the recorder run root and SHALL be able to finalize offline replay and comparison artifacts from that retained recorder evidence for the same run.

When recorder capture is disabled, stopping the run SHALL still finalize the live summary report and issue documents for the retained live-state artifacts, but the workflow SHALL NOT claim recorder-backed replay or comparison artifacts for that run.

#### Scenario: Stopped non-recorder run retains live-state artifacts
- **WHEN** a maintainer stops a restored live-watch run that did not enable recorder capture
- **THEN** the run root still contains machine-readable live state and transition artifacts for that run
- **AND THEN** the finalized report identifies that recorder-backed replay evidence was not retained

#### Scenario: Stopped recorder-enabled run retains offline-debuggable artifacts
- **WHEN** a maintainer stops a restored live-watch run that enabled recorder capture
- **THEN** the run root still contains recorder artifacts together with machine-readable live state and transition artifacts
- **AND THEN** the workflow can finalize replay and comparison outputs from that retained evidence without reconnecting to a live tmux session

### Requirement: Live watch SHALL launch Kimi Code sessions with the standalone tracker dashboard
The shared TUI tracking live-watch workflow SHALL support `--tool kimi`.

When started for Kimi, live watch SHALL build a fresh Kimi runtime home from the generated run-local agent-definition tree derived from demo-local Kimi launch assets, launch the Kimi Code TUI in tmux, and start the standalone tracker dashboard for the Kimi run.

Recorder-backed live observation SHALL remain optional for Kimi and SHALL only start when explicitly enabled by the selected config or CLI controls.

#### Scenario: Default Kimi live watch starts without recorder capture
- **WHEN** a maintainer starts `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool kimi` without enabling recorder capture
- **THEN** the workflow builds a fresh Kimi runtime home from demo-local Kimi launch assets
- **AND THEN** it launches Kimi Code in tmux together with a separate dashboard session
- **AND THEN** it does not start terminal-recorder for that run

#### Scenario: Recorder-enabled Kimi live watch retains replay-debug evidence
- **WHEN** a maintainer starts Kimi live watch with recorder capture enabled
- **THEN** the workflow launches Kimi Code in tmux together with recorder-backed observation and a separate dashboard session
- **AND THEN** it retains recorder metadata for that run with the normal tool and dashboard attach information

### Requirement: Kimi live dashboard SHALL report `kimi_code` tracker state
The live dashboard for a Kimi run SHALL derive displayed state through the standalone shared TUI tracker using the `kimi_code` detector profile family selected by the shared profile registry.

The Kimi dashboard SHALL present the same public tracked-state fields as other tools, including diagnostics availability, input posture, turn phase, last-turn result/source, detector identity, and recent transition information.

The Kimi dashboard SHALL treat footer model metadata such as a model name followed by `thinking` according to the shared Kimi signal contract: footer metadata alone SHALL NOT mark the turn active.

#### Scenario: Dashboard updates during Kimi ready and active states
- **WHEN** a maintainer interacts with a watched Kimi Code session during live watch
- **THEN** the dashboard consumes visible-pane evidence and runtime observations for that Kimi run
- **AND THEN** the displayed state reflects `kimi_code` shared-tracker reduction

#### Scenario: Kimi footer thinking metadata remains ready
- **WHEN** the watched Kimi pane shows a ready prompt and footer text containing `thinking`
- **AND WHEN** no current active-turn or approval evidence is visible
- **THEN** the dashboard does not report an active turn solely from that footer text

### Requirement: Kimi live watch SHALL expose manual inspection commands and artifacts
Each Kimi live-watch run SHALL persist the same machine-readable live artifacts as other supported tools, including `latest_state.json`, `state_samples.ndjson`, `transitions.ndjson`, and the resolved demo config.

The live-watch start and inspect outputs SHALL include Kimi tool attach and dashboard attach commands so maintainers can manually inspect the Kimi TUI and tracker dashboard.

#### Scenario: Kimi inspect output reports attach commands
- **WHEN** a maintainer inspects a running Kimi live-watch run
- **THEN** the inspect payload reports the Kimi tool attach command
- **AND THEN** it reports the dashboard attach command for the same Kimi run


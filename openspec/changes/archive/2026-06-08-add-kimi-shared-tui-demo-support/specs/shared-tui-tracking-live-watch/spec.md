## ADDED Requirements

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

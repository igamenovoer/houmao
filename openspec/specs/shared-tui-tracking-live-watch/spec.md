# shared-tui-tracking-live-watch Specification

## Purpose
Define the live watch workflow for the standalone shared tracked-TUI module, including fixture-backed tool launch, dashboard behavior, retained machine-readable state artifacts, and final offline replay/comparison.

## Requirements

### Requirement: Live watch SHALL launch fixture-backed Claude and Codex sessions with a standalone tracker dashboard
The repository SHALL provide a live interactive watch workflow for the standalone shared TUI tracker under `scripts/demo/shared-tui-tracking-demo-pack/` that can launch either Claude or Codex from repository fixture brains and bring up a separate tmux-backed dashboard that shows live tracked state.

Recorder-backed observation SHALL be optional for live watch and SHALL only start when the selected live-watch recorder control explicitly enables it.

The workflow SHALL create run roots under a repo-owned subtree such as `tmp/demo/shared-tui-tracking-demo-pack/live/<tool>/<run-id>/`.

#### Scenario: Developer starts a default live watch run for one supported tool
- **WHEN** a developer starts the shared-tracker live watch workflow for Claude or Codex without enabling recorder capture
- **THEN** the workflow builds a fresh runtime home from `tests/fixtures/agents/`
- **AND THEN** it launches the tool in tmux together with a separate dashboard session
- **AND THEN** it does not start terminal-recorder for that run
- **AND THEN** it returns the run root and attach information for both the live tool session and the dashboard

#### Scenario: Developer starts a replay-debug live watch run with recorder enabled
- **WHEN** a developer starts the shared-tracker live watch workflow for Claude or Codex with recorder capture explicitly enabled
- **THEN** the workflow builds a fresh runtime home from `tests/fixtures/agents/`
- **AND THEN** it launches the tool in tmux together with recorder-backed observation and a separate dashboard session
- **AND THEN** it retains recorder metadata for that run together with the normal tool and dashboard attach information

### Requirement: Live watch SHALL use permissive supported launch posture by default
Normal live watch launches SHALL use the most permissive supported posture so developers do not hit unexpected approval or sandbox stalls during ordinary observation runs.

For Claude, the workflow SHALL include `--dangerously-skip-permissions`.

For Codex, the generated runtime home SHALL use the repo-supported permissive bootstrap posture with `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.

#### Scenario: Live watch run starts without an unexpected approval stall
- **WHEN** a developer launches a normal live watch run for Claude or Codex
- **THEN** the workflow uses the tool’s permissive supported posture by default
- **AND THEN** the resulting live session is not expected to stop on an unexpected approval or sandbox prompt during ordinary use

### Requirement: Live watch SHALL resolve launch and observation defaults from the demo-owned config
The live watch workflow under `scripts/demo/shared-tui-tracking-demo-pack/` SHALL load demo-owned defaults from `demo-config.toml` for tool launch posture, output layout, tmux observation cadence, tracker-semantic timing, dashboard-related presentation settings, and live-watch recorder enablement unless a later override source is applied.

The default live observation cadence SHALL use the same `sample_interval_seconds = 0.2` baseline as the recorded-validation workflow unless explicitly overridden.

The checked-in default live-watch config SHALL disable recorder capture unless a later override source explicitly enables it.

#### Scenario: Live watch starts with demo-owned defaults
- **WHEN** a developer starts a live watch run without overriding observation cadence or recorder mode
- **THEN** the workflow resolves its defaults from the demo-owned config
- **AND THEN** the live observation path uses the demo-owned `0.2s` sampling baseline by default
- **AND THEN** the run starts without recorder capture

#### Scenario: Developer enables recorder capture through an explicit override
- **WHEN** a developer starts a live watch run with an explicit recorder enablement override
- **THEN** the workflow resolves the live-watch config with recorder capture enabled for that run
- **AND THEN** the live observation path retains recorder-backed evidence in addition to normal live-state artifacts

### Requirement: Live dashboard SHALL derive state from recorder and runtime evidence through the standalone tracker
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

#### Scenario: Dashboard updates during a default non-recorder run
- **WHEN** the developer interacts with the watched Claude or Codex session during a live-watch run without recorder capture
- **THEN** the dashboard consumes direct visible-pane tmux captures and runtime observations for that run
- **AND THEN** the displayed state reflects the standalone shared-tracker reduction of those observations

#### Scenario: Dashboard updates during a recorder-enabled run
- **WHEN** the developer interacts with the watched Claude or Codex session during a live-watch run with recorder capture enabled
- **THEN** the dashboard consumes appended recorder pane snapshots and runtime observations for that run
- **AND THEN** the displayed state reflects the standalone shared-tracker reduction of those observations

### Requirement: Live watch SHALL persist machine-readable state artifacts and finalize offline analysis
Each live watch run SHALL persist machine-readable live-state artifacts.

At minimum, every live-watch run SHALL retain:

- `latest_state.json`,
- `state_samples.ndjson`, and
- `transitions.ndjson`.

When recorder capture is enabled, the run SHALL also retain the recorder run root and the workflow SHALL be able to finalize offline replay and comparison artifacts from that retained recorder evidence for the same run.

When recorder capture is disabled, stopping the run SHALL still finalize the live summary report and issue documents for the retained live-state artifacts, but the workflow SHALL NOT claim recorder-backed replay or comparison artifacts for that run.

#### Scenario: Stopped default live watch run retains non-recorder state artifacts
- **WHEN** a developer stops a live watch run that did not enable recorder capture
- **THEN** the run root still contains machine-readable live state and transition artifacts for that run
- **AND THEN** the finalized report identifies that recorder-backed replay evidence was not retained

#### Scenario: Stopped recorder-enabled live watch run retains offline-debuggable artifacts
- **WHEN** a developer stops a live watch run that enabled recorder capture
- **THEN** the run root still contains recorder artifacts together with machine-readable live state and transition artifacts
- **AND THEN** the workflow can finalize replay and comparison outputs from that retained evidence without reconnecting to a live tmux session

### Requirement: Live watch SHALL persist the resolved demo config with the run
Each live watch run SHALL persist the resolved demo configuration that governed the run after defaults and overrides are merged.

The retained config artifact SHALL allow developers to inspect which tool-launch, evidence, semantic, and presentation knobs were active for that run when reviewing the live dashboard output or the finalized offline analysis.

#### Scenario: Completed live watch run records its governing config
- **WHEN** a developer stops a live watch run
- **THEN** the run output contains the resolved demo configuration for that run
- **AND THEN** the persisted config can be used to reason about how the observed state behavior relates to the run’s launch and capture settings

### Requirement: Live watch SHALL finalize with a Markdown summary report and separate issue docs
Stopping a live watch run SHALL produce a human-readable Markdown report inside the run output directory that explains what worked and what did not during that run.

That report SHALL summarize the observed live state behavior, the final replay/comparison verdict, and the important artifact locations for the run.

When the finalized run detects mismatches, failures, or other actionable issues, the workflow SHALL also write one separate Markdown issue document per issue inside an issue-specific subdirectory under the same output directory.

#### Scenario: Stopped live watch run writes summary and issue docs
- **WHEN** a developer stops a live watch run that exposed one or more tracker or comparison problems
- **THEN** the run output directory contains a Markdown summary report describing what worked and what did not
- **AND THEN** the run output directory also contains one or more separate Markdown issue documents for the detected problems
- **AND THEN** those issue documents reference the relevant snapshots, transitions, or comparison artifacts for the run

### Requirement: Live watch SHALL remain independent from Houmao server lifecycle routes
The live watch workflow SHALL remain independent from `houmao-server` routes and Houmao session-management CLI subprocesses for its normal start, inspect, dashboard, and stop flow.

The workflow MAY reuse shared Python/library code for runtime-home construction, recorder lifecycle, tmux helpers, direct runtime probing, and standalone-tracker reduction.

#### Scenario: Live watch runs without Houmao server route dependency
- **WHEN** a developer starts, inspects, or stops a shared-tracker live watch run
- **THEN** the workflow uses shared library code plus direct tmux and recorder orchestration for its normal lifecycle
- **AND THEN** it does not require `houmao-server` routes or Houmao session-management CLI subprocesses to perform that workflow

## ADDED Requirements

### Requirement: Live watch SHALL launch fixture-backed Claude and Codex sessions with a standalone tracker dashboard
The repository SHALL provide a live interactive watch workflow for the standalone shared TUI tracker under `scripts/demo/shared-tui-tracking-demo-pack/` that can launch either Claude or Codex from repository fixture brains, start recorder-backed observation, and bring up a separate tmux-backed dashboard that shows live tracked state.

The workflow SHALL create run roots under a repo-owned subtree such as `tmp/demo/shared-tui-tracking-demo-pack/live/<tool>/<run-id>/`.

#### Scenario: Developer starts a live watch run for one supported tool
- **WHEN** a developer starts the shared-tracker live watch workflow for Claude or Codex
- **THEN** the workflow builds a fresh runtime home from `tests/fixtures/agents/`
- **AND THEN** it launches the tool in tmux together with recorder-backed observation and a separate dashboard session
- **AND THEN** it returns the run root and attach information for both the live tool session and the dashboard

### Requirement: Live watch SHALL use permissive supported launch posture by default
Normal live watch launches SHALL use the most permissive supported posture so developers do not hit unexpected approval or sandbox stalls during ordinary observation runs.

For Claude, the workflow SHALL include `--dangerously-skip-permissions`.

For Codex, the generated runtime home SHALL use the repo-supported permissive bootstrap posture with `approval_policy = "never"` and `sandbox_mode = "danger-full-access"`.

#### Scenario: Live watch run starts without an unexpected approval stall
- **WHEN** a developer launches a normal live watch run for Claude or Codex
- **THEN** the workflow uses the tool’s permissive supported posture by default
- **AND THEN** the resulting live session is not expected to stop on an unexpected approval or sandbox prompt during ordinary use

### Requirement: Live dashboard SHALL derive state from recorder and runtime evidence through the standalone tracker
The live dashboard SHALL consume recorder pane snapshots and runtime liveness observations for the watched run and SHALL derive displayed state through the standalone shared TUI tracker rather than through a second ad hoc parsing contract.

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

#### Scenario: Dashboard updates as the live surface changes
- **WHEN** the developer interacts with the watched Claude or Codex session
- **THEN** the dashboard consumes appended recorder and runtime observations for that run
- **AND THEN** the displayed state reflects the standalone shared-tracker reduction of those observations

### Requirement: Live watch SHALL persist machine-readable state artifacts and finalize offline analysis
Each live watch run SHALL persist machine-readable live-state artifacts in addition to raw recorder output.

At minimum, the run SHALL retain:

- `latest_state.json`,
- `state_samples.ndjson`,
- `transitions.ndjson`, and
- the recorder run root.

When the run stops, the workflow SHALL be able to finalize offline replay and comparison artifacts from the retained recorder evidence for that same run.

#### Scenario: Stopped live watch run retains offline-debuggable artifacts
- **WHEN** a developer stops a live watch run
- **THEN** the run root still contains recorder artifacts together with machine-readable live state and transition artifacts
- **AND THEN** the workflow can finalize replay and comparison outputs from that retained evidence without reconnecting to a live tmux session

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

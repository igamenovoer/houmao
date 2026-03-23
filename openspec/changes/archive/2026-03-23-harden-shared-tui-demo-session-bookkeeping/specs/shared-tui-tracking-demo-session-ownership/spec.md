## ADDED Requirements

### Requirement: Demo runs SHALL persist a run-local tmux ownership artifact before workflow-owned sessions are created
The shared tracked-TUI demo pack SHALL create a run-local ownership artifact for both `recorded-capture` and `live watch` runs before launching any workflow-owned tmux session.

That artifact SHALL identify the demo run, the workflow kind, and the owned resource roles for that run, and it SHALL be updated incrementally as tool, dashboard, and recorder resources are created or reaped.

#### Scenario: Recorded capture writes ownership metadata before tool launch
- **WHEN** a developer starts `recorded-capture`
- **THEN** the run root already contains a run-local ownership artifact before the tool tmux session is launched
- **AND THEN** a later startup failure can still resolve that run as a demo-owned cleanup target

#### Scenario: Live watch updates ownership metadata as sessions are created
- **WHEN** a developer starts a live-watch run that creates tool, dashboard, and recorder-backed resources
- **THEN** the ownership artifact is updated as each workflow-owned resource becomes known
- **AND THEN** the artifact records the role and tmux session identity for each created resource when that identity is available

### Requirement: Workflow-owned tmux sessions SHALL publish demo recovery pointers in tmux session environment
Every tmux session started for a shared tracked-TUI demo run SHALL publish secret-free environment pointers that allow recovery code to identify the demo run root or ownership artifact and the role of that tmux session.

This requirement SHALL apply to tool sessions, dashboard sessions, and recorder-owned tmux sessions when recorder startup creates a distinct tmux session.

#### Scenario: Cleanup recovers a tool session from tmux environment
- **WHEN** a workflow-owned tool tmux session is still live but the run's ownership artifact does not contain that session name
- **THEN** recovery code can read tmux session environment for that live session
- **AND THEN** the published pointers identify the same demo run and owned resource role

#### Scenario: Recorder-backed run tags the recorder tmux session
- **WHEN** a demo run starts terminal-recorder and that recorder owns a distinct tmux session
- **THEN** the recorder tmux session also publishes the demo-owned recovery pointers
- **AND THEN** forceful cleanup can identify that recorder session as owned by the same demo run

### Requirement: The demo pack SHALL provide a forceful cleanup path for one run's owned tmux resources
The shared tracked-TUI demo driver under `scripts/demo/shared-tui-tracking-demo-pack/` SHALL provide an operator-facing cleanup command that reaps workflow-owned tmux resources for one targeted run.

Cleanup SHALL resolve owned resources from the run-local ownership artifact first and SHALL use tmux session-environment recovery when the artifact is partial.

When a recorder run root is known, cleanup SHALL stop terminal-recorder through its service API before falling back to direct tmux kill.

The cleanup command SHALL describe itself as recovery-oriented and SHALL NOT claim graceful finalization of live-watch analysis artifacts.

#### Scenario: Cleanup reaps a run with complete ownership metadata
- **WHEN** a developer invokes the demo cleanup command for a run whose ownership artifact lists live tool and dashboard sessions
- **THEN** the workflow reaps those workflow-owned tmux sessions
- **AND THEN** the cleanup result identifies that the run was forcefully cleaned rather than gracefully stopped

#### Scenario: Cleanup reaps a run after partial startup persistence
- **WHEN** a developer invokes the demo cleanup command for a run whose ownership artifact exists but does not contain every created session name
- **THEN** the cleanup path supplements discovery from tmux session environment for sessions published by that run
- **AND THEN** the remaining workflow-owned sessions for that run are reaped

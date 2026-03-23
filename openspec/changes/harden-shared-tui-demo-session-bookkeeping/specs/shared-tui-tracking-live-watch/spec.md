## ADDED Requirements

### Requirement: Live watch SHALL retain recoverable ownership bookkeeping during startup and lifecycle control
The live watch workflow under `scripts/demo/shared-tui-tracking-demo-pack/` SHALL persist run-local ownership bookkeeping before startup completes and SHALL use that bookkeeping during failed-start cleanup and later lifecycle control for the same run.

That bookkeeping SHALL be sufficient to recover workflow-owned tool, dashboard, and recorder resources for the targeted run even when startup was interrupted after tmux resources were already created.

#### Scenario: Failed startup still leaves a recoverable live-watch run
- **WHEN** live-watch startup is interrupted after the tool tmux session is created and before the normal startup path completes
- **THEN** the run retains enough ownership bookkeeping for later recovery to identify the workflow-owned tool session for that run
- **AND THEN** failed-start cleanup does not depend solely on in-memory startup resources

#### Scenario: Stop resolves remaining sessions from durable bookkeeping
- **WHEN** a developer stops a live-watch run whose workflow-owned sessions can no longer be reconstructed from only the happy-path startup metadata
- **THEN** the stop flow uses the run's ownership bookkeeping to resolve the remaining tool, dashboard, and recorder resources for that run
- **AND THEN** it reaps the remaining workflow-owned tmux sessions for that run

#### Scenario: Inspect reports liveness through recovered ownership metadata
- **WHEN** a developer inspects a live-watch run after one workflow-owned session has disappeared but others for the same run are still live
- **THEN** the inspect flow uses the run's ownership bookkeeping to determine which workflow-owned tmux sessions still exist
- **AND THEN** the reported liveness reflects the recovered ownership map for that run rather than only a transient in-memory startup view

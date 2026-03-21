## ADDED Requirements

### Requirement: Interactive watch SHALL reap workflow-owned tmux resources when startup fails or is interrupted
If the interactive Claude watch workflow creates any workflow-owned live resources during `start` and later fails before startup completes, it SHALL perform best-effort cleanup before surfacing the failure.

Workflow-owned live resources include:
- the run's Claude tmux session
- the run's dashboard tmux session
- the run's passive terminal-record session and controller state

This cleanup SHALL apply both to ordinary startup failures and to operator interruption during startup. Cleanup MAY preserve run-local logs and artifact files for debugging, but it SHALL NOT leave workflow-owned tmux sessions running for that failed start attempt.

#### Scenario: Dashboard startup failure reaps partial run resources
- **WHEN** the interactive watch workflow has already launched the Claude tmux session and started passive terminal recording
- **AND WHEN** dashboard startup later fails before the run reaches steady state
- **THEN** the workflow reaps the run's Claude, dashboard, and recorder tmux resources before returning failure
- **AND THEN** any retained run-root artifacts belong only to failure evidence, not to a still-live watch session

#### Scenario: Operator interruption during startup reaps partial run resources
- **WHEN** an operator interrupts the interactive watch workflow while startup is still in progress
- **AND WHEN** the run has already created one or more workflow-owned tmux or recorder resources
- **THEN** the workflow performs best-effort cleanup of those resources before propagating the interruption
- **AND THEN** the interrupted startup does not leave orphaned `cc-track-*` or `HMREC-*` tmux sessions behind

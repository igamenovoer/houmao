## MODIFIED Requirements

### Requirement: Interactive watch pack SHALL launch a recorder-backed Claude session from canonical repository fixtures with a live dashboard
The repository SHALL provide an interactive Claude state-tracking watch workflow under `scripts/explore/claude-code-state-tracking/` that can build a fresh Claude runtime home from canonical preset-backed fixture inputs under `tests/fixtures/plain-agent-def/`, launch the generated `launch.sh` in tmux, start recorder-backed observation, and bring up a live dashboard for the same run.

The interactive watch SHALL provide, at minimum:

- a `start` workflow that creates a fresh run root,
- a run-local runtime root under that run root for generated brain artifacts,
- a Claude launch path driven by a tracked role preset together with the matching tool setup bundle and selected auth bundle from the maintained plain direct-dir lane,
- a tmux-backed Claude session for manual prompting,
- a live dashboard process or session,
- terminal-recorder capture in `passive` mode,
- runtime liveness observation, and
- explicit attach information for the Claude session and dashboard.

#### Scenario: Operator starts an interactive watch run
- **WHEN** a developer starts the interactive Claude watch workflow
- **THEN** the workflow builds a fresh Claude runtime home from canonical preset-backed repository fixtures under `tests/fixtures/plain-agent-def/` and launches its generated `launch.sh` in tmux together with recorder-backed observation and a live dashboard
- **AND THEN** the generated brain home and manifest live under that run's own runtime subtree rather than a shared global runtime directory
- **AND THEN** the workflow returns the run root and attach points for both the Claude session and the dashboard

## MODIFIED Requirements

### Requirement: Recorder start targets an existing tmux session or pane
The repository SHALL provide a terminal-record start flow that targets an already-running tmux session or pane rather than launching a new agent process.

The start flow SHALL require a target tmux session identifier and MAY accept an explicit target pane identifier.

Pane resolution for the addressed tmux session SHALL enumerate panes across the full session rather than only the current tmux window.

If the target session contains multiple panes across one or more windows and the caller does not provide an explicit target pane, the recorder SHALL fail with an explicit target-selection error instead of guessing.

On successful start, the recorder SHALL create one recorder run root, persist live run state, and return enough information for a later `status` or `stop` command to address the same recorder process.

#### Scenario: Start targets an existing single-pane tmux session
- **WHEN** a developer starts the recorder against an existing tmux session that has one targetable pane
- **THEN** the recorder resolves that pane without launching a new agent process
- **AND THEN** it persists live run state for later control operations

#### Scenario: Ambiguous target pane fails explicitly
- **WHEN** a developer starts the recorder against a tmux session with multiple panes
- **AND WHEN** they do not provide an explicit target pane
- **THEN** the recorder fails with an explicit target-selection error
- **AND THEN** it does not silently choose one pane

#### Scenario: Explicit target pane may live outside the current window
- **WHEN** a developer starts the recorder against tmux session `S`
- **AND WHEN** the requested explicit target pane belongs to a non-current window in `S`
- **THEN** the recorder resolves that pane successfully from the full session-wide pane set
- **AND THEN** it does not require the pane's window to be current

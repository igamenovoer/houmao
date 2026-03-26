## Purpose
Define the lifecycle and control contract for the tmux-backed terminal recorder that targets already-running agent sessions.

## Requirements

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

### Requirement: Recorder exposes long-running start, status, and stop control
The terminal recorder SHALL run as a long-lived process after `start` and SHALL support later `status` and `stop` control against the persisted run state.

The `status` flow SHALL report whether the recorder is still active together with the selected mode, target tmux session, target pane, and artifact root.

The `stop` flow SHALL request orderly shutdown, capture final run metadata, and mark the run as inactive without deleting preserved recorder artifacts.

#### Scenario: Status reports one active recorder run
- **WHEN** a developer invokes the recorder status flow for an active run
- **THEN** the tool reports that the recorder process is active
- **AND THEN** it returns the selected mode, tmux target, and artifact root for that run

#### Scenario: Stop finalizes an active run
- **WHEN** a developer invokes the recorder stop flow for an active run
- **THEN** the recorder shuts down in an orderly way
- **AND THEN** the persisted run state is marked inactive while preserved artifacts remain on disk

### Requirement: Recorder supports explicit active and passive modes
The terminal recorder SHALL support exactly two operating modes, `active` and `passive`, with different input-capture guarantees.

In `active` mode, the recorder SHALL provide a recorder-owned interactive path for the target tmux session and SHALL surface an attach target for that recorder-owned client session.

In `passive` mode, the recorder SHALL observe the target tmux session without requiring the user to abandon their existing tmux inspection workflow.

The selected mode SHALL be persisted in recorder metadata and SHALL remain stable for the duration of the run.

#### Scenario: Active mode returns a recorder-owned attach target
- **WHEN** a developer starts the recorder in `active` mode
- **THEN** the recorder creates or resolves a recorder-owned interactive session for the target
- **AND THEN** startup output includes an attach target for that recorder-owned client path

#### Scenario: Passive mode does not become the required input path
- **WHEN** a developer starts the recorder in `passive` mode
- **THEN** the recorder observes the target tmux session without claiming to be the exclusive user input path
- **AND THEN** users may continue to inspect the target tmux session directly

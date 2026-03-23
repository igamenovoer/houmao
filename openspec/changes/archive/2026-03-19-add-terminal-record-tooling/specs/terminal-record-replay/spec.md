## ADDED Requirements

### Requirement: Recorder artifacts support parser and state replay
The repository SHALL provide a replay/analyze flow that consumes recorder pane snapshot artifacts and derives parser-facing and state-tracking observations from the recorded sequence.

The replay/analyze flow SHALL operate over persisted pane snapshots rather than requiring a live tmux session.

At minimum, replay output SHALL be able to preserve sample identity and the derived parser/state observations for each selected snapshot.

#### Scenario: Analyze derives parser and state observations from one recorded run
- **WHEN** a developer runs the replay or analyze flow against one recorded run
- **THEN** the tool reads the persisted pane snapshot sequence without attaching to a live tmux session
- **AND THEN** it emits parser-facing and state-tracking observations keyed to the recorded samples

### Requirement: Replay contracts use pane snapshots as the machine source of truth
For recorder-backed parser and state-tracking tests, the machine-readable replay contract SHALL use the persisted pane snapshot sequence as the source of truth.

The terminal cast MAY be used for operator review, but SHALL NOT be the required parser replay surface for automated state-tracking validation.

#### Scenario: Automated replay does not require cast reconstruction
- **WHEN** automated parser or state-tracking validation runs against recorder artifacts
- **THEN** the validation consumes the pane snapshot sequence as the machine source of truth
- **AND THEN** it does not require reconstructing tmux pane content from the terminal cast

### Requirement: Replay supports operator-provided labels over recorded samples
The repository SHALL support operator-provided labels that annotate selected recorded samples or sample ranges with expected parser or lifecycle meanings.

At minimum, the labeling surface SHALL support stable references to recorded samples together with expected state-oriented fields such as parser classification, readiness/completion interpretation, or scenario identity.

Recorded labels SHALL be persisted as structured artifacts within the recorder run root or in a repo-owned exported fixture layout.

#### Scenario: Operator labels a blocked trust-prompt sample
- **WHEN** a developer labels one recorded sample as a trust-prompt blocked state
- **THEN** the persisted label artifact records a stable reference to that sample
- **AND THEN** downstream replay or tests can assert the expected parser and lifecycle interpretation for that labeled checkpoint

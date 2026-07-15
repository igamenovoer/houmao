## ADDED Requirements

### Requirement: Kimi queued-message surfaces remain busy until retained work is released
The maintained Kimi Code TUI tracker SHALL treat a current source-backed queue pane as evidence that a new independent turn cannot start immediately.

The current Kimi queue-pane evidence SHALL include the bounded hints `ctrl-s to steer immediately`, `will send after current task`, and `will send after compaction` when they occur in the current queue region. A current queue pane SHALL produce active evidence, SHALL set `surface.ready_posture=no`, and SHALL block ready-return success even when the empty editor remains visible and the spinner row falls outside the narrow activity window.

Historical queue-pane text outside the current bounded turn region SHALL NOT keep a later idle editor busy.

#### Scenario: Streaming queue pane blocks readiness
- **WHEN** a Kimi snapshot shows an empty editor and a current queued message with `ctrl-s to steer immediately`
- **THEN** the Kimi profile reports current active evidence
- **AND THEN** it reports `surface.ready_posture=no`

#### Scenario: Deferred current-task queue blocks readiness without a visible spinner
- **WHEN** a Kimi snapshot shows a current queued message with `will send after current task`
- **AND WHEN** no moon or braille spinner is inside the narrow spinner window
- **THEN** the Kimi profile still reports the turn as active and non-ready

#### Scenario: Historical queue text does not block a settled editor
- **WHEN** older queue-pane text exists outside the bounded latest-turn region
- **AND WHEN** the current editor is empty and has no current queue, spinner, approval, or tool activity
- **THEN** the Kimi profile may report the current prompt as ready

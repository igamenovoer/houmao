## ADDED Requirements

### Requirement: Codex current pending-input panes are active-turn evidence
The Codex 0.144 tracked-TUI profile SHALL recognize current pending-steer, rejected-steer, and queued-follow-up sections rendered by the upstream pending-input preview.

The section headers `Messages to be submitted after next tool call`, `Messages to be submitted at end of turn`, and `Queued follow-up inputs` SHALL be treated as non-response current-turn cells. A current section SHALL contribute active evidence and SHALL prevent `surface.ready_posture=yes` even when the ordinary status row is hidden.

Historical pending-input text followed by a later completed assistant response SHALL NOT by itself keep a settled prompt active.

#### Scenario: Pending steer does not hide the working row
- **WHEN** a current Codex surface shows a working row followed by `Messages to be submitted after next tool call`
- **THEN** the pending-input header does not terminate the working-row scan as if it were an assistant response
- **AND THEN** the profile reports the turn as active and non-ready

#### Scenario: Pending steer remains busy while status row is hidden
- **WHEN** a current Codex surface shows a pending-input section while streamed assistant output is growing and the working row is temporarily hidden
- **THEN** the pending-input section independently keeps the current turn active

#### Scenario: Settled historical pending input does not remain active
- **WHEN** a later completed assistant response and clean current prompt supersede historical pending-input text
- **THEN** the historical section alone does not block current ready posture

### Requirement: Codex retry and list-selector activity is bounded to current source-backed surfaces
The Codex tracked-TUI profile SHALL recognize current reconnect activity from the maintained source-backed reconnect status family and SHALL NOT classify arbitrary prose or command descriptions containing `retry` as stream activity.

The profile SHALL treat a current model or list selector with a selection title or rows and the current `Press enter to confirm or esc to go back` footer as a blocking overlay. Historical selector titles or footers outside the current bounded interactive region SHALL NOT block a later prompt.

#### Scenario: Reconnect status is active
- **WHEN** the current Codex status surface displays `Reconnecting... 2/5` or the maintained equivalent reconnect status
- **THEN** the profile reports stream-retry active evidence and blocks ready-return success

#### Scenario: Retry prose is not activity
- **WHEN** current visible prose or a slash-command description contains the word `retry`
- **AND WHEN** no current reconnect status surface exists
- **THEN** the profile does not report stream-retry active evidence from that prose

#### Scenario: Model selector blocks prompt readiness
- **WHEN** the current Codex surface shows `Select Model and Effort` and the list-selection confirmation footer
- **THEN** the profile reports a blocking interactive surface
- **AND THEN** it does not classify the selected `› 1.` row as a submit-ready prompt draft

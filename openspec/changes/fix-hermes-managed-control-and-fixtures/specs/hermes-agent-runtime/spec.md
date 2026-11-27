# Spec Delta

## MODIFIED Requirements

### Requirement: Hermes TUI Uses Native Structured Control

Hermes TUI mode SHALL expose a real Hermes terminal through tmux and use verified native RPC for manager and gateway control. Houmao SHALL pin the exact logical conversation and report terminal attachment separately from native availability. Readiness, turns, and completion SHALL derive from structured evidence.

#### Scenario: Native TUI and Houmao Share One Conversation

- **WHEN** an operator attaches to the pane and sends a turn in the verified conversation
- **THEN** Houmao observes native activity for that session without capturing terminal text
- **AND THEN** later Houmao submissions and corresponding native events appear in the same conversation

#### Scenario: Human Switches or Exits the TUI

- **WHEN** the operator changes the TUI's displayed conversation or closes the TUI client
- **THEN** Houmao reports the changed terminal attachment alongside the original managed conversation
- **AND THEN** automated input and accepted work remain addressed to the pinned conversation
- **AND THEN** changing the managed conversation requires an explicit verified lifecycle or session operation

#### Scenario: Parser-Specific Operations Target Hermes

- **WHEN** a caller requests terminal-parser history, automatic key dispatch, or another parser-specific operation from a Hermes TUI
- **THEN** the operation reports unsupported
- **AND THEN** qualified terminal handoff and structured control remain available

#### Scenario: A Direct Manager Prompt Uses the Native Owner

- **WHEN** a local or delegated manager prompt selects a current Hermes TUI generation with a ready pinned conversation
- **THEN** the manager and gateway use the same owner admission and Hermes native submit path
- **AND THEN** the manager correlates its result to its original owner claim and exact durable native admission
- **AND THEN** submission and settlement work when the gateway is detached or Ink is absent or displaying another conversation

#### Scenario: Manager and Gateway Compete for the Owner Slot

- **WHEN** a manager prompt and a gateway prompt compete for the same pinned conversation and managed generation
- **THEN** the shared owner slot admits at most one prompt while its outcome remains unresolved
- **AND THEN** the refused caller reports that work is outstanding before sending input

#### Scenario: Manager Wait Reports Exact Terminal or Known Admission Evidence

- **WHEN** the manager waits for a submitted Hermes TUI prompt
- **THEN** it reports completion, failure, or interruption only from a terminal receipt attributable to that request
- **AND THEN** if its bounded wait expires with verified queue acceptance or native handoff, it reports that acceptance under the original request ID
- **AND THEN** if admission cannot be established, it reports uncertainty and retains the evidence for reconciliation without replaying the prompt

#### Scenario: A Direct Manager Prompt Finds the Pinned Conversation Busy

- **WHEN** the pinned conversation is busy at the final native readiness check or the selected owner is unavailable
- **THEN** the manager reports the native refusal or unavailable authority before sending input
- **AND THEN** a failed pre-admission attempt does not leave an unresolved slot that prevents the next qualified prompt

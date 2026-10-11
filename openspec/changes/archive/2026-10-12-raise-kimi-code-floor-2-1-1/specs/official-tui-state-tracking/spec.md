# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi Code parser maps visible surfaces to operator state
The Kimi parser SHALL map visible Kimi TUI surfaces into the existing parser-owned operator state vocabulary.

At minimum, the Kimi parser SHALL distinguish:

- prompt-ready main chat surfaces
- active response or tool-use surfaces
- approval dialogs that require operator choice
- agent-initiated question dialogs that require an operator answer
- startup or modal surfaces such as workspace trust, session picker, login, update, or unknown blocking prompts

The parser SHALL classify approval dialogs and agent-initiated question dialogs as operator-blocked and SHALL expose dialog text that includes the command or question being approved or asked when that text is visible.

The parser SHALL classify the `Trust this folder?` workspace-trust modal as a startup modal surface.

The parser SHALL NOT classify Kimi footer model metadata as active-turn evidence by itself.

The parser SHALL classify recognized startup or modal surfaces that block normal prompt entry as unavailable for managed prompt submission until the blocker clears.

#### Scenario: Kimi ready surface maps to ready state
- **WHEN** the captured Kimi pane shows a prompt-ready main chat surface with no current blocker
- **THEN** the parsed surface reports an idle or ready business state and freeform input mode

#### Scenario: Kimi approval dialog maps to operator-blocked state
- **WHEN** the captured Kimi pane shows `Run this command?` and approval or rejection choices
- **THEN** the parsed surface reports an operator-blocked state with modal input context
- **AND THEN** the parsed surface includes the visible approval dialog text

#### Scenario: Kimi question dialog maps to operator-blocked state
- **WHEN** the captured Kimi pane shows an agent-initiated multiple-choice question dialog (question title, numbered options, cancel hint)
- **THEN** the parsed surface reports an operator-blocked state with modal input context
- **AND THEN** the parsed surface includes the visible question text

#### Scenario: Kimi workspace-trust modal maps to startup modal
- **WHEN** the captured Kimi pane shows the `Trust this folder?` startup modal
- **THEN** the parsed surface reports an operator-blocked startup-modal state
- **AND THEN** managed prompt submission is reported as unavailable until the modal clears

#### Scenario: Kimi footer thinking text is not active by itself
- **WHEN** the captured Kimi pane shows footer text containing `thinking`
- **AND WHEN** no current active response, tool-use, or progress surface is visible
- **THEN** the parser does not report active business state solely from that footer text

## ADDED Requirements

### Requirement: Kimi 2.1.x busy evidence is the live-edge spinner union
For kimi-code versions at or above the support floor, current-turn busy evidence SHALL be the union of provider spinner-frame rows at the live edge (moon-phase and braille-phase families). Braille rows SHALL count only when qualified by a 2.1.x busy label (`Thinking…`, `Working…`, `Retrying (N/M)`, `Compacting context…`, `Orchestrating…`, or subagent `… Running (…)` rows); the compaction bullet SHALL count without a spinner frame. An interruption notice SHALL mark the surface interrupted only when no concurrent spinner-union activity is visible. Queue-hint chrome SHALL establish pending input only while visible at the live edge.

#### Scenario: Braille thinking phase reads as busy
- **WHEN** a tracked Kimi 2.1.x pane shows a braille spinner row labeled `Thinking…` or `Working…` at the live edge
- **THEN** the tracked state reports active-turn evidence and not-ready posture
- **AND THEN** no ready state is manufactured between spinner frames

#### Scenario: Resumed turn after interruption stays active
- **WHEN** an `Interrupted by user` notice is visible in scrollback and a queued follow-up turn is actively running below it
- **THEN** tracked state reports the surface as active, not interrupted and not ready

#### Scenario: Queue hint history does not fabricate pending input
- **WHEN** the provider queue pane has drained and its hint text survives only in scrollback history
- **THEN** tracked state reports no provider-owned pending input

### Requirement: Kimi tracked state models modal surfaces and busy-time input acceptance
For kimi-code versions at or above the support floor, a visible composer SHALL classify the surface as accepting input even while a turn is active, because kimi queues text submitted mid-turn. Operator-modal spans (approval panels, question dialogs, goal-start prompts, workspace-trust modal) SHALL close input acceptance while mounted and SHALL report `turn_phase=active` with a blocked reason, because a turn or launch is in flight behind the modal; they SHALL report not-ready posture.

#### Scenario: Composer accepts input while a turn is active
- **WHEN** a Kimi turn is active and the composer remains visible
- **THEN** tracked state reports the surface as accepting input with not-ready posture
- **AND THEN** a submission in that window is understood to enter the provider queue rather than start immediately

#### Scenario: Approval modal reports blocked active turn
- **WHEN** a Kimi approval panel or question dialog is mounted
- **THEN** tracked state reports `turn_phase=active` with a blocked reason, not-ready posture, and closed input acceptance
- **AND THEN** resolving the modal returns tracking to the underlying turn state

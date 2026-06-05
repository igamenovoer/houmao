## ADDED Requirements

### Requirement: Kimi Code TUI launches as a maintained local interactive provider
The system SHALL support `tool = kimi` as a maintained tmux-backed `local_interactive` TUI provider.

Kimi TUI launch SHALL remain distinct from the `kimi_headless` backend. A request for local interactive Kimi SHALL start the interactive Kimi Code TUI, while a request for headless Kimi SHALL continue using the prompt-mode headless backend.

The local interactive Kimi runtime SHALL preserve the existing tmux primary-surface contract, managed runtime home projection, launch-profile environment handling, gateway attachability, and managed-agent metadata publication used by other maintained local interactive providers.

#### Scenario: Kimi local interactive launch starts the TUI
- **WHEN** an operator launches a managed agent for tool `kimi` with local interactive posture
- **THEN** the runtime starts the Kimi Code interactive TUI in the managed tmux primary surface
- **AND THEN** the managed session records backend `local_interactive`
- **AND THEN** the process inspector can later recognize the Kimi TUI as supported

#### Scenario: Kimi headless remains separate
- **WHEN** an operator launches a managed agent for tool `kimi` with headless posture
- **THEN** the runtime continues using backend `kimi_headless`
- **AND THEN** the launch does not inherit Kimi TUI parser, prompt, or relaunch assumptions solely because both modes use the same provider CLI

### Requirement: Kimi Code TUI control uses semantic prompt submission and Escape interruption
For live Kimi Code `local_interactive` sessions, semantic prompt submission SHALL insert the prompt through the existing submit-aware tmux paste path and send the final submit action separately.

The semantic prompt path SHALL treat the whole prompt body as literal text and SHALL NOT interpret raw control-input key tokens inside the prompt body.

For Kimi Code TUI interruption, the runtime SHALL use Escape as the primary interrupt key for active streaming, selection, and approval-modal cancellation.

#### Scenario: Kimi semantic prompt becomes a submitted provider turn
- **WHEN** the runtime semantically submits the prompt `reply exactly OK` into a live Kimi TUI session
- **THEN** Kimi receives the prompt as a submitted provider turn
- **AND THEN** the prompt is not left staged as an unsent editor draft

#### Scenario: Kimi prompt body preserves key-looking text literally
- **WHEN** the runtime semantically submits the prompt body `print <[Enter]> literally` into Kimi TUI
- **THEN** Kimi receives the literal text `<[Enter]>`
- **AND THEN** the runtime does not synthesize an Enter key from that substring before the automatic final submit

#### Scenario: Kimi interrupt uses Escape
- **WHEN** a live Kimi TUI turn is streaming or a Kimi modal surface is active
- **THEN** the runtime interrupt operation sends Escape to the managed pane
- **AND THEN** it does not use double Ctrl+C as the primary interrupt path for Kimi TUI

### Requirement: Kimi Code TUI relaunch supports provider-native session selection
For Kimi Code `local_interactive` sessions, runtime relaunch SHALL translate the shared relaunch chat-session selector into Kimi startup arguments before respawning the provider process in tmux window `0`.

The Kimi TUI relaunch translation SHALL be:

- `new`: no Kimi session-selection arguments
- `tool_last_or_new`: `kimi --continue`
- `exact`: `kimi --session <session_id>`

An exact Kimi relaunch selector SHALL require a non-empty provider-native session id.

#### Scenario: Kimi TUI relaunch starts a fresh chat by default
- **WHEN** an operator relaunches a Kimi TUI managed session without a relaunch chat-session selector
- **THEN** the runtime respawns Kimi Code without `--continue` or `--session`
- **AND THEN** the provider starts a fresh Kimi chat according to native Kimi behavior

#### Scenario: Kimi TUI relaunch resumes latest chat
- **WHEN** an operator relaunches a Kimi TUI managed session with relaunch chat-session mode `tool_last_or_new`
- **THEN** the runtime respawns Kimi Code with `--continue`
- **AND THEN** it does not send a resume request as a prompt after startup

#### Scenario: Kimi TUI relaunch resumes exact chat
- **WHEN** an operator relaunches a Kimi TUI managed session with relaunch chat-session mode `exact` and provider session id `session_abc`
- **THEN** the runtime respawns Kimi Code with `--session session_abc`
- **AND THEN** it rejects the relaunch if the exact selector has no provider session id

### Requirement: Kimi Code TUI exposes ready, active, and approval-blocked state
The Kimi TUI support SHALL expose operator-facing state for prompt-ready surfaces, active response surfaces, and approval-blocked surfaces through the maintained TUI tracking APIs.

The system SHALL treat the visible Kimi editor prompt as ready only when no current approval dialog, session picker, login/update prompt, or active response/tool surface blocks normal prompt submission.

The system SHALL treat Kimi approval dialogs containing command approval choices as operator-blocked surfaces and SHALL include the relevant approval text in detailed parser evidence.

The system SHALL NOT treat footer model metadata such as a model name followed by `thinking` as sufficient evidence that a turn is active.

#### Scenario: Kimi idle editor is ready
- **WHEN** a captured Kimi TUI snapshot shows the editor prompt ready for input and no current blocking dialog or active response surface
- **THEN** the tracked state reports a ready prompt posture
- **AND THEN** operator-facing state reports that the session can accept a managed prompt

#### Scenario: Kimi activity surface is active
- **WHEN** a captured Kimi TUI snapshot shows current response activity, a spinner row, or a current tool-use surface after a submitted prompt
- **THEN** the tracked state reports an active turn posture
- **AND THEN** the operator-facing state does not report the session as ready merely because the editor frame is still visible

#### Scenario: Kimi approval prompt blocks operator progress
- **WHEN** a captured Kimi TUI snapshot shows a command approval dialog with choices such as approve or reject
- **THEN** the parsed surface reports an operator-blocked state
- **AND THEN** detailed state includes the approval dialog text needed for an operator or controller to understand the block

#### Scenario: Kimi footer thinking metadata does not imply active turn
- **WHEN** a captured Kimi TUI snapshot shows footer text containing `thinking`
- **AND WHEN** the current Kimi surface has a submit-ready prompt and no current active-turn evidence
- **THEN** the tracked state does not report an active turn solely from that footer text


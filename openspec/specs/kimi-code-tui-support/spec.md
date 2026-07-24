# kimi-code-tui-support Specification

## Purpose
TBD - created by archiving change add-kimi-tui-support. Update Purpose after archive.
## Requirements
### Requirement: Kimi Code TUI launches as a maintained local interactive provider
The system SHALL support `tool = kimi` as a maintained tmux-backed `local_interactive` TUI provider.

Kimi TUI launch SHALL remain distinct from the `kimi_headless` backend. A request for local interactive Kimi SHALL start the interactive Kimi Code TUI, while a request for headless Kimi SHALL continue using the prompt-mode headless backend.

The local interactive Kimi runtime SHALL preserve the existing tmux primary-surface contract, managed runtime home projection, launch-profile environment handling, gateway attachability, and managed-agent metadata publication used by other maintained local interactive providers.

Kimi Code `local_interactive` role injection SHALL use a bootstrap-message turn rather than an unverified native TUI system prompt flag.

Managed Kimi Code TUI launches SHALL project `KIMI_CODE_NO_AUTO_UPDATE=1` into the launched process environment so Kimi does not stop startup on an interactive update preflight.

#### Scenario: Kimi local interactive launch starts the TUI
- **WHEN** an operator launches a managed agent for tool `kimi` with local interactive posture
- **THEN** the runtime starts the Kimi Code interactive TUI in the managed tmux primary surface
- **AND THEN** the managed session records backend `local_interactive`
- **AND THEN** the process inspector can later recognize the Kimi TUI as supported

#### Scenario: Kimi headless remains separate
- **WHEN** an operator launches a managed agent for tool `kimi` with headless posture
- **THEN** the runtime continues using backend `kimi_headless`
- **AND THEN** the launch does not inherit Kimi TUI parser, prompt, or relaunch assumptions solely because both modes use the same provider CLI

#### Scenario: Kimi TUI launch suppresses update preflight
- **WHEN** Houmao starts a managed Kimi Code local interactive session
- **THEN** the launched Kimi process environment includes `KIMI_CODE_NO_AUTO_UPDATE=1`
- **AND THEN** Houmao does not depend on an interactive Kimi update prompt being absent by chance

#### Scenario: Kimi TUI role injection uses bootstrap message
- **WHEN** a managed Kimi Code local interactive launch has a role prompt
- **THEN** Houmao plans bootstrap-message role injection for Kimi TUI
- **AND THEN** it does not add an unverified Kimi TUI system-prompt CLI flag

### Requirement: Kimi Code TUI launch does not project prompt-mode-only skills-dir arguments
Houmao SHALL NOT add managed `--skills-dir` arguments to Kimi Code `local_interactive` launch commands until Kimi exposes a maintained TUI skills-dir startup mechanism.

Kimi headless prompt-mode behavior SHALL remain free to use its existing managed skills-dir projection where supported.

#### Scenario: Kimi TUI launch omits managed skills-dir args
- **WHEN** Houmao prepares a local interactive Kimi launch with managed skills available
- **THEN** the Kimi TUI launch command does not include managed `--skills-dir` arguments
- **AND THEN** Kimi TUI startup is not treated as supporting prompt-mode-only skills-dir injection

#### Scenario: Kimi headless skills-dir behavior remains distinct
- **WHEN** Houmao prepares a Kimi headless prompt-mode launch
- **THEN** existing Kimi headless skills-dir behavior is governed by the headless launch policy
- **AND THEN** Kimi TUI support does not remove or rename that behavior

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

An exact Kimi relaunch selector SHALL require a non-empty provider-native session id. The runtime SHALL NOT use bare `kimi --session` because that starts Kimi's interactive session picker.

For maintained Kimi 0.23.x, unattended relaunch SHALL combine strategy-owned `--auto` with `--continue` or `--session <session_id>`. The runtime SHALL reject a final command that combines `--auto` with `--yolo`, but it SHALL NOT reject native auto mode solely because a resume selector is present. Kimi TUI relaunch SHALL continue to permit launch-owned `--model <alias>` arguments with resume selectors.

#### Scenario: Kimi TUI relaunch starts a fresh chat by default
- **WHEN** an operator relaunches a Kimi TUI managed session without a chat-session selector
- **THEN** the runtime respawns Kimi without `--continue` or `--session`

#### Scenario: Kimi TUI relaunch resumes latest chat unattended
- **WHEN** an unattended Kimi TUI session relaunches with mode `tool_last_or_new`
- **THEN** the runtime respawns Kimi with `--auto --continue`
- **AND THEN** it does not send a resume or auto-mode request as a prompt after startup

#### Scenario: Kimi TUI relaunch resumes exact chat unattended
- **WHEN** an unattended Kimi TUI session relaunches with mode `exact` and provider session id `session_abc`
- **THEN** the runtime respawns Kimi with `--auto --session session_abc`
- **AND THEN** it rejects the relaunch if the exact selector has no provider session id

#### Scenario: Kimi TUI relaunch avoids interactive picker
- **WHEN** an operator relaunches a Kimi TUI managed session with mode `exact`
- **THEN** the runtime never respawns Kimi with bare `--session`

#### Scenario: Kimi TUI relaunch rejects conflicting permission modes
- **WHEN** final unattended relaunch arguments would contain both `--auto` and `--yolo`
- **THEN** Houmao rejects or canonicalizes the conflict before provider start
- **AND THEN** it does not remove strategy-owned `--auto` merely because a resume selector is present

#### Scenario: Kimi TUI relaunch keeps model selection
- **WHEN** an unattended exact relaunch selects model `kimi-code/kimi-for-coding` and session `session_abc`
- **THEN** the final command contains `--model kimi-code/kimi-for-coding --auto --session session_abc`

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

### Requirement: Kimi unattended TUI startup establishes policy without a conversational turn
Maintained Kimi 0.23.x unattended TUI startup SHALL use native `--auto` before role bootstrap or workload submission. Houmao SHALL NOT submit `/auto on`, answer a confirmation, or send another conversational command to establish the unattended posture.

Normal unattended startup and work SHALL not enter approval, waiting-for-answer, or confirmation states. If Kimi hard-codes an intervention that no supported setting can suppress, Houmao SHALL retain evidence and report it as an explicit exception rather than silently answering it.

#### Scenario: Fresh unattended Kimi starts prompt-free
- **WHEN** Houmao launches a fresh maintained Kimi TUI with unattended prompt mode
- **THEN** the final launch command includes `--auto`
- **AND THEN** the first managed conversational input is role bootstrap or workload content, not a policy command

#### Scenario: Avoidable confirmation fails unattended validation
- **WHEN** a normal unattended Kimi scenario displays a confirmation or user-question surface
- **AND WHEN** current source or CLI settings provide a supported suppression mechanism
- **THEN** validation fails the unattended contract
- **AND THEN** the harness does not answer the prompt automatically

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

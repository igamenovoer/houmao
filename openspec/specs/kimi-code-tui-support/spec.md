# kimi-code-tui-support Specification

## Purpose
TBD - created by archiving change add-kimi-tui-support. Update Purpose after archive.
## Requirements

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

For maintained Kimi 2.1.1 or later, unattended relaunch SHALL combine strategy-owned `--auto` with `--continue` or `--session <session_id>`. The runtime SHALL reject a final command that combines `--auto` with `--yolo`, but it SHALL NOT reject native auto mode solely because a resume selector is present. Kimi TUI relaunch SHALL continue to permit launch-owned `--model <alias>` arguments with resume selectors and SHALL validate the native `SYSTEM.md` contract before respawn.

#### Scenario: Kimi TUI relaunch starts a fresh chat by default
- **WHEN** an operator relaunches a Kimi TUI managed session without a chat-session selector
- **THEN** the runtime respawns Kimi without `--continue` or `--session`

#### Scenario: Kimi TUI relaunch resumes latest chat unattended
- **WHEN** an unattended Kimi TUI session relaunches with mode `tool_last_or_new`
- **THEN** the runtime respawns Kimi with `--auto --continue`
- **AND THEN** it does not send a resume, auto-mode, or role-prompt request as a chat turn after startup

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

Maintained Kimi 2.1.1-or-later TUI startup SHALL apply the resolved native permission mode after role projection and before managed input. Houmao SHALL use `--auto` for the omitted unattended permission mode and a qualified native startup surface for a supported authored value. Launch SHALL establish policy and role outside the conversation.

Under the unattended default, normal startup and work SHALL proceed without approval, answer, or confirmation states. A deliberate approval-setting override SHALL retain its native behavior. If a provider-required intervention remains, Houmao SHALL preserve the evidence and report the intervention.

#### Scenario: Fresh unattended Kimi starts without policy or role chat
- **WHEN** Houmao launches a fresh maintained Kimi TUI in unattended mode with permission mode omitted
- **THEN** the final launch command includes native `--auto` and the managed native prompt is already projected
- **AND THEN** the first managed conversational input is workload content

#### Scenario: Fresh unattended Kimi starts prompt-free
- **WHEN** Houmao starts a fresh maintained Kimi TUI with the unattended default permission mode
- **THEN** native `--auto` and native `SYSTEM.md` establish policy and role before conversation
- **AND THEN** startup sends no policy or role bootstrap prompt

#### Scenario: A user selects a mode for a resumed TUI
- **WHEN** a Kimi TUI relaunch resumes its saved session with a supported explicit permission mode
- **THEN** that mode takes effect at native startup
- **AND THEN** Houmao sends no policy-changing conversation input to establish it

#### Scenario: Avoidable confirmation fails unattended validation
- **WHEN** a Kimi TUI using the unattended default presents a confirmation or question that a supported startup setting can suppress
- **THEN** validation reports the unattended compatibility failure
- **AND THEN** the harness preserves the native intervention as evidence

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

### Requirement: Kimi unattended TUI startup pre-seeds workspace trust

Maintained Kimi 0.34.0-or-later unattended TUI startup SHALL suppress the provider's workspace-trust confirmation modal by pre-seeding the provider-native trust record for the launch working directory into the managed home before provider start. Houmao SHALL NOT answer the modal conversationally or by simulated keystroke as its suppression mechanism.

#### Scenario: Fresh unattended TUI shows no trust confirmation
- **WHEN** Houmao launches a fresh maintained Kimi TUI with unattended prompt mode and a managed home that has no prior trust state for the working directory
- **THEN** the trust-confirmation modal never mounts during startup
- **AND THEN** the first operator-visible surface is the ready TUI, not a confirmation dialog

#### Scenario: Recorded unattended corpus contains no trust intervention
- **WHEN** a maintained unattended Kimi TUI scenario is recorded for qualification
- **THEN** its labeled timeline contains no trust-confirmation intervention for the launch working directory
- **AND THEN** any residual provider confirmation surface is reported as an explicit exception with evidence

### Requirement: Maintained Kimi Code TUI launches with native role instructions
Kimi Code >=2.1.1 SHALL run as a maintained tmux-backed `local_interactive` TUI with no upper version limit. Launch SHALL project native `SYSTEM.md` role instructions before provider start, enforce the v2 engine, and set `KIMI_CODE_NO_AUTO_UPDATE=1`. It SHALL preserve shared TUI/runtime/gateway contracts, remain distinct from `kimi_headless`, and send no role-bootstrap turn.

#### Scenario: Kimi local interactive launch starts with native role instructions
- **WHEN** an operator launches a managed Kimi 2.1.1-or-later agent with local-interactive posture and a non-empty role prompt
- **THEN** the runtime starts the interactive Kimi Code TUI in the managed tmux primary surface after `SYSTEM.md` projection succeeds
- **AND THEN** the first conversational input is not a role bootstrap message

#### Scenario: Kimi headless remains separate
- **WHEN** an operator launches a managed Kimi agent with headless posture
- **THEN** the runtime uses backend `kimi_headless`
- **AND THEN** the launch does not inherit Kimi TUI parser, prompt-submission, or relaunch assumptions solely because both modes use the same provider CLI

#### Scenario: Kimi TUI launch suppresses update preflight and legacy mode
- **WHEN** Houmao starts a managed Kimi Code local-interactive session
- **THEN** the launched process environment includes `KIMI_CODE_NO_AUTO_UPDATE=1`
- **AND THEN** the process cannot select the legacy engine for this managed launch

#### Scenario: Kimi TUI retains the shared managed runtime contract
- **WHEN** a maintained Kimi local-interactive agent starts
- **THEN** its launch preserves the tmux primary surface, managed runtime home, launch-profile environment, gateway attachability, and managed-agent metadata publication
- **AND THEN** its tool identity remains `kimi`

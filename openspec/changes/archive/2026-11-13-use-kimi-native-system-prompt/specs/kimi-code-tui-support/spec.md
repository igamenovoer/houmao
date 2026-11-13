## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: Kimi unattended TUI startup establishes policy without a conversational turn
Maintained Kimi 2.1.1-or-later unattended TUI startup SHALL use native `--auto` after native role-prompt projection and before workload submission. Houmao SHALL NOT submit `/auto on`, a role bootstrap, an answered confirmation, or another conversational command to establish launch policy or role identity.

Normal unattended startup and work SHALL not enter approval, waiting-for-answer, or confirmation states. If Kimi hard-codes an intervention that no supported setting can suppress, Houmao SHALL retain evidence and report it as an explicit exception rather than silently answering it.

#### Scenario: Fresh unattended Kimi starts without policy or role chat
- **WHEN** Houmao launches a fresh maintained Kimi 2.1.1-or-later TUI with unattended prompt mode
- **THEN** the final launch command includes `--auto` and the managed native prompt is already projected
- **AND THEN** the first managed conversational input is workload content

#### Scenario: Fresh unattended Kimi starts prompt-free
- **WHEN** Houmao launches a fresh maintained Kimi TUI with unattended prompt mode
- **THEN** native `--auto` and native `SYSTEM.md` projection establish policy and role before conversation
- **AND THEN** startup sends no policy or role bootstrap prompt

#### Scenario: Avoidable confirmation fails unattended validation
- **WHEN** a normal unattended Kimi scenario displays a confirmation or user-question surface
- **AND WHEN** current source or CLI settings provide a supported suppression mechanism
- **THEN** validation fails the unattended contract
- **AND THEN** the harness does not answer the prompt automatically

## REMOVED Requirements

### Requirement: Kimi Code TUI launches as a maintained local interactive provider
**Reason**: The prior contract required bootstrap-message role injection and did not express the Kimi 2.1.1 minimum, no-upper-limit native prompt, or v2-engine boundary.

**Migration**: Rebuild and relaunch with Kimi 2.1.1 or later so the replacement native-role-instruction contract applies.

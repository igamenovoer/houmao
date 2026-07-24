## MODIFIED Requirements

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

## ADDED Requirements

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


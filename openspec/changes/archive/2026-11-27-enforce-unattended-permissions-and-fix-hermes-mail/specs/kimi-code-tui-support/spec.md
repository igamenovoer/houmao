# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi Code TUI relaunch supports provider-native session selection
For Kimi Code `local_interactive` sessions, runtime relaunch SHALL translate the shared relaunch chat-session selector into Kimi startup arguments before respawning the provider process in tmux window `0`.

The Kimi TUI relaunch translation SHALL be:

- `new`: no Kimi session-selection arguments
- `tool_last_or_new`: `kimi --continue`
- `exact`: `kimi --session <session_id>`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

An exact Kimi relaunch selector SHALL require a non-empty provider-native session id. The runtime SHALL NOT use bare `kimi --session` because that starts Kimi's interactive session picker.

For maintained Kimi 2.1.1 or later, unattended relaunch SHALL combine strategy-owned `--auto` with `--continue` or `--session <session_id>`. The runtime SHALL reject an incompatible winning authored permission value before provider start. The final unattended command SHALL contain a single native `--auto` and any selected resume argument. Kimi TUI relaunch SHALL continue to permit launch-owned `--model <alias>` arguments with resume selectors and SHALL validate the native `SYSTEM.md` contract before respawn.

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
- **WHEN** the winning authored permission setting for an unattended relaunch resolves to `--yolo`
- **THEN** Houmao reports the conflict before provider-start mutation
- **AND THEN** a valid relaunch with the same resume selector continues to use strategy-owned `--auto`

#### Scenario: Kimi TUI relaunch keeps model selection
- **WHEN** an unattended exact relaunch selects model `kimi-code/kimi-for-coding` and session `session_abc`
- **THEN** the final command contains `--model kimi-code/kimi-for-coding --auto --session session_abc`

### Requirement: Kimi unattended TUI startup establishes policy without a conversational turn

Maintained Kimi 2.1.1-or-later TUI startup SHALL apply the resolved native permission mode after role projection and before managed input. Houmao SHALL use `--auto` for unattended startup and reject an effective authored mode other than `auto`. Under `as_is`, Houmao SHALL apply a supported authored mode through a qualified native startup surface and preserve native behavior for omitted settings. Launch SHALL establish policy and role outside the conversation.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Under unattended policy, normal startup and work SHALL proceed without operator approval, answers, or confirmations. Native hard denials and explicit deny rules still apply. If a provider-required intervention remains, Houmao SHALL preserve the evidence and report the intervention.

#### Scenario: Fresh unattended Kimi starts without policy or role chat
- **WHEN** Houmao launches a fresh maintained Kimi TUI in unattended mode with an omitted or matching effective permission setting
- **THEN** the final launch command includes native `--auto` and the managed native prompt is already projected
- **AND THEN** the first managed conversational input is workload content

#### Scenario: Fresh unattended Kimi starts prompt-free
- **WHEN** Houmao starts a fresh maintained Kimi TUI with unattended `auto`
- **THEN** native `--auto` and native `SYSTEM.md` establish policy and role before conversation
- **AND THEN** startup sends no policy or role bootstrap prompt

#### Scenario: A user selects a mode for a resumed TUI
- **WHEN** an `as_is` Kimi TUI relaunch resumes its saved session with a supported explicit permission mode
- **THEN** that mode takes effect at native startup
- **AND THEN** Houmao sends no policy-changing conversation input to establish it

#### Scenario: Avoidable confirmation fails unattended validation
- **WHEN** a Kimi TUI under unattended policy presents a confirmation or question that a supported startup setting can suppress
- **THEN** validation reports the unattended compatibility failure
- **AND THEN** the harness preserves the native intervention as evidence

#### Scenario: Unattended startup rejects an authored manual mode

- **WHEN** the effective permission setting for unattended Kimi TUI startup is `manual`
- **THEN** Houmao reports the conflict and directs the operator to supported `as_is` settings
- **AND THEN** the provider home and runtime are untouched by provider-start actions

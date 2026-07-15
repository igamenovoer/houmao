## MODIFIED Requirements

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that maintained Kimi Code 0.23.x local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

The reference SHALL explain that unattended Kimi TUI startup uses native `--auto` before managed prompts are submitted and that current Kimi accepts this flag with `--continue` and `--session <session_id>`. It SHALL state that Houmao does not refresh auto mode through a chat command.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch and SHALL describe current source evidence for Kimi's system-prompt limitations without retaining a stale 0.11 version claim.

#### Scenario: Reader sees Kimi TUI unattended behavior
- **WHEN** a reader opens the Kimi local-interactive backend reference
- **THEN** it states that unattended startup includes native `--auto`
- **AND THEN** it states that the mode applies before role bootstrap or workload prompts

#### Scenario: Reader sees Kimi resumed startup behavior
- **WHEN** a reader opens the Kimi relaunch reference
- **THEN** it shows native `--auto` combined with `--continue` or `--session <session_id>`
- **AND THEN** it describes no post-readiness `/auto on` command

#### Scenario: Reader can distinguish as-is from unattended
- **WHEN** a reader compares Kimi launch prompt modes
- **THEN** `as_is` preserves provider approval behavior
- **AND THEN** `unattended` is the maintained no-question mode

#### Scenario: Reader sees current Kimi system-prompt evidence
- **WHEN** a reader opens the Kimi role-injection reference
- **THEN** the documentation describes the maintained Kimi 0.23.x system-prompt integration from current source evidence
- **AND THEN** it does not present Kimi 0.11.0 as the maintained version


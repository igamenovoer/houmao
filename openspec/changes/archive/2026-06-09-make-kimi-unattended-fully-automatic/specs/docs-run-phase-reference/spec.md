## ADDED Requirements

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that Kimi Code local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

The reference SHALL explain that unattended Kimi TUI startup enters Kimi auto permission mode before managed prompts are submitted.

The reference SHALL explain that resumed Kimi TUI startup cannot combine Kimi native resume selectors with `--auto`, so Houmao preserves Kimi resume arguments and refreshes auto mode after TUI readiness.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch.

#### Scenario: Reader sees Kimi TUI unattended behavior
- **WHEN** a reader opens the run-phase backend reference for Kimi Code local-interactive launch
- **THEN** it states that unattended Kimi TUI launch runs in Kimi auto permission mode
- **AND THEN** it states that Houmao applies that mode before role bootstrap or workload prompts

#### Scenario: Reader sees Kimi resumed startup constraint
- **WHEN** a reader opens the run-phase relaunch reference for Kimi Code local-interactive launch
- **THEN** it explains that `--continue` and `--session <session_id>` cannot be combined with `--auto`
- **AND THEN** it explains that Houmao refreshes auto mode after TUI readiness for unattended resumed sessions

#### Scenario: Reader can distinguish as-is from unattended
- **WHEN** a reader compares Kimi launch prompt modes in run-phase documentation
- **THEN** `as_is` is described as preserving provider approval behavior
- **AND THEN** `unattended` is described as the maintained no-question mode

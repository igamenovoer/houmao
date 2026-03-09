# cao-interactive-demo-inspect-surface Specification

## Purpose
TBD - created by archiving change improve-cao-interactive-demo-inspect-output. Update Purpose after archive.
## Requirements
### Requirement: Interactive demo inspect SHALL present an operator-oriented session summary
When a developer runs `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect` without `--json`, the interactive demo SHALL render a human-readable inspection surface that makes the current session state, the main operator commands, and the important artifact locations easy to identify.

The human-readable surface SHALL include at minimum:
- whether the recorded session is active,
- the persisted canonical agent identity,
- the current Claude Code state,
- the tmux attach command,
- the terminal log tail command,
- the terminal identifier,
- the session manifest path,
- the workspace root,
- the runtime root, and
- the last-updated timestamp.

#### Scenario: Human-readable inspect highlights the next operator actions
- **WHEN** a developer runs `run_demo.sh inspect` after launching the interactive demo
- **THEN** the output includes a clearly identifiable tmux attach command and terminal-log tail command
- **AND THEN** the output also includes the current session status, Claude Code state, and artifact locations needed for debugging

### Requirement: Interactive demo inspect SHALL surface live Claude Code state when available
The interactive demo SHALL attempt to resolve the current Claude Code state from the CAO terminal identified by the persisted `terminal_id`.

When the CAO status lookup succeeds, `inspect` SHALL expose that state in both the human-readable and JSON surfaces as `claude_code_state`.

The surfaced state SHALL use the CAO terminal status values returned by the live terminal lookup, including at minimum `idle`, `processing`, `completed`, `waiting_user_answer`, and `error`.

If the live CAO terminal-status lookup cannot be completed, `inspect` SHALL still render the persisted demo metadata and SHALL use `claude_code_state = unknown` rather than failing the entire inspect command.

#### Scenario: Live CAO terminal status appears in inspect
- **WHEN** a developer runs `inspect` while the interactive CAO terminal still exists and the CAO server is reachable
- **THEN** the output includes `claude_code_state` with the live CAO terminal status for that terminal
- **AND THEN** the command continues to include the normal tmux/log/artifact details

#### Scenario: Inspect tolerates missing live state
- **WHEN** a developer runs `inspect` after the CAO server is unavailable or the terminal can no longer be queried
- **THEN** the command still prints the persisted demo inspection metadata
- **AND THEN** the surfaced `claude_code_state` is `unknown`

### Requirement: Interactive demo inspect SHALL optionally include a clean output-text tail
The interactive demo `inspect` command SHALL accept `--with-output-text <num-tail-chars>` as an optional argument.

`<num-tail-chars>` SHALL be a positive integer specifying how many characters of clean projected Claude dialog text to include from the tail of the current live TUI snapshot.

When this option is present, the demo SHALL fetch live CAO terminal output using `output?mode=full`, project that scrollback into clean dialog text using the runtime-owned Claude dialog-projection path, and include the last `<num-tail-chars>` characters of that projected dialog text in the inspect result as `output_text_tail`.

The reported `output_text_tail` SHALL come from clean projected dialog text and SHALL NOT fall back to raw ANSI/tmux scrollback.

#### Scenario: Inspect returns the requested clean dialog tail
- **WHEN** a developer runs `inspect --with-output-text 500` while the live Claude terminal is reachable
- **THEN** the output includes `output_text_tail` derived from the current clean projected Claude dialog text
- **AND THEN** the returned string contains at most 500 characters from the end of that projected dialog text
- **AND THEN** the command continues to include the normal session, state, tmux, and log metadata

#### Scenario: Short projected dialog returns the full clean text
- **WHEN** a developer runs `inspect --with-output-text 500` and the current projected dialog text is shorter than 500 characters
- **THEN** `output_text_tail` contains the full projected dialog text
- **AND THEN** the command does not pad, truncate incorrectly, or include raw scrollback chrome

#### Scenario: Inspect reports output-tail unavailability without using raw scrollback
- **WHEN** a developer runs `inspect --with-output-text 500` and live output fetch or clean projection cannot be completed
- **THEN** the command still prints the base inspection metadata
- **AND THEN** it includes an explicit note that the clean output-text tail is unavailable
- **AND THEN** it does not substitute raw `mode=full` or terminal-log content in place of clean projected dialog text

### Requirement: Interactive demo inspect SHALL resolve terminal-log paths from the effective CAO home
The interactive demo SHALL derive `terminal_log_path` from the effective CAO home configured for the demo run instead of assuming the operator's real login home directory.

For the default per-run startup layout, `terminal_log_path` SHALL point to `<run-root>/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log`.

When the operator overrides the launcher-home path, `terminal_log_path` SHALL point to `<launcher-home>/.aws/cli-agent-orchestrator/logs/terminal/<terminal_id>.log`.

#### Scenario: Default startup reports the run-root terminal log file
- **WHEN** a developer launches the interactive demo with default startup paths and then runs `inspect`
- **THEN** the reported `terminal_log_path` and tail command point into that run's workspace-root `.aws/cli-agent-orchestrator/logs/terminal/` directory
- **AND THEN** the path ends with the recorded `terminal_id` plus `.log`

#### Scenario: Explicit launcher-home override controls the reported log path
- **WHEN** a developer launches the interactive demo with an explicit launcher-home override and then runs `inspect` or `verify`
- **THEN** the reported `terminal_log_path` points under that override path's `.aws/cli-agent-orchestrator/logs/terminal/` directory
- **AND THEN** the demo does not fall back to a hard-coded `~/.aws/cli-agent-orchestrator/logs/terminal/` prefix

### Requirement: Interactive demo verification artifacts SHALL preserve the resolved inspect contract
The interactive demo verification flow SHALL record the same resolved `terminal_log_path` contract exposed by `inspect`, and the report verification helper SHALL validate that resolved-path behavior rather than the legacy `~/.aws/...` placeholder pattern.

#### Scenario: Verification report records the resolved terminal log path
- **WHEN** a developer runs `run_demo.sh verify` after the minimum required interactive turns
- **THEN** `report.json` includes `terminal_id` and a `terminal_log_path` that matches the effective CAO home for that run
- **AND THEN** the verification helper accepts the report without requiring a user-home `~/.aws/...` path


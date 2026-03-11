## MODIFIED Requirements

### Requirement: Interactive demo inspect JSON SHALL expose a stable top-level contract
When a developer runs `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect --json`, the command SHALL emit a stable top-level JSON object describing the current persisted session plus any requested live output-tail data.

The JSON output SHALL include at minimum:
- `active`
- `session_status`
- `agent_identity`
- `session_name`
- `tool`
- `variant_id`
- `brain_recipe`
- `tool_state`
- `session_manifest`
- `tmux_target`
- `tmux_attach_command`
- `terminal_id`
- `terminal_log_path`
- `terminal_log_tail_command`
- `workspace_dir`
- `runtime_root`
- `updated_at`

When `--with-output-text <num-tail-chars>` is requested, the JSON output SHALL additionally include:
- `output_text_tail_chars_requested`
- `output_text_tail`

If the clean projected dialog tail cannot be produced, the JSON output SHALL include:
- `output_text_tail_note`

#### Scenario: Inspect JSON returns the stable field set for the selected variant
- **WHEN** a developer runs `run_demo.sh inspect --json` after launching the interactive demo
- **THEN** the JSON payload includes the stable top-level fields for session state, selected tool and variant, log/tmux commands, and artifact locations
- **AND THEN** the payload uses `tool_state` instead of `claude_code_state`

### Requirement: Interactive demo inspect SHALL present an operator-oriented session summary
When a developer runs `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect` without `--json`, the interactive demo SHALL render a human-readable inspection surface that makes the current session state, the selected demo variant, the main operator commands, and the important artifact locations easy to identify.

The human-readable surface SHALL include at minimum:
- whether the recorded session is active,
- the persisted canonical agent identity,
- the selected `tool`,
- the selected `variant_id`,
- the current `tool_state`,
- the tmux attach command,
- the terminal log tail command,
- the terminal identifier,
- the session manifest path,
- the workspace root,
- the runtime root, and
- the last-updated timestamp.

#### Scenario: Human-readable inspect highlights the next operator actions for the selected variant
- **WHEN** a developer runs `run_demo.sh inspect` after launching the interactive demo
- **THEN** the output includes a clearly identifiable tmux attach command and terminal-log tail command
- **AND THEN** the output includes the current session status, selected tool and variant, live tool state, and artifact locations needed for debugging

### Requirement: Interactive demo inspect SHALL optionally include a clean output-text tail
The interactive demo `inspect` command SHALL accept `--with-output-text <num-tail-chars>` as an optional argument.

`<num-tail-chars>` SHALL be a positive integer specifying how many characters of clean projected dialog text to include from the tail of the current live TUI snapshot for the persisted tool selection.

When this option is present, the demo SHALL fetch live CAO terminal output using `output?mode=full`, project that scrollback into clean dialog text using the runtime-owned parser stack for the persisted tool, and include the last `<num-tail-chars>` characters of that projected dialog text in the inspect result as `output_text_tail`.

The reported `output_text_tail` SHALL come from clean projected dialog text and SHALL NOT fall back to raw ANSI or tmux scrollback.

#### Scenario: Inspect returns the requested clean dialog tail for the selected tool
- **WHEN** a developer runs `inspect --with-output-text 500` while the live Claude or Codex terminal is reachable
- **THEN** the output includes `output_text_tail` derived from the current clean projected dialog text for that tool
- **AND THEN** the returned string contains at most 500 characters from the end of that projected dialog text
- **AND THEN** the command continues to include the normal session, variant, tmux, and log metadata

#### Scenario: Short projected dialog returns the full clean text
- **WHEN** a developer runs `inspect --with-output-text 500` and the current projected dialog text is shorter than 500 characters
- **THEN** `output_text_tail` contains the full projected dialog text
- **AND THEN** the command does not pad, truncate incorrectly, or include raw scrollback chrome

#### Scenario: Inspect reports output-tail unavailability without using raw scrollback
- **WHEN** a developer runs `inspect --with-output-text 500` and live output fetch or clean projection cannot be completed
- **THEN** the command still prints the base inspection metadata
- **AND THEN** it includes an explicit note that the clean output-text tail is unavailable
- **AND THEN** it does not substitute raw `mode=full` or terminal-log content in place of clean projected dialog text

## REMOVED Requirements

### Requirement: Interactive demo inspect SHALL surface live Claude Code state when available
**Reason**: The inspect surface now needs one tool-agnostic live-state field that works for both Claude and Codex sessions.
**Migration**: Use `tool_state` in inspect JSON and human-readable output instead of `claude_code_state`.

## ADDED Requirements

### Requirement: Interactive demo inspect SHALL surface live tool state when available
The interactive demo SHALL attempt to resolve the current tool state from the CAO terminal identified by the persisted `terminal_id`.

When the CAO status lookup succeeds, `inspect` SHALL expose that state in both the human-readable and JSON surfaces as `tool_state`.

The surfaced state SHALL use the CAO terminal status values returned by the live terminal lookup, including at minimum `idle`, `processing`, `completed`, `waiting_user_answer`, and `error`.

If the live CAO terminal-status lookup cannot be completed, `inspect` SHALL still render the persisted demo metadata and SHALL use `tool_state = unknown` rather than failing the entire inspect command.

#### Scenario: Live CAO terminal status appears in inspect for the selected tool
- **WHEN** a developer runs `inspect` while the interactive CAO terminal still exists and the CAO server is reachable
- **THEN** the output includes `tool_state` with the live CAO terminal status for that terminal
- **AND THEN** the command continues to include the normal tool, variant, tmux, log, and artifact details

#### Scenario: Inspect tolerates missing live state
- **WHEN** a developer runs `inspect` after the CAO server is unavailable or the terminal can no longer be queried
- **THEN** the command still prints the persisted demo inspection metadata
- **AND THEN** the surfaced `tool_state` is `unknown`

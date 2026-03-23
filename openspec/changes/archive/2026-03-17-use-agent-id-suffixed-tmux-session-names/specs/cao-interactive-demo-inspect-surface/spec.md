## MODIFIED Requirements

### Requirement: Interactive demo inspect JSON SHALL expose a stable top-level contract
The interactive demo inspect `--json` command SHALL emit a stable top-level JSON object describing the current persisted session plus any requested live output-tail data.

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

When `--with-output-text <num-tail-chars>` is requested, the JSON output SHALL
additionally include:
- `output_text_tail_chars_requested`
- `output_text_tail`

If the clean projected dialog tail cannot be produced, the JSON output SHALL
include:
- `output_text_tail_note`

For tmux-backed demo sessions whose live tmux handle differs from the canonical
agent identity, the inspect JSON SHALL preserve that distinction:

- `agent_identity` SHALL remain the canonical `AGENTSYS-<name>` identity
- `session_name` SHALL reflect the actual persisted runtime session name
- `tmux_target` SHALL reflect the actual tmux attach target
- `tmux_attach_command` SHALL target `tmux_target`

#### Scenario: Inspect JSON returns the stable field set for the selected variant
- **WHEN** a developer runs `run_demo.sh inspect --json` after launching the interactive demo
- **THEN** the JSON payload includes the stable top-level fields for session state, selected tool and variant, log/tmux commands, and artifact locations
- **AND THEN** the payload uses `tool_state` instead of `claude_code_state`

#### Scenario: Inspect JSON distinguishes canonical identity from tmux handle
- **WHEN** a developer runs `run_demo.sh inspect --json` for a live session with canonical agent identity `AGENTSYS-alice`
- **AND WHEN** the persisted tmux handle is `AGENTSYS-alice-270b87`
- **THEN** the JSON payload includes `agent_identity="AGENTSYS-alice"`
- **AND THEN** it includes `tmux_target="AGENTSYS-alice-270b87"`
- **AND THEN** `tmux_attach_command` is `tmux attach -t AGENTSYS-alice-270b87`

### Requirement: Interactive demo inspect SHALL present an operator-oriented session summary
The interactive demo inspect command SHALL render a human-readable inspection surface for `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect` that makes the current session state, the selected demo variant, the main operator commands, and the important artifact locations easy to identify.

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

When the live tmux handle differs from the canonical agent identity, the human-readable surface SHALL show the actual tmux attach command while still surfacing the canonical agent identity separately.

#### Scenario: Human-readable inspect highlights the next operator actions
- **WHEN** a developer runs `run_demo.sh inspect` after launching the interactive demo
- **THEN** the output includes a clearly identifiable tmux attach command and terminal-log tail command
- **AND THEN** the output includes the current session status, selected tool and variant, live tool state, and artifact locations needed for debugging

#### Scenario: Human-readable inspect uses the actual tmux attach target
- **WHEN** a developer runs `run_demo.sh inspect` for a live session with canonical agent identity `AGENTSYS-alice`
- **AND WHEN** the persisted tmux handle is `AGENTSYS-alice-270b87`
- **THEN** the output surfaces `agent_identity: AGENTSYS-alice`
- **AND THEN** it surfaces `tmux_attach: tmux attach -t AGENTSYS-alice-270b87`

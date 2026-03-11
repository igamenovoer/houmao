# cao-interactive-full-pipeline-demo Specification

## Purpose
TBD - created by archiving change add-interactive-cao-full-pipeline-demo. Update Purpose after archive.
## Requirements
### Requirement: Interactive demo session startup
The demo workflow SHALL provide a startup command that builds a Claude CAO runtime context, starts a `cao_rest` session with a role prompt, and writes a state artifact containing the name-based session identity and inspection metadata.

#### Scenario: Startup succeeds with fixed local prerequisites
- **WHEN** the user runs the interactive startup command with valid local CAO availability and credentials
- **THEN** the command targets `http://127.0.0.1:9889`
- **AND** the command starts the session with an explicit name-based `--agent-identity`
- **AND** the command produces a state artifact containing `agent_identity`, `session_manifest`, `session_name`, `tmux_target`, `terminal_id`, `terminal_log_path`, and `workspace_dir`
- **AND** the command exits without calling `stop-session`

#### Scenario: Startup fails safely when prerequisites are missing
- **WHEN** required runtime prerequisites (for example tmux, credentials, or CAO connectivity) are unavailable
- **THEN** the command exits with an explicit reason and does not create a partial interactive state marked as active

#### Scenario: Startup replaces a previously active demo session
- **WHEN** the user runs the interactive startup command while the state artifact already marks another demo session active
- **THEN** the command first attempts `brain_launch_runtime stop-session` for the recorded `agent_identity`
- **AND** the command starts a replacement session
- **AND** the state artifact is rewritten to the new `agent_identity` and metadata

### Requirement: Multi-turn prompt driving against a live session
The demo workflow SHALL provide a turn-driving command that reads the persisted state artifact and sends a prompt through `brain_launch_runtime send-prompt` to the same active session by name-based `agent_identity`.

Operator interaction between automated turns MAY include manual slash commands or manual model switching inside the live session. Once the visible provider surface has returned to its normal prompt, the demo SHALL continue to treat that session as reusable for subsequent `send-turn` operations.

#### Scenario: Sequential prompts use one session identity
- **WHEN** the user runs the turn-driving command multiple times after a successful startup
- **THEN** each turn targets the same `agent_identity` recorded by startup
- **AND** each turn records a non-empty response in per-turn output artifacts along with the `agent_identity` used for that turn

#### Scenario: Follow-up send-turn still works after a recovered slash-command or model switch
- **WHEN** the operator uses a slash command or manual model switch inside the active interactive session between automated turns
- **AND WHEN** the live provider surface has already returned to its normal prompt before the next `send-turn`
- **THEN** the next `send-turn` reuses the same persisted `agent_identity`
- **AND THEN** it submits the prompt and records a normal turn artifact instead of hanging in readiness gating

#### Scenario: Turn-driving rejects missing or inactive session state
- **WHEN** the user runs the turn-driving command before startup or after stop
- **THEN** the command fails with a clear actionable message indicating that no active interactive session exists

### Requirement: Fixed local CAO target
The demo workflow SHALL use the fixed CAO base URL `http://127.0.0.1:9889` for startup and SHALL NOT depend on alternate CAO base URL inputs.

#### Scenario: Operator attempts to provide another CAO base URL
- **WHEN** the operator supplies a non-default CAO base URL input or environment override
- **THEN** the demo continues to use `http://127.0.0.1:9889`
- **AND** the effective startup metadata reflects the fixed loopback target

### Requirement: Live inspection affordances
The demo workflow SHALL expose enough metadata for live tmux and log inspection while the session remains active.

#### Scenario: User can attach and observe
- **WHEN** startup completes
- **THEN** the workflow outputs or stores a tmux attach target derived from session metadata
- **AND** the workflow outputs or stores a terminal log path suitable for tailing CAO output

### Requirement: Explicit interactive teardown
The demo workflow SHALL provide an explicit stop command that terminates the active interactive session and marks the state as no longer active.

#### Scenario: Stop cleans up active session
- **WHEN** the user runs the stop command with an active state artifact
- **THEN** the command calls `brain_launch_runtime stop-session` for the recorded `agent_identity`
- **AND** subsequent turn-driving attempts fail until startup is run again

#### Scenario: Stop is safe when session is already gone
- **WHEN** the recorded session no longer exists remotely
- **THEN** the command exits gracefully and updates local state to inactive

### Requirement: Live control-input driving against an active session
The demo workflow SHALL provide a `send-keys` command that reads the persisted state artifact and sends a raw control-input sequence through `brain_launch_runtime send-keys` to the same active session by name-based `agent_identity`.

The operator-facing control-input workflow SHALL require one positional key-stream input, and it SHALL forward the runtime-owned `send-keys` contract without appending implicit submit behavior.

#### Scenario: Control input targets the active persisted session
- **WHEN** the user runs the control-input command after a successful startup
- **THEN** the command targets the same `agent_identity` recorded in the active state artifact
- **AND** it sends the requested sequence through `brain_launch_runtime send-keys`

#### Scenario: Control input rejects missing or inactive session state
- **WHEN** the user runs the control-input command before startup or after stop
- **THEN** the command fails with a clear actionable message indicating that no active interactive session exists

#### Scenario: Control input forwards the runtime sequence contract
- **WHEN** the user runs the control-input command with a required positional key stream
- **THEN** the demo forwards the provided sequence to the runtime `send-keys` path without reinterpreting the runtime's mixed text or special-key grammar
- **AND** it does not add an implicit trailing `Enter`

#### Scenario: Control input can request raw-string mode
- **WHEN** the user runs the control-input command with `--as-raw-string`
- **THEN** the demo forwards that flag to the runtime `send-keys` path
- **AND** token-like substrings are treated according to the runtime's raw-string mode

### Requirement: Control-input artifacts remain distinct from prompt-turn verification
The demo workflow SHALL persist control-input artifacts separately from prompt-turn artifacts and SHALL NOT count control-input actions as prompt turns for verification.

#### Scenario: Control input writes separate artifacts
- **WHEN** the user runs the control-input command
- **THEN** the demo writes a structured control-input record plus captured stdout and stderr logs under a dedicated artifact family separate from `turns/`
- **AND** existing prompt-turn artifacts remain unchanged

#### Scenario: Verification remains prompt-turn-only after control input
- **WHEN** the user runs one or more control-input actions between prompt turns and later runs `verify`
- **THEN** the generated verification report is derived only from recorded prompt-turn artifacts
- **AND** it does not require or count control-input artifacts as turns

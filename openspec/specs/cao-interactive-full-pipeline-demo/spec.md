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

## ADDED Requirements

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

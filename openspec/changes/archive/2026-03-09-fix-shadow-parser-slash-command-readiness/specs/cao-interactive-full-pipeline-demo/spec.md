## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Runtime log cleanup handles gateway diagnostic log files
`houmao-mgr admin cleanup runtime logs` and `houmao-mgr agents cleanup logs` SHALL classify gateway diagnostic log files under the gateway-owned log directory as cleanup-sensitive runtime log artifacts.

Runtime log cleanup SHALL preserve durable gateway artifacts such as `manifest.json`, `gateway/queue.sqlite`, `gateway/events.jsonl`, and `gateway/state.json` when removing gateway diagnostic log files.

Runtime log cleanup SHALL apply the same live-session safety posture to gateway diagnostic log files as it applies to other gateway log output.

#### Scenario: Stopped-session log cleanup removes diagnostic logs but preserves durable gateway state
- **WHEN** an operator runs a supported runtime log cleanup command for a stopped session with gateway diagnostic log files
- **THEN** the command may remove those diagnostic log files as runtime log artifacts
- **AND THEN** it preserves durable gateway artifacts such as `queue.sqlite`, `events.jsonl`, `state.json`, and `manifest.json`

#### Scenario: Active-session log cleanup follows existing live safeguards
- **WHEN** an operator runs a supported runtime log cleanup command for an active session with gateway diagnostic log files
- **THEN** the command applies the existing live-session safety checks before removing cleanup-sensitive gateway log artifacts
- **AND THEN** the command does not retire or purge the active registry record merely because diagnostic log files were selected for cleanup

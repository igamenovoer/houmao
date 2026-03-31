## MODIFIED Requirements

### Requirement: Pair-owned gateway attach for managed `houmao_server_rest` sessions supports explicit and current-session targeting
When called through the current-session contract, the command SHALL require execution inside the target agent's tmux session, SHALL discover the current tmux session as the attach context, SHALL prefer `HOUMAO_MANIFEST_PATH` from that tmux session when present and valid, and SHALL otherwise use `HOUMAO_AGENT_ID` from that same tmux session to resolve exactly one fresh shared-registry record and `runtime.manifest_path`.

Current-session attach SHALL NOT fall back to retired `AGENTSYS_*` names. It SHALL also NOT fall back to `HOUMAO_GATEWAY_ATTACH_PATH`, `HOUMAO_GATEWAY_ROOT`, `terminal_id`, cwd, ambient shell env, or another server target when manifest or shared-registry discovery is invalid or stale.

#### Scenario: Current-session attach prefers HOUMAO manifest pointer
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from the owning tmux session
- **AND WHEN** that tmux session publishes a valid `HOUMAO_MANIFEST_PATH`
- **THEN** the attach flow resolves authority from that manifest pointer

#### Scenario: Current-session attach falls back to HOUMAO agent id through the shared registry
- **WHEN** a developer runs `houmao-mgr agents gateway attach` from a tmux session whose `HOUMAO_MANIFEST_PATH` is unusable
- **AND WHEN** the tmux session publishes `HOUMAO_AGENT_ID`
- **THEN** the attach flow resolves authority through exactly one fresh shared-registry record

### Requirement: Native headless gateway attach supports tmux current-session targeting without requiring a live worker process
For native headless tmux-backed sessions, the system SHALL allow gateway attach from inside the owning tmux session using manifest-first discovery from `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`.

#### Scenario: Native headless attach accepts HOUMAO current-session discovery
- **WHEN** a developer runs gateway attach from inside the owning native headless tmux session
- **AND WHEN** that session publishes a valid `HOUMAO_MANIFEST_PATH`
- **THEN** the system resolves the target from `HOUMAO_MANIFEST_PATH`


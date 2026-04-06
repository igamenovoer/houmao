## ADDED Requirements

### Requirement: Gateway tmux-session selectors resolve through fresh registry tmux aliases
When `houmao-mgr agents gateway ...` resolves `--target-tmux-session <tmux-session-name>` through local registry-backed discovery, the system SHALL match that selector against fresh shared-registry `terminal.session_name` values.

That lookup SHALL require an exact tmux session name match. If exactly one fresh shared-registry record matches, the system SHALL resolve that record as the local managed-agent target.

If no fresh record matches, the lookup SHALL report that the tmux-session selector could not be resolved through the shared registry. If more than one fresh record matches, the command SHALL fail explicitly and SHALL surface enough identity metadata for the operator to disambiguate the target.

This tmux-session alias path SHALL remain local registry-backed discovery only and SHALL NOT redefine tmux session names as remote pair-managed agent identifiers.

#### Scenario: Gateway CLI resolves a managed agent by exact tmux session alias
- **WHEN** an operator runs `houmao-mgr agents gateway status --target-tmux-session HOUMAO-gpu-coder-1-1775467167530`
- **AND WHEN** exactly one fresh shared-registry record has `terminal.session_name = "HOUMAO-gpu-coder-1-1775467167530"`
- **THEN** the system resolves that record as the local managed-agent target
- **AND THEN** the operator does not need to rediscover the friendly `agent_name` or authoritative `agent_id` first

#### Scenario: Ambiguous tmux session alias lookup fails closed
- **WHEN** an operator runs `houmao-mgr agents gateway status --target-tmux-session hm-gateway-demo`
- **AND WHEN** more than one fresh shared-registry record matches that tmux session alias
- **THEN** the command fails that resolution explicitly
- **AND THEN** the error surfaces candidate `agent_id`, `agent_name`, and `terminal.session_name` values rather than silently choosing one

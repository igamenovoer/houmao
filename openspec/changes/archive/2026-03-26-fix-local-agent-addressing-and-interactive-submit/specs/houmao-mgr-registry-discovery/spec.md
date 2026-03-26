## ADDED Requirements

### Requirement: Local registry-first discovery resolves exact ids, unique names, and unique tmux aliases

For serverless local `houmao-mgr agents` post-launch commands that resolve a managed agent through the shared registry, the system SHALL support all of the following local target forms:

- exact authoritative `agent_id`
- unique friendly `agent_name`
- unique exact tmux session name from the live registry record's `terminal.session_name`

For the native CLI surface, the local registry-backed discovery path SHALL be driven by explicit selector flags rather than one positional managed-agent reference:

- `--agent-id <id>` performs exact authoritative-id lookup
- `--agent-name <name>` performs friendly-name lookup

The tmux-session alias path remains an additional local discovery capability for serverless tooling and current-session-adjacent workflows, but it SHALL NOT redefine tmux session names as managed-agent identity and SHALL NOT require pair-managed server APIs to learn tmux-local aliases.

When friendly-name lookup or tmux-session alias lookup matches more than one fresh live registry record, the command SHALL fail explicitly and SHALL surface enough identity metadata for the operator to disambiguate the target.

#### Scenario: Local command resolves a managed agent by exact authoritative id

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **AND WHEN** a fresh shared-registry record stores `agent_id = "abc123"`
- **THEN** `houmao-mgr` resolves that exact record as the local managed-agent target
- **AND THEN** the operator does not depend on friendly-name uniqueness for that control action

#### Scenario: Local command resolves a managed agent by unique friendly name

- **WHEN** an operator runs `houmao-mgr agents state --agent-name projection-demo-codex`
- **AND WHEN** exactly one fresh shared-registry record stores `agent_name = "projection-demo-codex"`
- **THEN** `houmao-mgr` resolves that record as the local managed-agent target
- **AND THEN** the operator can use the friendly name without needing the tmux session handle

#### Scenario: Ambiguous friendly-name lookup fails closed

- **WHEN** an operator runs `houmao-mgr agents show --agent-name gpu`
- **AND WHEN** more than one fresh shared-registry record stores `agent_name = "gpu"`
- **THEN** `houmao-mgr` fails that resolution explicitly
- **AND THEN** the error lists candidate `agent_id`, `agent_name`, and `terminal.session_name` values rather than silently choosing one

#### Scenario: Local tooling resolves a managed agent by tmux session alias

- **WHEN** local serverless tooling resolves the tmux session alias `hm-gw-track-codex`
- **AND WHEN** exactly one fresh shared-registry record has `terminal.session_name = "hm-gw-track-codex"`
- **THEN** the system resolves that record as the local managed-agent target
- **AND THEN** the tooling does not need to rediscover the friendly `agent_name` first

#### Scenario: Pair-managed explicit port bypass keeps server authority semantics

- **WHEN** an operator runs `houmao-mgr agents show --agent-id abc123 --port 9889`
- **THEN** `houmao-mgr` bypasses local registry resolution and contacts the server authority at port `9889`
- **AND THEN** the command does not rely on tmux-local alias semantics for that invocation

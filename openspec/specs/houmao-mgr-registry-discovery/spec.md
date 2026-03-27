## Purpose
Define registry-first managed-agent discovery and control for `houmao-mgr agents` commands.

## Requirements

### Requirement: Agent post-launch commands use registry-first discovery
`houmao-mgr agents` post-launch commands (prompt, stop, interrupt, show, state, history, and subgroup commands) SHALL resolve `<agent_ref>` by first looking up the agent in the shared registry before contacting a server.

The discovery chain SHALL be:
1. Look up `<agent_ref>` in the shared registry (`~/.houmao/registry/live_agents/`)
2. From the registry record, determine the backend type and control path
3. For `houmao_server_rest` backends: extract server URL from the manifest's backend state
4. For headless backends (`claude_headless`, `codex_headless`, `gemini_headless`): control directly via `RuntimeSessionController`
5. If registry lookup fails: fall back to `--port` flag, then `CAO_PORT` environment variable, then default server URL

#### Scenario: Post-launch command discovers agent via shared registry
- **WHEN** an operator runs `houmao-mgr agents show <agent_ref>`
- **AND WHEN** the agent has a live shared registry record
- **THEN** `houmao-mgr` resolves the agent's backend type and control path from the registry record
- **AND THEN** the command does not require an explicit `--port` flag

#### Scenario: Post-launch command falls back to port when registry lookup fails
- **WHEN** an operator runs `houmao-mgr agents show <agent_ref>`
- **AND WHEN** no shared registry record exists for that agent
- **THEN** `houmao-mgr` falls back to the `--port` flag, then `CAO_PORT` env var, then the default server URL
- **AND THEN** the command succeeds if the server is reachable and knows the agent

#### Scenario: Headless agent is controlled directly without a server
- **WHEN** an operator runs `houmao-mgr agents prompt <agent_ref> --prompt "..."`
- **AND WHEN** the shared registry record indicates a headless backend (e.g., `claude_headless`)
- **THEN** `houmao-mgr` loads the `RuntimeSessionController` from the manifest path in the registry record
- **AND THEN** the prompt is submitted directly without contacting `houmao-server`

### Requirement: `houmao-mgr agents list` aggregates from shared registry
`houmao-mgr agents list` SHALL read live agents from the shared registry as its primary data source.

When a `houmao-server` is reachable, the list MAY be enriched with server-managed agent state (e.g., TUI tracking status), but the registry SHALL be the primary source so that agents launched without a server are still visible.

#### Scenario: Agents list shows locally launched agents
- **WHEN** an operator runs `houmao-mgr agents list`
- **AND WHEN** agents were launched via `houmao-mgr agents launch` without a server
- **THEN** those agents appear in the list from the shared registry
- **AND THEN** the list does not require a running `houmao-server`

#### Scenario: Agents list enriches with server state when available
- **WHEN** an operator runs `houmao-mgr agents list`
- **AND WHEN** a `houmao-server` is running with additional managed agents
- **THEN** the list includes both registry-discovered agents and server-managed agents
- **AND THEN** duplicate entries are deduplicated by agent identity

### Requirement: `--port` flag remains as optional override
All `houmao-mgr agents` commands that currently accept `--port` SHALL continue to accept it as an optional override that bypasses registry-first discovery.

When `--port` is explicitly provided, the command SHALL contact the server at that port directly without attempting registry lookup first.

#### Scenario: Explicit port overrides registry discovery
- **WHEN** an operator runs `houmao-mgr agents show <agent_ref> --port 9889`
- **THEN** `houmao-mgr` contacts the server at port 9889 directly
- **AND THEN** registry lookup is skipped for this invocation

### Requirement: Local registry-first discovery resolves exact ids, unique names, and unique tmux aliases

For serverless local `houmao-mgr agents` post-launch commands that resolve a managed agent through the shared registry, the system SHALL support all of the following local target forms:

- exact authoritative `agent_id`
- unique friendly `agent_name`
- unique exact tmux session name from the live registry record's `terminal.session_name`

For the native CLI surface, the local registry-backed discovery path SHALL be driven by explicit selector flags rather than one positional managed-agent reference:

- `--agent-id <id>` performs exact authoritative-id lookup
- `--agent-name <name>` performs friendly-name lookup using the raw creation-time name supplied during managed-agent launch

For `--agent-name` targeting, operators SHALL provide the same raw friendly name they used at creation time. The system SHALL NOT require callers to use canonical `AGENTSYS-...` names on this selector surface.

When a caller provides an `--agent-name` value that begins with a case-sensitive or case-insensitive `AGENTSYS` namespace prefix plus separator, the command SHALL fail explicitly instead of silently normalizing or accepting that prefixed form as the user-facing selector.

The tmux-session alias path remains an additional local discovery capability for serverless tooling and current-session-adjacent workflows, but it SHALL NOT redefine tmux session names as managed-agent identity and SHALL NOT require pair-managed server APIs to learn tmux-local aliases.

When friendly-name lookup or tmux-session alias lookup matches more than one fresh live registry record, the command SHALL fail explicitly and SHALL surface enough identity metadata for the operator to disambiguate the target.

#### Scenario: Local command resolves a managed agent by exact authoritative id

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **AND WHEN** a fresh shared-registry record stores `agent_id = "abc123"`
- **THEN** `houmao-mgr` resolves that exact record as the local managed-agent target
- **AND THEN** the operator does not depend on friendly-name uniqueness for that control action

#### Scenario: Local command resolves a managed agent by raw friendly name

- **WHEN** an operator runs `houmao-mgr agents state --agent-name james`
- **AND WHEN** exactly one fresh shared-registry record stores `agent_name = "james"`
- **THEN** `houmao-mgr` resolves that record as the local managed-agent target
- **AND THEN** the operator uses the same raw name that was supplied during creation

#### Scenario: Prefixed canonical name is rejected on `--agent-name`

- **WHEN** an operator runs `houmao-mgr agents state --agent-name AGENTSYS-james`
- **THEN** `houmao-mgr` rejects that selector with an explicit unprefixed-agent-name error
- **AND THEN** the command does not silently normalize that value into a friendly-name lookup

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

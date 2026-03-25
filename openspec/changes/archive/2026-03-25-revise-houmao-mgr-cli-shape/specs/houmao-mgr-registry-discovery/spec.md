## ADDED Requirements

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

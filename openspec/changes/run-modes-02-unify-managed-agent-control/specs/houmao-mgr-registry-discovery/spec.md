# Spec Delta

## MODIFIED Requirements

### Requirement: Agent post-launch commands use registry-first discovery

`houmao-mgr agents` post-launch commands that require live runtime control SHALL resolve `<agent_ref>` by first looking up owner-local lifecycle records and operator execution locators in the shared registry before contacting a fallback server.

The active discovery chain SHALL be:
1. Look up `<agent_ref>` in the shared managed-agent registry's owner-local and execution-locator collections and reject conflicting or ambiguous matches
2. For an execution locator, enter its saved route, verify the execution binding, and resolve the owner's lifecycle record before interpreting runtime paths or control endpoints
3. Require the selected owner lifecycle record to be active for live prompt, stop, interrupt, state, and live subgroup commands unless the command explicitly supports stopped lifecycle records
4. From an active owner lifecycle record, determine the recorded run mode, backend and control path inside that owner context
5. For `houmao_server_rest` backends: extract server URL from the manifest's backend state
6. For owner-local managed agents, resolve the qualified mode/backend pair in the saved execution context and call the owner-side controller. Communication commands SHALL share admission with the gateway. Lifecycle commands SHALL remain available through the owner when the gateway is detached
7. If no matching lifecycle record or execution locator exists, retain the external communication-only lookup and existing pair-server fallback; explicit `--port` continues to bypass registry lookup

A matching execution locator whose owner is unreachable, unauthorized, stale, or incompatible SHALL report that outcome and SHALL NOT continue into caller-local or default-server fallback.

Stopped lifecycle records SHALL NOT be treated as active live targets for prompt, interrupt, live state, or gateway command routing. Commands that do not support stopped records SHALL fail with an actionable message that identifies the matched stopped record and points to supported lifecycle actions such as relaunch or cleanup.

#### Scenario: Post-launch command discovers active agent via shared registry

- **WHEN** an operator runs `houmao-mgr agents state --agent-name reviewer`
- **AND WHEN** the agent has an active lifecycle-aware shared registry record
- **THEN** `houmao-mgr` resolves the agent's backend type and control path from the registry record
- **AND THEN** the command does not require an explicit `--port` flag

#### Scenario: Live command rejects stopped registry target

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name reviewer --prompt "..."`
- **AND WHEN** the registry contains exactly one matching record with lifecycle state `stopped`
- **THEN** `houmao-mgr` rejects the target as inactive
- **AND THEN** the error identifies supported follow-up actions such as `agents relaunch` or `agents cleanup`

#### Scenario: Post-launch command falls back to port when no registry record exists

- **WHEN** an operator runs `houmao-mgr agents state --agent-name reviewer`
- **AND WHEN** no lifecycle-aware shared registry record, execution locator, or external communication-only record exists for that agent
- **THEN** `houmao-mgr` falls back to the `--port` flag, then `CAO_PORT` env var, then the default server URL
- **AND THEN** the command succeeds if the server is reachable and knows the agent

#### Scenario: Local tmux-backed agent is controlled directly without a server

- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name reviewer --prompt "..."`
- **AND WHEN** the shared registry record indicates an active local tmux-backed backend
- **THEN** `houmao-mgr` loads the `RuntimeSessionController` from the manifest path in the registry record
- **AND THEN** the owner admits and dispatches the prompt using the same arbiter as the gateway without contacting a pair server

#### Scenario: Unreachable executor does not fall through to a local namesake

- **WHEN** the selector resolves to a known execution locator but its owner route cannot be reached
- **THEN** the command reports owner unavailability for that agent and execution context
- **AND THEN** it does not use the caller's tmux server, open the owner manifest locally, or contact the default pair server

#### Scenario: Owner is reachable while the gateway is unavailable

- **WHEN** the manager resolves an active agent with a stopped gateway
- **THEN** it can still stop or inspect the agent through the verified execution owner without launching another provider

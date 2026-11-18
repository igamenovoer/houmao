# Houmao Manager Registry Discovery Spec Delta

## MODIFIED Requirements

### Requirement: Agent post-launch commands use registry-first discovery

`houmao-mgr agents` post-launch commands that require live runtime control SHALL resolve `<agent_ref>` by first looking up owner-local lifecycle records and operator execution locators in the shared registry before contacting a fallback server.

The active discovery chain SHALL be:
1. Look up `<agent_ref>` in the shared managed-agent registry's owner-local and execution-locator collections and reject conflicting or ambiguous matches
2. For an execution locator, enter its saved route, verify the execution binding, and resolve the owner's lifecycle record before interpreting runtime paths or control endpoints
3. Require the selected owner lifecycle record to be active for live prompt, stop, interrupt, state, and live subgroup commands unless the command explicitly supports stopped lifecycle records
4. From an active owner lifecycle record, determine the backend type and control path inside that owner context
5. For `houmao_server_rest` backends: extract server URL from the manifest's backend state
6. For owner-local tmux-backed backends, including `local_interactive`, `claude_headless`, `codex_headless`, `gemini_headless`, `dsh_acp`, and `dsh_web`: control directly via the owner-side `RuntimeSessionController`
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
- **AND THEN** the prompt is submitted directly without contacting `houmao-server`

#### Scenario: Unreachable executor does not fall through to a local namesake

- **WHEN** the selector resolves to a known execution locator but its owner route cannot be reached
- **THEN** the command reports owner unavailability for that agent and execution context
- **AND THEN** it does not use the caller's tmux server, open the owner manifest locally, or contact the default pair server

### Requirement: Registry-backed discovery includes external communication-only records

`houmao-mgr` registry-backed managed-agent discovery SHALL include external communication-only records as selectable communication targets while preserving the existing local lifecycle record contract.

Owner-local lifecycle records under `live_agents/` and executor-managed routing locators SHALL form the first registry discovery tier for normal managed-agent selectors. Conflicting managed matches SHALL fail explicitly. External records SHALL be considered only after no matching managed lifecycle target is selected. Explicit pair-port targeting SHALL continue to bypass registry discovery.

External discovery SHALL resolve by local external-agent id for `--agent-id` and by local external-agent name for `--agent-name`. It SHALL route to the stored remote agent reference rather than treating the local alias as a remote pair-managed identity. An execution profile with a matching name or address SHALL NOT upgrade an external record's authority.

#### Scenario: External record resolves after local lifecycle lookup

- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james`
- **AND WHEN** no owner-local lifecycle record or execution locator matches `remote-james`
- **AND WHEN** exactly one external communication-only record has local name `remote-james`
- **THEN** registry discovery resolves the external record
- **AND THEN** command routing uses the record's stored remote pair API base URL and remote agent reference

#### Scenario: Local lifecycle record takes precedence over external alias

- **WHEN** a local lifecycle record and an external communication-only record could both match selector `james`
- **THEN** registry discovery selects the local lifecycle record
- **AND THEN** it does not silently shadow local lifecycle authority with the external alias

#### Scenario: Explicit port bypass remains unchanged

- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james --port 9891`
- **THEN** the command uses the explicit local-loopback pair port behavior
- **AND THEN** it does not read owner-local lifecycle, execution-locator, or external communication-only registry records for that invocation

## ADDED Requirements

### Requirement: Executor-aware selectors preserve identity across execution contexts

Managed selectors SHALL resolve exact authoritative IDs and unique friendly names across owner-local records and execution locators. Equivalent entries for the same ID and binding SHALL deduplicate; differing bindings for one ID or multiple IDs for one name SHALL report conflict or ambiguity. Tmux aliases SHALL remain context-local convenience selectors and SHALL NOT infer a foreign owner.

#### Scenario: Same friendly name under different users requires disambiguation

- **WHEN** two known agents under different execution bindings share friendly name `reviewer`
- **THEN** friendly-name selection reports ambiguity with candidate agent IDs and execution contexts
- **AND THEN** exact agent-ID selection resolves the corresponding saved route

#### Scenario: Identical tmux names do not identify an executor

- **WHEN** a caller-local session and a delegated agent have the same tmux session name
- **THEN** tmux-name lookup alone does not select the delegated owner
- **AND THEN** selecting the delegated agent by its authoritative ID uses its recorded execution binding

### Requirement: Executor-managed lifecycle commands use owner authority for active and stopped agents

Executor-managed state, inspect, resume, interrupt, stop, and relaunch SHALL execute through the saved owner route. Stopped-agent recovery SHALL resolve preserved manifest authority only in that context. Successful stop SHALL retain the owner identity and execution locator needed for relaunch, and qualify returned artifact paths with the context. Unsupported controls SHALL fail without changing target type.

#### Scenario: Delegated stopped agent is relaunched through its owner

- **WHEN** an execution locator addresses a stopped agent with owner-side relaunch authority
- **THEN** relaunch restores that logical agent under the recorded execution binding
- **AND THEN** it does not scan caller-local runtime roots for a matching name or manifest

#### Scenario: Stop returns owner-qualified cleanup information

- **WHEN** a delegated agent with manifest authority stops successfully
- **THEN** the response identifies the owner context and its manifest/session-root locators
- **AND THEN** the operator execution locator remains addressable for owner-side lifecycle follow-up

### Requirement: Execution-locator listing distinguishes observed lifecycle from unverified state

Registry-backed listing SHALL include executor-managed agents using owner-observed state rather than caller-local liveness. Default active-only output SHALL show confirmed active agents; lifecycle-inclusive output SHALL expose known unavailable or unverified targets without declaring them stopped. Rows SHALL distinguish executor-managed, owner-local, and external communication-only authority and deduplicate equivalent identities.

#### Scenario: Active delegated agent appears without a local session

- **WHEN** an execution locator resolves to a currently active owner-side agent with no caller-local tmux session
- **THEN** the agent appears in active listing with its execution context and authority kind

#### Scenario: Unavailable owner remains a known unverified target

- **WHEN** lifecycle-inclusive listing encounters an execution locator whose owner cannot be contacted
- **THEN** output retains that known identity with unavailable or unverified status
- **AND THEN** it does not claim stopped state, remove the locator, or report a caller-local namesake as that agent


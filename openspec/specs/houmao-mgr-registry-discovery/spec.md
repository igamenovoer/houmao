## Purpose
Define registry-first managed-agent discovery and control for `houmao-mgr agents` commands.
## Requirements
### Requirement: Shared registry records preserve managed-agent lifecycle state
The shared registry SHALL represent managed-agent lifecycle state rather than only live tmux liveness.

Each registry record SHALL contain durable managed-agent identity and runtime locator metadata, including `agent_name`, `agent_id`, backend/tool identity, manifest path, session root, and agent-definition directory when available.

Each registry record SHALL expose a lifecycle state. At minimum, lifecycle state SHALL distinguish:

- `active`: live runtime control is available
- `stopped`: runtime artifacts remain addressable and relaunch may be available, but live prompt/gateway control is unavailable
- `relaunching`: a stopped or active record is in a bounded relaunch transition
- `retired`: the logical managed-agent identity is no longer intended for relaunch

Live liveness data such as leases, current tmux session names, and live gateway endpoints SHALL be modeled as active-only metadata and SHALL NOT be required for stopped or retired records.

Stopped records SHALL preserve the last known tmux session name separately from the current live tmux session name.

#### Scenario: Active registry record carries live liveness metadata
- **WHEN** a local tmux-backed managed agent is active
- **THEN** its registry record stores lifecycle state `active`
- **AND THEN** the record exposes active liveness metadata sufficient for active command routing
- **AND THEN** the record stores the current live tmux session name as the active terminal binding

#### Scenario: Stopped relaunchable registry record remains addressable
- **WHEN** a local tmux-backed managed agent is stopped and still has readable runtime relaunch metadata
- **THEN** its registry record stores lifecycle state `stopped`
- **AND THEN** the record preserves `agent_name`, `agent_id`, manifest path, session root, and agent-definition directory
- **AND THEN** the record clears active liveness and live gateway endpoint metadata
- **AND THEN** the record preserves the stopped tmux session name as last-known terminal metadata

#### Scenario: Stopped registry record does not masquerade as live
- **WHEN** a registry record stores lifecycle state `stopped`
- **THEN** active command routing does not treat that record as a live prompt or gateway target
- **AND THEN** the record does not need a fresh live lease to remain discoverable for lifecycle-aware commands

### Requirement: Agent post-launch commands use registry-first discovery
`houmao-mgr agents` post-launch commands that require live runtime control SHALL resolve `<agent_ref>` by first looking up an active lifecycle-aware managed-agent record in the shared registry before contacting a server.

The active discovery chain SHALL be:
1. Look up `<agent_ref>` in the shared managed-agent registry
2. Require the matched registry record to be active for live prompt, stop, interrupt, state, and live subgroup commands unless the command explicitly supports stopped lifecycle records
3. From an active registry record, determine the backend type and control path
4. For `houmao_server_rest` backends: extract server URL from the manifest's backend state
5. For local tmux-backed backends (`local_interactive`, `claude_headless`, `codex_headless`, `gemini_headless`): control directly via `RuntimeSessionController`
6. If active registry lookup fails because no lifecycle record exists: fall back to `--port` flag, then `CAO_PORT` environment variable, then default server URL

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
- **AND WHEN** no lifecycle-aware shared registry record exists for that agent
- **THEN** `houmao-mgr` falls back to the `--port` flag, then `CAO_PORT` env var, then the default server URL
- **AND THEN** the command succeeds if the server is reachable and knows the agent

#### Scenario: Local tmux-backed agent is controlled directly without a server
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-name reviewer --prompt "..."`
- **AND WHEN** the shared registry record indicates an active local tmux-backed backend
- **THEN** `houmao-mgr` loads the `RuntimeSessionController` from the manifest path in the registry record
- **AND THEN** the prompt is submitted directly without contacting `houmao-server`

### Requirement: `houmao-mgr agents list` aggregates from shared registry
`houmao-mgr agents list` SHALL read active agents from the shared managed-agent registry as its primary data source.

By default, `agents list` SHALL show active managed agents only. The command SHALL provide an explicit lifecycle-inclusive mode, such as `--all` or `--state <state>`, for stopped or retired records.

When a `houmao-server` is reachable, the list MAY be enriched with server-managed agent state (e.g., TUI tracking status), but the registry SHALL be the primary source so that agents launched without a server are still visible.

#### Scenario: Agents list shows locally launched active agents
- **WHEN** an operator runs `houmao-mgr agents list`
- **AND WHEN** agents were launched via `houmao-mgr agents launch` without a server
- **AND WHEN** those records have lifecycle state `active`
- **THEN** those agents appear in the list from the shared registry
- **AND THEN** the list does not require a running `houmao-server`

#### Scenario: Default agents list hides stopped records
- **WHEN** an operator runs `houmao-mgr agents list`
- **AND WHEN** the registry contains a stopped lifecycle record for `reviewer`
- **THEN** `reviewer` is not shown in the default active-only list
- **AND THEN** the output remains focused on currently live managed agents

#### Scenario: Agents list can include stopped records explicitly
- **WHEN** an operator runs `houmao-mgr agents list --state stopped`
- **AND WHEN** the registry contains a stopped lifecycle record for `reviewer`
- **THEN** the output includes `reviewer`
- **AND THEN** the output identifies the lifecycle state as `stopped`

#### Scenario: Agents list enriches with server state when available
- **WHEN** an operator runs `houmao-mgr agents list`
- **AND WHEN** a `houmao-server` is running with additional managed agents
- **THEN** the list includes both registry-discovered agents and server-managed agents
- **AND THEN** duplicate entries are deduplicated by agent identity

### Requirement: Relaunch resolves active and stopped relaunchable registry records
`houmao-mgr agents relaunch` SHALL resolve explicit local `--agent-id` and `--agent-name` selectors through lifecycle-aware registry records.

When the selected registry record is active and local tmux authority is healthy, relaunch SHALL use the existing active relaunch path.

When the selected registry record is active but local tmux authority is degraded because the tmux session still exists while the contractual primary surface is missing, relaunch SHALL use the degraded-active recovery path for that same logical managed agent.

When the selected registry record is active but local tmux authority is stale because the recorded tmux session no longer exists, relaunch SHALL use preserved local manifest authority to revive that same logical managed agent when supported relaunch metadata remains available.

When the selected registry record is active, local tmux authority is stale, and preserved manifest-owned relaunch authority is no longer readable, relaunch SHALL fail explicitly. The failure SHALL identify that neither active relaunch nor stopped revival is available and SHALL point operators to `houmao-mgr agents stop` followed by fresh `houmao-mgr agents launch`.

When the selected registry record is stopped and marked relaunchable, relaunch SHALL use the preserved local manifest authority to revive the stopped managed-agent session.

When the selected registry record is stopped but not relaunchable, relaunch SHALL fail explicitly and SHALL identify why relaunch is unavailable.

When no lifecycle-aware registry record exists for a selector, relaunch MAY use the pre-existing stopped-manifest scan as a migration/recovery fallback for sessions stopped before lifecycle-aware registry records were introduced.

#### Scenario: Relaunch targets a degraded active record by friendly name
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-name reviewer`
- **AND WHEN** exactly one registry record stores `agent_name = "reviewer"` with lifecycle state `active`
- **AND WHEN** local tmux inspection shows that the tmux session still exists but the contractual primary surface is missing
- **THEN** the command resolves that active record as a degraded-active recovery target
- **AND THEN** the command rebuilds the same logical managed agent instead of requiring a fresh launch

#### Scenario: Relaunch targets a stale active record by agent id
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id agent-123`
- **AND WHEN** the matching registry record still stores lifecycle state `active`
- **AND WHEN** local tmux inspection shows that the recorded tmux session no longer exists
- **AND WHEN** manifest-owned relaunch authority remains available
- **THEN** the command resolves that record as stale active local authority
- **AND THEN** the command revives the same logical managed agent rather than failing with a generic unusable-target error

#### Scenario: Relaunch fails cleanly for stale active record without preserved authority
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id agent-123`
- **AND WHEN** the matching registry record still stores lifecycle state `active`
- **AND WHEN** local tmux inspection shows that the recorded tmux session no longer exists
- **AND WHEN** manifest-owned relaunch authority is no longer readable
- **THEN** the command fails explicitly
- **AND THEN** the error identifies that neither active relaunch nor stopped revival is available
- **AND THEN** the error points operators to `houmao-mgr agents stop` followed by fresh `houmao-mgr agents launch`

#### Scenario: Relaunch targets a stopped relaunchable record by friendly name
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-name reviewer --chat-session-mode tool_last_or_new`
- **AND WHEN** exactly one registry record stores `agent_name = "reviewer"`, lifecycle state `stopped`, and relaunchable runtime authority
- **THEN** the command resolves that stopped record as the relaunch target
- **AND THEN** the command revives the same logical managed agent instead of requiring a fresh launch

#### Scenario: Relaunch rejects stopped non-relaunchable record
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id agent-123`
- **AND WHEN** the matching registry record has lifecycle state `stopped` and is not relaunchable
- **THEN** the command fails explicitly
- **AND THEN** the error identifies that the stopped record exists but does not contain supported relaunch authority

#### Scenario: Relaunch migration fallback republishes lifecycle record
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-name reviewer`
- **AND WHEN** no lifecycle-aware registry record matches
- **AND WHEN** exactly one stopped runtime manifest under the effective runtime root matches the selector
- **THEN** the command may recover from that stopped manifest
- **AND THEN** a successful relaunch publishes an active lifecycle-aware registry record for future lookup

### Requirement: `--port` flag remains as optional override
All `houmao-mgr agents` commands that currently accept `--port` SHALL continue to accept it as an optional override that bypasses registry-first discovery.

When `--port` is explicitly provided, the command SHALL contact the server at that port directly without attempting registry lookup first.

#### Scenario: Explicit port overrides registry discovery
- **WHEN** an operator runs `houmao-mgr agents state <agent_ref> --port 9889`
- **THEN** `houmao-mgr` contacts the server at port 9889 directly
- **AND THEN** registry lookup is skipped for this invocation

### Requirement: Local registry-first discovery resolves exact ids, unique names, and unique tmux aliases

For serverless local `houmao-mgr agents` commands that resolve a managed agent through the shared registry, the system SHALL support all of the following local target forms when they are valid for the command's lifecycle scope:

- exact authoritative `agent_id`
- unique friendly `agent_name`
- unique exact current tmux session name from an active registry record's terminal metadata

For the native CLI surface, the local registry-backed discovery path SHALL be driven by explicit selector flags rather than one positional managed-agent reference:

- `--agent-id <id>` performs exact authoritative-id lookup
- `--agent-name <name>` performs friendly-name lookup using the raw creation-time name supplied during managed-agent launch

For `--agent-name` targeting, operators SHALL provide the same raw friendly name they used at creation time. The system SHALL NOT require callers to use canonical `AGENTSYS-...` names on this selector surface.

When a caller provides an `--agent-name` value that begins with a case-sensitive or case-insensitive `AGENTSYS` namespace prefix plus separator, the command SHALL fail explicitly instead of silently normalizing or accepting that prefixed form as the user-facing selector.

The tmux-session alias path remains an additional local discovery capability for serverless tooling and current-session-adjacent workflows, but it SHALL resolve only active records with current live tmux session metadata. It SHALL NOT match stopped records by last-known tmux session name for live command routing, SHALL NOT redefine tmux session names as managed-agent identity, and SHALL NOT require pair-managed server APIs to learn tmux-local aliases.

When friendly-name lookup or tmux-session alias lookup matches more than one registry record in the command's lifecycle scope, the command SHALL fail explicitly and SHALL surface enough identity and lifecycle metadata for the operator to disambiguate the target.

#### Scenario: Local command resolves a managed agent by exact authoritative id

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123`
- **AND WHEN** an active shared-registry record stores `agent_id = "abc123"`
- **THEN** `houmao-mgr` resolves that exact record as the local managed-agent target
- **AND THEN** the operator does not depend on friendly-name uniqueness for that control action

#### Scenario: Local command resolves a managed agent by raw friendly name

- **WHEN** an operator runs `houmao-mgr agents state --agent-name james`
- **AND WHEN** exactly one active shared-registry record stores `agent_name = "james"`
- **THEN** `houmao-mgr` resolves that record as the local managed-agent target
- **AND THEN** the operator uses the same raw name that was supplied during creation

#### Scenario: Prefixed canonical name is rejected on `--agent-name`

- **WHEN** an operator runs `houmao-mgr agents state --agent-name AGENTSYS-james`
- **THEN** `houmao-mgr` rejects that selector with an explicit unprefixed-agent-name error
- **AND THEN** the command does not silently normalize that value into a friendly-name lookup

#### Scenario: Ambiguous friendly-name lookup fails closed

- **WHEN** an operator runs `houmao-mgr agents state --agent-name gpu`
- **AND WHEN** more than one active shared-registry record stores `agent_name = "gpu"`
- **THEN** `houmao-mgr` fails that resolution explicitly
- **AND THEN** the error lists candidate `agent_id`, `agent_name`, lifecycle state, and current terminal values rather than silently choosing one

#### Scenario: Local tooling resolves a managed agent by tmux session alias

- **WHEN** local serverless tooling resolves the tmux session alias `hm-gw-track-codex`
- **AND WHEN** exactly one active shared-registry record has current terminal session name `hm-gw-track-codex`
- **THEN** the system resolves that record as the local managed-agent target
- **AND THEN** the tooling does not need to rediscover the friendly `agent_name` first

#### Scenario: Stopped record last-known tmux session is not a live alias
- **WHEN** local serverless tooling resolves the tmux session alias `HOUMAO-reviewer-old`
- **AND WHEN** the only matching registry record has lifecycle state `stopped` and last-known terminal session name `HOUMAO-reviewer-old`
- **THEN** active live-target resolution does not resolve that record by tmux alias
- **AND THEN** the operator must use `--agent-id`, `--agent-name`, or cleanup/relaunch lifecycle commands to address the stopped record

#### Scenario: Pair-managed explicit port bypass keeps server authority semantics

- **WHEN** an operator runs `houmao-mgr agents state --agent-id abc123 --port 9889`
- **THEN** `houmao-mgr` bypasses local registry resolution and contacts the server authority at port `9889`
- **AND THEN** the command does not rely on tmux-local alias semantics for that invocation

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

### Requirement: Managed-agent stop responses include durable cleanup locators
`houmao-mgr agents stop` SHALL include durable cleanup locator fields in its successful structured response when the resolved managed-agent target exposes local manifest authority.

At minimum, the successful stop response SHALL include:

- `manifest_path`
- `session_root`

The command SHALL capture these values before clearing or otherwise losing the live shared-registry record. These locator fields SHALL remain valid for supported `houmao-mgr agents cleanup session|logs|mailbox --manifest-path` or `--session-root` follow-up as long as the corresponding runtime-owned artifacts still exist.

For relaunchable local tmux-backed managed agents, a successful stop SHALL update the shared registry record to lifecycle state `stopped` instead of deleting the managed-agent identity record. The stopped record SHALL preserve the locators needed for later `houmao-mgr agents relaunch` and `houmao-mgr agents cleanup`.

The command SHALL clear active liveness and live gateway metadata from the registry record after stop succeeds. The stopped record SHALL NOT remain an active live target solely to support later cleanup by name or id.

This same stop contract SHALL apply when the selected local tmux-backed active record is degraded or stale, as long as local manifest-owned stop authority still exists.

#### Scenario: Local stop returns cleanup locators before lifecycle transition
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name reviewer`
- **AND WHEN** the target resolves through a fresh local shared-registry record with manifest authority
- **THEN** the successful stop response includes `manifest_path` and `session_root`
- **AND THEN** those fields identify the stopped session envelope that can be passed to `houmao-mgr agents cleanup`

#### Scenario: Stop preserves relaunchable managed-agent registry identity
- **WHEN** `houmao-mgr agents stop --agent-id agent-123` successfully stops a local tmux-backed managed session
- **THEN** the registry record for `agent-123` transitions to lifecycle state `stopped`
- **AND THEN** the record preserves the manifest path, session root, agent-definition directory, and friendly agent name
- **AND THEN** active liveness and live gateway metadata are cleared from the record

#### Scenario: Degraded active stop still publishes cleanup locators
- **WHEN** `houmao-mgr agents stop --agent-id agent-123` resolves an active local tmux-backed managed session
- **AND WHEN** local tmux inspection shows that the session still exists but the contractual primary surface is missing
- **THEN** the command still succeeds through degraded-active recovery
- **AND THEN** the successful stop response includes `manifest_path` and `session_root`
- **AND THEN** the registry record no longer remains an active live target after stop completes

#### Scenario: Stale active stop retires registry record when manifest authority is unavailable
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id agent-123`
- **AND WHEN** the matching registry record still stores lifecycle state `active`
- **AND WHEN** local tmux inspection shows that the recorded tmux session no longer exists
- **AND WHEN** manifest-owned relaunch authority is no longer readable
- **THEN** the command clears the live lifecycle claim and retires the registry record idempotently
- **AND THEN** the response indicates that retirement happened without preserved relaunch authority
- **AND THEN** the response may omit `manifest_path` and `session_root` when local manifest authority is no longer readable

#### Scenario: Missing local manifest authority omits cleanup locators
- **WHEN** `houmao-mgr agents stop` resolves a target whose control path does not expose local manifest or session-root authority
- **THEN** the command may omit `manifest_path` and `session_root`
- **AND THEN** the response remains valid for the stop action without inventing cleanup locators

### Requirement: Registry-backed discovery includes external communication-only records
`houmao-mgr` registry-backed managed-agent discovery SHALL include external communication-only records as selectable communication targets while preserving the existing local lifecycle record contract.

Local lifecycle records under `live_agents/` SHALL remain the first registry discovery source for normal managed-agent selectors. External records SHALL be considered only after no matching local lifecycle record is selected. Explicit pair-port targeting SHALL continue to bypass registry discovery.

External discovery SHALL resolve by local external-agent id for `--agent-id` and by local external-agent name for `--agent-name`. It SHALL route to the stored remote agent reference rather than treating the local alias as a remote pair-managed identity.

#### Scenario: External record resolves after local lifecycle lookup
- **WHEN** an operator runs `houmao-mgr agents state --agent-name remote-james`
- **AND WHEN** no local lifecycle record matches `remote-james`
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
- **AND THEN** it does not read local lifecycle or external communication-only registry records for that invocation

### Requirement: External registry records remain separate from local lifecycle records
External communication-only records SHALL be stored in a registry collection that is separate from local lifecycle records. Local lifecycle validation, lease freshness, tmux liveness probing, relaunch resolution, and stale local runtime cleanup SHALL NOT require external records to contain local runtime metadata.

Registry cleanup that is designed for stale local lifecycle records SHALL NOT delete valid external communication-only records merely because they lack local tmux sessions, local leases, or local manifest paths.

#### Scenario: External record without local manifest remains valid
- **WHEN** the registry contains a valid external communication-only record with no local manifest path and no tmux session metadata
- **THEN** registry readers accept it as an external locator record
- **AND THEN** local lifecycle record validation is not applied to that external record

#### Scenario: Local stale cleanup preserves external record
- **WHEN** a local stale-registry cleanup pass inspects registry state
- **AND WHEN** it encounters a valid external communication-only record
- **THEN** the cleanup pass preserves the external record
- **AND THEN** it does not remove the record due to missing local tmux liveness


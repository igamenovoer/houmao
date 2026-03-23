## ADDED Requirements

### Requirement: `houmao-server` keeps TUI registration separate from native headless launch
`houmao-server` SHALL keep its existing server-owned registration bridge for terminal-backed compatibility sessions and SHALL NOT require that bridge for native headless agents.

For TUI-backed registrations, `terminal_id` SHALL remain part of the compatibility registration contract.

For headless agents, `houmao-server` SHALL create server authority through its Houmao-owned native headless launch path instead of through delegated registration.

#### Scenario: TUI registration remains terminal-keyed
- **WHEN** a caller registers a TUI-backed managed session through the compatibility registration bridge
- **THEN** `houmao-server` continues to require `terminal_id` for that registration
- **AND THEN** the TUI registration path remains distinct from the native headless launch path

#### Scenario: Headless authority does not require delegated registration
- **WHEN** a caller launches a headless managed agent through the native headless API
- **THEN** `houmao-server` creates authority for that agent without requiring a delegated launch registration record
- **AND THEN** headless lifecycle does not depend on child-CAO session or terminal discovery

### Requirement: `houmao-server` persists native headless authority under the server-owned state tree
For each native headless agent launched through `houmao-server`, the server SHALL persist a dedicated managed-agent authority record under the server-owned state tree.

In v1, that authority subtree SHALL live under:

```text
<server_root>/state/managed_agents/<tracked_agent_id>/
```

That subtree SHALL contain an `authority.json` record for the launched headless agent.

At minimum, that `authority.json` record SHALL persist:

- `tracked_agent_id`
- `tool`
- `manifest_path`
- `session_root`
- `tmux_session_name`
- optional `agent_name`
- optional `agent_id`

`houmao-server` SHALL use that authority record plus runtime-owned evidence such as the manifest and session root to rebuild headless agent authority on startup or recovery.

`houmao-server` SHALL NOT admit a headless agent from a stray manifest alone when no matching server-owned headless authority record exists.

#### Scenario: Native headless launch writes server-owned authority
- **WHEN** `houmao-server` successfully launches a native headless agent
- **THEN** it writes an `authority.json` record under `state/managed_agents/<tracked_agent_id>/`
- **AND THEN** later restart recovery can use that server-owned authority record to rebuild the managed agent

#### Scenario: Stray manifest without authority is not re-admitted
- **WHEN** a runtime manifest for a headless session still exists on disk
- **AND WHEN** no matching server-owned `authority.json` record exists for that headless session
- **THEN** `houmao-server` does not re-admit that headless session into managed-agent authority from the manifest alone
- **AND THEN** restart recovery remains bounded by explicit server-owned authority

### Requirement: `houmao-server` persists active headless turn authority and reconciles it across restart
When `houmao-server` accepts a headless turn for a managed headless agent, it SHALL persist active-turn authority under the same managed-agent authority subtree.

In v1, that active-turn record SHALL live at:

```text
<server_root>/state/managed_agents/<tracked_agent_id>/active_turn.json
```

At minimum, `active_turn.json` SHALL persist:

- `tracked_agent_id`
- `turn_id`
- `turn_index`
- `turn_artifact_dir`
- `started_at_utc`
- live targeting metadata needed for later interrupt or reconciliation when available

Single-active-turn admission gating and active-turn interrupt targeting SHALL use that persisted active-turn authority rather than depending only on in-memory runner state.

On startup or recovery, `houmao-server` SHALL reconcile `active_turn.json` against live tmux evidence and durable turn artifacts before it admits another turn for that agent or reports that the agent has no active turn.

If reconciliation determines the earlier turn is still active, `houmao-server` SHALL restore active-turn authority for that turn.

If reconciliation determines the earlier turn has already reached a terminal state, `houmao-server` SHALL clear the active-turn record and reopen turn admission for that agent.

#### Scenario: Restart preserves single-active-turn gating for a live turn
- **WHEN** `houmao-server` restarts while `active_turn.json` exists for a headless managed agent
- **AND WHEN** reconciliation determines that recorded turn is still active
- **THEN** the server continues rejecting overlapping turn submissions for that agent
- **AND THEN** single-active-turn semantics do not disappear merely because the server restarted

#### Scenario: Restart clears active-turn authority for a terminal turn
- **WHEN** `houmao-server` restarts while `active_turn.json` exists for a headless managed agent
- **AND WHEN** reconciliation determines that recorded turn has already reached a terminal state
- **THEN** the server clears the active-turn record
- **AND THEN** the next turn submission for that agent may be admitted normally

### Requirement: `houmao-server` maintains a managed-agent registry that includes headless agents
In addition to the existing known-session tracking for terminal-backed sessions, `houmao-server` SHALL maintain a server-owned managed-agent registry that can represent both TUI-backed and headless agents.

For TUI-backed agents, that managed-agent registry MAY project from the existing known-session registry and terminal-alias mappings.

For headless agents, that managed-agent registry SHALL use server-owned `authority.json`, reconciled `active_turn.json`, runtime-owned manifest state, and turn-artifact evidence to maintain live identity and coarse state, and SHALL NOT require a fabricated terminal alias.

On startup or recovery, `houmao-server` SHALL rebuild server-launched headless managed agents from server-owned headless authority plus manifest-backed runtime evidence rather than requiring child CAO session discovery.

#### Scenario: Headless managed agent rebuilds after server restart
- **WHEN** `houmao-server` restarts and finds a valid server-owned headless launch record whose manifest and session root still exist
- **THEN** it rebuilds that headless managed agent into the managed-agent registry
- **AND THEN** the headless agent becomes available again through `/houmao/agents/*` without needing a `terminal_id`

#### Scenario: Headless admission does not fabricate a terminal alias
- **WHEN** `houmao-server` admits a registered headless managed agent
- **THEN** it tracks that agent through managed-agent identity plus headless metadata
- **AND THEN** it does not invent a fake `terminal_id` solely to fit the headless agent into terminal-keyed structures

### Requirement: Existing CAO-compatible and terminal-keyed routes remain TUI-specific compatibility surfaces
When `houmao-server` adds headless managed-agent support, it SHALL keep existing CAO-compatible `/sessions/*` and `/terminals/*` routes plus existing `/houmao/terminals/{terminal_id}/*` routes as TUI-specific or CAO-compatible surfaces.

`houmao-server` SHALL NOT publish registered headless managed agents as fake CAO sessions or fake terminals on those routes.

Headless managed agents SHALL instead be exposed through the Houmao-owned `/houmao/agents/*` route family.

#### Scenario: Headless managed agent stays off terminal-keyed compatibility routes
- **WHEN** `houmao-server` is managing a registered headless Claude agent
- **THEN** that headless agent is available through `/houmao/agents/*`
- **AND THEN** the server does not fabricate a terminal-keyed compatibility entry for it on `/houmao/terminals/{terminal_id}/*`

#### Scenario: TUI compatibility routes remain available for terminal-backed sessions
- **WHEN** `houmao-server` is managing a TUI-backed session that already has a `terminal_id`
- **THEN** callers can continue using the existing terminal-keyed compatibility routes for that session
- **AND THEN** adding headless managed-agent support does not remove or rename the TUI compatibility surface

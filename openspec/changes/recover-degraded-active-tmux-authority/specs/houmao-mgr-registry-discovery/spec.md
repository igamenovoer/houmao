## MODIFIED Requirements

### Requirement: Relaunch resolves active and stopped relaunchable registry records
`houmao-mgr agents relaunch` SHALL resolve explicit local `--agent-id` and `--agent-name` selectors through lifecycle-aware registry records.

When the selected registry record is active and local tmux authority is healthy, relaunch SHALL use the existing active relaunch path.

When the selected registry record is active but local tmux authority is degraded because the tmux session still exists while the contractual primary surface is missing, relaunch SHALL use the degraded-active recovery path for that same logical managed agent.

When the selected registry record is active but local tmux authority is stale because the recorded tmux session no longer exists, relaunch SHALL use preserved local manifest authority to revive that same logical managed agent when supported relaunch metadata remains available.

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

#### Scenario: Missing local manifest authority omits cleanup locators
- **WHEN** `houmao-mgr agents stop` resolves a target whose control path does not expose local manifest or session-root authority
- **THEN** the command may omit `manifest_path` and `session_root`
- **AND THEN** the response remains valid for the stop action without inventing cleanup locators

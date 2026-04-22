## ADDED Requirements

### Requirement: Local tmux-backed managed runtime derives authority health separately from lifecycle state
For local tmux-backed managed-agent sessions, the runtime SHALL derive local tmux-authority health from tmux inspection rather than persisting additional shared lifecycle states.

At minimum, the derived local authority health model SHALL distinguish:

- `healthy`: the tmux session exists and the contractual primary window `0` and pane `0` exist
- `degraded_missing_primary`: the tmux session exists but the contractual primary surface is missing
- `stale_missing_session`: the persisted active authority points at a tmux session that no longer exists

This derived health classification SHALL be host-local runtime state. The shared registry lifecycle state SHALL remain limited to `active`, `stopped`, `relaunching`, and `retired`.

#### Scenario: Existing tmux session missing the primary agent surface is classified as degraded
- **WHEN** a local tmux-backed managed-agent record still points at an existing tmux session
- **AND WHEN** tmux inspection shows that primary window `0` or pane `0` is missing for that session
- **THEN** the runtime classifies the local authority as `degraded_missing_primary`
- **AND THEN** it does not persist a new shared lifecycle-state value for that host-local condition

#### Scenario: Missing tmux session behind an active record is classified as stale
- **WHEN** a local tmux-backed managed-agent record still claims lifecycle state `active`
- **AND WHEN** tmux inspection shows that the recorded tmux session no longer exists
- **THEN** the runtime classifies the local authority as `stale_missing_session`
- **AND THEN** the shared lifecycle state remains a separate concern from that derived local health result

## MODIFIED Requirements

### Requirement: Runtime stop preserves relaunch metadata for lifecycle-aware registry records
For local tmux-backed managed-agent sessions with runtime-owned manifest authority, runtime stop SHALL preserve enough metadata for a later stopped-session relaunch before live process/container metadata is cleared.

At minimum, the preserved metadata SHALL include:

- managed-agent name and id when present
- session manifest path
- session root
- agent-definition directory when present
- runtime home path through existing manifest/build metadata
- memory root, memo file, and pages directory when present
- launch-profile relaunch chat-session policy when present
- last known tmux session name

When stop removes a tmux session, the runtime manifest SHALL no longer claim that the removed tmux session is an active live authority, but it SHALL preserve or reconstruct relaunch authority needed by the lifecycle registry.

When the selected local tmux-backed managed-agent authority is `degraded_missing_primary`, runtime stop SHALL still be able to tear down the surviving tmux session remnant and preserve stopped-session continuity metadata.

When the selected local tmux-backed managed-agent authority is `stale_missing_session`, runtime stop SHALL still be able to clear live lifecycle claims and preserve stopped-session continuity metadata when relaunch authority remains readable from manifest-owned state.

#### Scenario: Force cleanup stop preserves relaunch metadata
- **WHEN** a local interactive managed agent is stopped with force cleanup
- **AND WHEN** the runtime kills the provider tmux session
- **THEN** the stopped session manifest and lifecycle registry record preserve the agent identity, runtime home, manifest path, session root, and agent-definition directory
- **AND THEN** live liveness metadata for the killed tmux session is cleared

#### Scenario: Degraded active stop preserves relaunch metadata after removing tmux remnant
- **WHEN** a local tmux-backed managed agent still has an active lifecycle record
- **AND WHEN** its tmux session still exists but the contractual primary surface is missing
- **AND WHEN** runtime stop is requested
- **THEN** the runtime removes the surviving tmux session remnant
- **AND THEN** the resulting stopped metadata preserves relaunch authority for the same logical managed agent

#### Scenario: Stale active stop can retire live claims without a remaining tmux session
- **WHEN** a local tmux-backed managed agent still has an active lifecycle record
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** manifest-owned relaunch authority remains readable
- **THEN** runtime stop clears the live lifecycle claim without requiring tmux teardown
- **AND THEN** the resulting stopped metadata preserves relaunch authority for later recovery

#### Scenario: Stop preserves launch-profile relaunch policy
- **WHEN** a managed agent was launched from a profile with relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** the agent is stopped
- **THEN** the stopped runtime metadata preserves that relaunch policy
- **AND THEN** a later relaunch without explicit chat-session flags can use the stored policy

### Requirement: Active relaunch remains distinct from stopped-session revival
The existing active relaunch operation SHALL continue to use live tmux-backed authority for the selected managed agent when that authority is healthy.

Stopped-session revival SHALL remain a separate runtime path that recreates live authority from preserved relaunch metadata when the selected lifecycle record is stopped or when active local authority has become `stale_missing_session`.

When active local authority is `degraded_missing_primary`, active relaunch SHALL rebuild the contractual primary tmux surface inside the existing tmux session before continuing provider-start relaunch behavior.

When active local authority is `stale_missing_session` and preserved relaunch authority remains available, relaunch SHALL transition through the stopped-session revival path instead of failing with a generic stale-authority error.

#### Scenario: Active relaunch rebuilds a degraded primary surface
- **WHEN** a runtime controller is asked to perform active relaunch
- **AND WHEN** the selected local tmux session still exists
- **AND WHEN** the contractual primary surface is missing from that tmux session
- **THEN** relaunch rebuilds the stable primary tmux surface in the existing session
- **AND THEN** provider-start relaunch continues for the same logical managed agent

#### Scenario: Stale active relaunch uses stopped-session revival semantics
- **WHEN** a runtime controller is asked to perform relaunch for a local managed-agent record that still claims lifecycle state `active`
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** preserved relaunch authority remains available
- **THEN** the runtime uses stopped-session revival semantics to create a fresh live tmux container
- **AND THEN** a successful relaunch republishes active lifecycle metadata for the same logical managed agent

#### Scenario: Stopped-session revival publishes a fresh active authority
- **WHEN** stopped-session revival succeeds
- **THEN** the runtime manifest records the new live tmux session authority
- **AND THEN** the registry record transitions to lifecycle state `active`
- **AND THEN** live command routing can use the revived record

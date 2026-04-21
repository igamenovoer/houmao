## ADDED Requirements

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

#### Scenario: Force cleanup stop preserves relaunch metadata
- **WHEN** a local interactive managed agent is stopped with force cleanup
- **AND WHEN** the runtime kills the provider tmux session
- **THEN** the stopped session manifest and lifecycle registry record preserve the agent identity, runtime home, manifest path, session root, and agent-definition directory
- **AND THEN** live liveness metadata for the killed tmux session is cleared

#### Scenario: Stop preserves launch-profile relaunch policy
- **WHEN** a managed agent was launched from a profile with relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** the agent is stopped
- **THEN** the stopped runtime metadata preserves that relaunch policy
- **AND THEN** a later relaunch without explicit chat-session flags can use the stored policy

### Requirement: Runtime can revive stopped tmux-backed managed sessions without rebuilding the home
The runtime SHALL provide a stopped-session revival path for relaunchable local tmux-backed managed sessions.

Stopped-session revival SHALL reuse the existing managed runtime home and logical managed-agent identity. It SHALL NOT create a fresh managed-agent identity and SHALL NOT require a fresh launch from recipe or profile.

Stopped-session revival SHALL create a new live tmux container when the previous tmux session was removed. It SHALL update the runtime manifest and registry liveness metadata to reference the new live tmux session after successful revival.

Stopped-session revival SHALL apply the effective relaunch chat-session selector using the same provider-native semantics as active relaunch:

- `new` starts a fresh provider chat against the existing home
- `tool_last_or_new` asks the provider CLI to continue the latest provider-local chat when supported
- `exact` asks the provider CLI to resume the requested provider session id when supported

#### Scenario: Local interactive stopped relaunch reuses home and continues provider chat
- **WHEN** a stopped local interactive Codex managed agent has a preserved runtime home and relaunchable registry record
- **AND WHEN** an operator runs `houmao-mgr agents relaunch --agent-name reviewer --chat-session-mode tool_last_or_new`
- **THEN** the runtime creates a new tmux-backed provider surface for the same logical managed agent
- **AND THEN** the launch uses the existing managed runtime home
- **AND THEN** the provider is started with tool-native latest-chat continuation arguments when supported

#### Scenario: Headless stopped relaunch restores a turn-ready tmux surface
- **WHEN** a stopped headless managed agent has a preserved runtime home and relaunchable registry record
- **AND WHEN** an operator runs `houmao-mgr agents relaunch --agent-id agent-123`
- **THEN** the runtime creates a new tmux-backed headless control surface for the same logical managed agent
- **AND THEN** the manifest and registry record are updated to active lifecycle state after successful relaunch
- **AND THEN** subsequent prompt turns use the revived runtime authority

#### Scenario: Stopped relaunch fails without supported relaunch authority
- **WHEN** a stopped managed-agent manifest lacks the metadata needed to rebuild provider-start runtime state
- **AND WHEN** an operator requests stopped-session relaunch
- **THEN** the runtime returns an explicit relaunch error
- **AND THEN** the error does not silently fall back to creating a fresh launch

### Requirement: Active relaunch remains distinct from stopped-session revival
The existing active relaunch operation SHALL continue to require a valid live tmux-backed authority for the selected managed agent.

Stopped-session revival SHALL be a separate runtime path or an explicitly separated branch that first recreates live authority and repairs manifest/registry liveness before using provider-start relaunch behavior.

#### Scenario: Active relaunch rejects stale active authority
- **WHEN** a runtime controller is asked to perform ordinary active relaunch
- **AND WHEN** its current live tmux session binding is missing or does not match active authority
- **THEN** ordinary active relaunch fails with a stale-authority error
- **AND THEN** the caller must use stopped-session revival when the selected lifecycle record is stopped and relaunchable

#### Scenario: Stopped-session revival publishes a fresh active authority
- **WHEN** stopped-session revival succeeds
- **THEN** the runtime manifest records the new live tmux session authority
- **AND THEN** the registry record transitions to lifecycle state `active`
- **AND THEN** live command routing can use the revived record

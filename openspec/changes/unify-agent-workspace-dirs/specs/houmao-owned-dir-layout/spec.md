## REMOVED Requirements

### Requirement: Workspace-local scratch behavior is manual-cleanup and documentation-guided in this change
**Reason**: Replaced by explicit per-agent workspace scratch-lane cleanup operations.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## MODIFIED Requirements

### Requirement: Houmao-owned directories are split into fixed responsibility zones
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different responsibilities while making the active project overlay the default local root for non-registry state.

The default per-user shared Houmao root that remains global SHALL be:
- registry root: `~/.houmao/registry`

For maintained local project-aware command flows, the default overlay-owned roots SHALL be:
- runtime root: `<active-overlay>/runtime`
- mailbox root: `<active-overlay>/mailbox`
- agent workspace root family: `<active-overlay>/memory/agents/<agent-id>/`
- easy root: `<active-overlay>/easy`

For each tmux-backed managed agent, the default workspace lanes SHALL be derived as:
- memo file: `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- scratch lane: `<active-overlay>/memory/agents/<agent-id>/scratch/`
- persist lane: `<active-overlay>/memory/agents/<agent-id>/persist/` when persistence is enabled

The system SHALL NOT derive current managed-agent scratch state from `<active-overlay>/jobs/<session-id>/`.

The system SHALL continue to support stronger override surfaces for global registry, runtime, mailbox, and exact persist locations where supported.

When both an explicit CLI/config override and an env-var override exist for the same effective location, the explicit override SHALL win.
When no explicit override exists but a supported env-var override is set, the env-var override SHALL win.
When neither explicit override nor env-var override is supplied for a maintained local project-aware flow, the system SHALL use the overlay-derived defaults above.

#### Scenario: Project-aware local roots resolve workspace lanes under the active overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local Houmao launch flow starts managed agent id `researcher-id` without stronger root overrides
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root is `/repo/.houmao/mailbox`
- **AND THEN** the effective memo file is `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the effective scratch lane is `/repo/.houmao/memory/agents/researcher-id/scratch`
- **AND THEN** the effective persist lane is `/repo/.houmao/memory/agents/researcher-id/persist` when persistence is enabled

#### Scenario: Shared registry remains under the user home by default
- **WHEN** an operator runs maintained local Houmao commands in project context without a registry override
- **THEN** the effective shared registry root remains under `~/.houmao/registry`
- **AND THEN** the command does not relocate the registry under the active project overlay by default

#### Scenario: Custom project agent-definition path does not change the fixed overlay-owned runtime family
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` sets `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** a maintained local Houmao launch flow starts managed agent id `researcher-id` without stronger root overrides
- **THEN** the effective runtime root remains `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root, workspace root family, and easy root remain `/repo/.houmao/mailbox`, `/repo/.houmao/memory/agents/researcher-id`, and `/repo/.houmao/easy`

### Requirement: Houmao-owned zones keep discovery, durable state, shared mailbox state, and destructive scratch separate
The system SHALL preserve distinct mutability and ownership boundaries across the Houmao-owned zones.

At minimum:
- the registry root SHALL contain discovery-oriented metadata only,
- the runtime root SHALL contain durable Houmao-managed runtime and launcher state,
- the mailbox root SHALL contain shared mailbox transport state,
- the per-agent workspace memo file SHALL contain live-agent instruction and loop initialization state,
- the per-agent workspace scratch lane SHALL contain temporary files, transient outputs, retry ledgers, and destructive scratch work,
- the per-agent workspace persist lane SHALL contain durable agent memory when persistence is enabled.

Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox contents MUST NOT be relocated into the shared registry root as part of this directory model.

Mailbox state MUST remain independently relocatable and MUST NOT be implicitly nested under the runtime root or a per-agent workspace lane just because those other zones exist.

#### Scenario: Registry root is not used as mutable CAO or runtime storage
- **WHEN** the system publishes live-agent discovery metadata and also starts a launcher-managed CAO service
- **THEN** the shared registry contains only registry-owned discovery records
- **AND THEN** launcher-managed CAO home state and durable runtime session state are stored outside the registry root

#### Scenario: Scratch lane does not replace shared mailbox or durable runtime state
- **WHEN** a started session writes scratch files while also using mailbox support and runtime-managed manifest persistence
- **THEN** scratch files and temporary outputs live under that agent's scratch lane
- **AND THEN** mailbox content and durable runtime session state remain in their own independent zones

#### Scenario: Memo file stays separate from scratch and persist lanes
- **WHEN** a loop initialization records live-agent rules for managed agent `researcher`
- **THEN** the rules live in `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** temporary outputs remain in the scratch lane
- **AND THEN** durable archive notes remain in the persist lane when persistence is enabled

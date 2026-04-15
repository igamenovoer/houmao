# houmao-owned-dir-layout Specification

## Purpose
Define the ownership boundaries, default roots, and authoritative identity model for Houmao-managed registry, runtime, mailbox, and job-directory state.
## Requirements
### Requirement: Maintained local default paths retire `.agentsys*` path families
Maintained workspace-local and run-local default path families that currently derive from `.agentsys` or `.agentsys-*` for agent-definition working trees or scratch outputs SHALL use `.houmao` or another Houmao-owned path family instead.

When the system derives a default ambient agent-definition root from a working directory without explicit CLI override, environment override, or discovered project config, that default SHALL be `<working-directory>/.houmao/agents`.
When maintained runtime or demo helpers require a workspace-local fallback scratch directory that previously lived under a `.agentsys*`-named sibling, that default SHALL instead live under `<working-directory>/.houmao/`.

This requirement applies to active maintained workflows and helper code. Historical or archival material MAY continue to mention retired `.agentsys` paths when it is clearly not part of the supported live surface.

#### Scenario: Ambient no-config agent-definition root uses `.houmao`
- **WHEN** the system needs a default agent-definition root for working directory `/repo/app`
- **AND WHEN** no explicit override, no env override, and no discovered `.houmao/houmao-config.toml` are present
- **THEN** the default ambient agent-definition root is `/repo/app/.houmao/agents`
- **AND THEN** the system does not derive `/repo/app/.agentsys/agents`

#### Scenario: Workspace-local fallback scratch path avoids `.agentsys*`
- **WHEN** a maintained helper needs a workspace-local fallback scratch directory under `/repo/app`
- **AND WHEN** no more specific manifest-adjacent or explicit output root applies
- **THEN** the helper derives that fallback path under `/repo/app/.houmao/`
- **AND THEN** it does not derive a sibling path such as `/repo/app/.agentsys-headless-turns`

#### Scenario: Maintained demo-generated agent tree uses `.houmao`
- **WHEN** a maintained demo run generates a run-local working tree under `/tmp/demo-run/workdir`
- **THEN** the generated agent-definition tree is derived under `/tmp/demo-run/workdir/.houmao/agents`
- **AND THEN** the maintained workflow does not generate `/tmp/demo-run/workdir/.agentsys/agents`

### Requirement: Houmao-owned directories are split into fixed responsibility zones
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different responsibilities while making the active project overlay the default local root for non-registry state.

The default per-user shared Houmao root that remains global SHALL be:
- registry root: `~/.houmao/registry`

For maintained local project-aware command flows, the default overlay-owned roots SHALL be:
- runtime root: `<active-overlay>/runtime`
- mailbox root: `<active-overlay>/mailbox`
- agent memory root family: `<active-overlay>/memory/agents/<agent-id>/`
- easy root: `<active-overlay>/easy`

For each tmux-backed managed agent, the default managed memory paths SHALL be derived as:
- memo file: `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- pages directory: `<active-overlay>/memory/agents/<agent-id>/pages/`

The system SHALL NOT derive current managed-agent memory paths from `<active-overlay>/jobs/<session-id>/`.

The system SHALL continue to support stronger override surfaces for global registry, runtime, and mailbox locations where supported.

When both an explicit CLI/config override and an env-var override exist for the same effective location, the explicit override SHALL win.
When no explicit override exists but a supported env-var override is set, the env-var override SHALL win.
When neither explicit override nor env-var override is supplied for a maintained local project-aware flow, the system SHALL use the overlay-derived defaults above.

#### Scenario: Project-aware local roots resolve managed memory under the active overlay
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** a maintained local Houmao launch flow starts managed agent id `researcher-id` without stronger root overrides
- **THEN** the effective runtime root is `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root is `/repo/.houmao/mailbox`
- **AND THEN** the effective memo file is `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the effective pages directory is `/repo/.houmao/memory/agents/researcher-id/pages`

#### Scenario: Shared registry remains under the user home by default
- **WHEN** an operator runs maintained local Houmao commands in project context without a registry override
- **THEN** the effective shared registry root remains under `~/.houmao/registry`
- **AND THEN** the command does not relocate the registry under the active project overlay by default

#### Scenario: Custom project agent-definition path does not change the fixed overlay-owned runtime family
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** `/repo/.houmao/houmao-config.toml` sets `paths.agent_def_dir = "custom-agents"`
- **AND WHEN** a maintained local Houmao launch flow starts managed agent id `researcher-id` without stronger root overrides
- **THEN** the effective runtime root remains `/repo/.houmao/runtime`
- **AND THEN** the effective mailbox root, memory root family, and easy root remain `/repo/.houmao/mailbox`, `/repo/.houmao/memory/agents/researcher-id`, and `/repo/.houmao/easy`

### Requirement: Houmao-owned directory layout does not require family-based agent bucketing
The system SHALL NOT require Houmao-owned directory hierarchy to encode agent grouping through tool names, family names, or other taxonomy buckets in order to associate runtime-owned state with one agent.

When association is needed, the system SHALL rely on persisted metadata and explicit identity surfaces such as canonical agent name, authoritative `agent_id`, persisted session metadata, or registry publication rather than on bucket names in the directory hierarchy.

This requirement does not forbid future metadata indexes or sidecar metadata files, but this change SHALL NOT require them.

Whenever a Houmao-owned directory name is intended to stand for one agent rather than one session or service instance, the system SHALL use authoritative `agent_id` as that directory name instead of canonical agent name.

#### Scenario: Generated Houmao-owned paths stay flat without tool-family buckets
- **WHEN** the system creates Houmao-owned build or runtime paths for one agent
- **THEN** those paths do not need an intermediate tool-family or agent-family bucket solely to establish association
- **AND THEN** association can instead be recovered from persisted metadata and existing identity surfaces

#### Scenario: Agent-keyed directory names use agent id rather than canonical agent name
- **WHEN** the system needs a Houmao-owned directory whose name stands for one agent
- **THEN** that directory name uses the agent's authoritative `agent_id`
- **AND THEN** the canonical agent name remains persisted in metadata rather than used as the writable directory key

### Requirement: Canonical agent name is a strong human-facing label and `agent_id` is the authoritative global identity
Canonical agent name SHALL use the `HOUMAO-<name>` prefix family as the strong human-facing label for system-owned agents, while `agent_id` remains the authoritative global identity.

When the system bootstraps an initial `agent_id` from canonical agent name, it SHALL use the full lowercase `md5("HOUMAO-<name>").hexdigest()` value.

#### Scenario: Agent-id bootstrap hashes the HOUMAO canonical name
- **WHEN** canonical agent name `HOUMAO-chris` is used for a new agent without an explicit or previously persisted `agent_id`
- **THEN** the system bootstraps the initial authoritative id as the full lowercase `md5("HOUMAO-chris").hexdigest()`

#### Scenario: Name-based lookup reflects the HOUMAO canonical label
- **WHEN** two different agents both use canonical agent name `HOUMAO-chris`
- **THEN** name-based lookup for `HOUMAO-chris` may require disambiguation by `agent_id` or another persisted metadata surface

### Requirement: Managed memory pages remain distinct from artifacts, runtime, and mailbox state
The system SHALL preserve distinct mutability and ownership boundaries across the Houmao-owned zones.

At minimum:
- the registry root SHALL contain discovery-oriented metadata only,
- the runtime root SHALL contain durable Houmao-managed runtime and launcher state,
- the mailbox root SHALL contain shared mailbox transport state,
- the per-agent memory memo file SHALL contain caller-authored Markdown notes,
- the per-agent memory pages directory SHALL contain small contained Markdown pages and related text context selected by users or LLMs.

Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox contents MUST NOT be relocated into the shared registry root as part of this directory model.

Mailbox state MUST remain independently relocatable and MUST NOT be implicitly nested under the runtime root or a per-agent memory pages directory just because those other zones exist.

Managed memory pages MUST NOT be treated as the default scratch ledger, build output location, or durable artifact repository for arbitrary work products; such artifacts belong in the launched workdir or explicit operator-designated paths.

#### Scenario: Registry root is not used as mutable CAO or runtime storage
- **WHEN** the system publishes live-agent discovery metadata and also starts a launcher-managed CAO service
- **THEN** the shared registry contains only registry-owned discovery records
- **AND THEN** launcher-managed CAO home state and durable runtime session state are stored outside the registry root

#### Scenario: Memory pages do not replace shared mailbox or durable runtime state
- **WHEN** a started session writes task artifacts while also using mailbox support and runtime-managed manifest persistence
- **THEN** task artifacts live in the launched workdir or another operator-designated path
- **AND THEN** mailbox content and durable runtime session state remain in their own independent zones

#### Scenario: Memo file stays separate from page content
- **WHEN** a loop initialization records live-agent rules for managed agent `researcher`
- **THEN** concise rules may live in `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** larger readable context may live under `/repo/.houmao/memory/agents/researcher-id/pages/`
- **AND THEN** large task artifacts remain outside managed memory unless the operator explicitly chooses a small page summary or pointer

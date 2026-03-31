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
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different default locations and responsibilities.

The default per-user Houmao roots SHALL be:
- registry root: `~/.houmao/registry`
- runtime root: `~/.houmao/runtime`
- mailbox root: `~/.houmao/mailbox`

For each started session, the default per-agent job dir SHALL be derived under the selected working directory as `<working-directory>/.houmao/jobs/<session-id>/`.

The system SHALL support env-var overrides for those default locations using:
- `HOUMAO_GLOBAL_REGISTRY_DIR` for the effective registry root
- `HOUMAO_GLOBAL_RUNTIME_DIR` for the effective runtime root
- `HOUMAO_GLOBAL_MAILBOX_DIR` for the effective Houmao mailbox root
- `HOUMAO_LOCAL_JOBS_DIR` as a per-launch or per-agent override for the directory under which that session's job dir is derived as `<local-jobs-dir>/<session-id>/`

#### Scenario: Env-var override relocates the runtime root
- **WHEN** `HOUMAO_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** no explicit runtime-root override is supplied
- **THEN** the effective Houmao runtime root is `/tmp/houmao-runtime`

#### Scenario: Local-jobs-dir env-var override relocates per-session job dirs
- **WHEN** `HOUMAO_LOCAL_JOBS_DIR` is set to `/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a session whose generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the effective job dir for that session is `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`

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

### Requirement: Houmao-owned zones keep discovery, durable state, shared mailbox state, and destructive scratch separate
The system SHALL preserve distinct mutability and ownership boundaries across the Houmao-owned zones.

At minimum:
- the registry root SHALL contain discovery-oriented metadata only,
- the runtime root SHALL contain durable Houmao-managed runtime and launcher state,
- the mailbox root SHALL contain shared mailbox transport state,
- the per-agent job dir SHALL contain session-local logs, outputs, temporary files, and destructive scratch work for one started session.

Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox contents MUST NOT be relocated into the shared registry root as part of this directory model.

Mailbox state MUST remain independently relocatable and MUST NOT be implicitly nested under the runtime root or a per-agent job dir just because those other zones exist.

#### Scenario: Registry root is not used as mutable CAO or runtime storage
- **WHEN** the system publishes live-agent discovery metadata and also starts a launcher-managed CAO service
- **THEN** the shared registry contains only registry-owned discovery records
- **AND THEN** launcher-managed CAO home state and durable runtime session state are stored outside the registry root

#### Scenario: Job dir does not replace shared mailbox or durable runtime state
- **WHEN** a started session writes session-local scratch files while also using mailbox support and runtime-managed manifest persistence
- **THEN** scratch files and temporary outputs live under that session's per-agent job dir
- **AND THEN** mailbox content and durable runtime session state remain in their own independent zones

### Requirement: Workspace-local scratch behavior is manual-cleanup and documentation-guided in this change
For this change, the system SHALL treat workspace-local job dirs as manually managed scratch space rather than auto-cleaned runtime state.

The system SHALL NOT require auto-generated `.gitignore` files under workspace-local `.houmao/` directories as part of this change.

Reference docs for this change SHALL recommend ignoring `.houmao/` or `.houmao/jobs/` when the default workspace-local job-dir layout is used.

#### Scenario: Stop-session leaves the job dir in place
- **WHEN** a developer stops a session that used a workspace-local job dir under `.houmao/jobs/`
- **THEN** the runtime leaves that job dir in place in this version
- **AND THEN** any cleanup of that scratch directory remains a manual operator action


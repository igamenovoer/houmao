## ADDED Requirements

### Requirement: Houmao-owned directories are split into fixed responsibility zones
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different default locations and responsibilities.

The default per-user Houmao roots SHALL be:
- registry root: `~/.houmao/registry`
- runtime root: `~/.houmao/runtime`
- mailbox root: `~/.houmao/mailbox`

For each started session, the default per-agent job dir SHALL be derived under the selected working directory as:
- `<working-directory>/.houmao/jobs/<session-id>/`

The system SHALL support env-var overrides for those default locations using:
- `AGENTSYS_GLOBAL_REGISTRY_DIR` for the effective registry root
- `AGENTSYS_GLOBAL_RUNTIME_DIR` for the effective runtime root
- `AGENTSYS_GLOBAL_MAILBOX_DIR` for the effective Houmao mailbox root
- `AGENTSYS_LOCAL_JOBS_DIR` for the directory under which per-session job dirs are derived as `<local-jobs-dir>/<session-id>/`

Subsystem-specific explicit CLI or config overrides that already exist MAY continue to relocate the effective registry root, runtime root, launcher home, or mailbox root.

When both an explicit CLI/config override and an env-var override exist for the same effective location, the explicit override SHALL win.
When no explicit override exists but a supported env-var override is set, the env-var override SHALL win.
When neither explicit override nor env-var override is supplied, the system SHALL use the defaults above.

#### Scenario: Default Houmao roots resolve under the user home
- **WHEN** a developer starts new Houmao-managed runtime or mailbox work without explicit root overrides
- **THEN** the system resolves the default registry, runtime, and mailbox roots under `~/.houmao/`

#### Scenario: Job dir is derived from working directory and session id
- **WHEN** the runtime starts a session with working directory `/repo/app` and generated session id `session-20260314-120000Z-abcd1234`
- **THEN** the default per-agent job dir for that session is `/repo/app/.houmao/jobs/session-20260314-120000Z-abcd1234/`

#### Scenario: Env-var override relocates the runtime root
- **WHEN** `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** no explicit runtime-root override is supplied
- **THEN** the effective Houmao runtime root is `/tmp/houmao-runtime`

#### Scenario: Local-jobs-dir env-var override relocates per-session job dirs
- **WHEN** `AGENTSYS_LOCAL_JOBS_DIR` is set to `/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a session whose generated session id is `session-20260314-120000Z-abcd1234`
- **AND WHEN** no more specific explicit job-dir override exists
- **THEN** the effective job dir for that session is `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`

### Requirement: Houmao-owned directory layout does not require family-based agent bucketing
The system SHALL NOT require Houmao-owned directory hierarchy to encode agent grouping through tool names, family names, or other taxonomy buckets in order to associate runtime-owned state with one agent.

When association is needed, the system SHALL rely on persisted metadata and strong identity surfaces such as canonical agent name, authoritative `agent_id`, persisted session metadata, or registry publication rather than on bucket names in the directory hierarchy.

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

### Requirement: Canonical agent name is the strong live identity and `agent_id` is the authoritative global identity
The system SHALL treat canonical agent name as the strong human-facing live identity for normal operator use. Reusing the same canonical agent name is expected to refer to the same agent most of the time.

The system SHALL also assign each agent an authoritative `agent_id` that is globally unique by contract.

When no explicit `agent_id` is supplied, the default `agent_id` SHALL be the full lowercase `md5(canonical agent name).hexdigest()`.

When system-owned writable association needs one stable key, the system SHALL treat `agent_id` as authoritative even if a user intentionally or accidentally pairs that same `agent_id` with a different canonical agent name.

When the system encounters a different canonical agent name already associated with the same `agent_id`, it SHALL emit a warning before continuing with that authoritative `agent_id`.

#### Scenario: Same canonical agent name derives the same default agent id
- **WHEN** canonical agent name `AGENTSYS-chris` is used without an explicit `agent_id`
- **THEN** the system derives the default authoritative id as the full lowercase `md5("AGENTSYS-chris").hexdigest()`
- **AND THEN** later reuse of that same canonical agent name derives the same default `agent_id`

#### Scenario: Different canonical names sharing one explicit agent id trigger a warning
- **WHEN** the system already has writable association metadata for `agent_id=abc123` with canonical agent name `AGENTSYS-chris`
- **AND WHEN** a later start or publication explicitly reuses `agent_id=abc123` with canonical agent name `AGENTSYS-alex`
- **THEN** the system emits a warning that different canonical names are sharing one authoritative `agent_id`
- **AND THEN** it still treats `agent_id=abc123` as the authoritative association key for system-owned writable state

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

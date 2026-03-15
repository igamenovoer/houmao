## ADDED Requirements

### Requirement: Runtime defaults new build and session state to the Houmao runtime root
When the caller does not provide an explicit runtime-root override, the runtime SHALL default new Houmao-managed build and session state to `~/.houmao/runtime`.

When no explicit runtime-root override is supplied and `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to an absolute directory path, the runtime SHALL use that env-var value as the effective runtime root instead of the built-in default.

At minimum, this default SHALL apply to:
- generated brain homes under `~/.houmao/runtime/homes/<home-id>/`,
- generated manifests under `~/.houmao/runtime/manifests/<home-id>.yaml`,
- runtime-owned session roots for started sessions,
- other durable runtime-owned session artifacts that are derived from the effective runtime root.

Explicit runtime-root overrides SHALL continue to take precedence over the default.

The default build-state layout SHALL NOT require tool- or family-based directory bucketing in order to associate a generated home or manifest with an agent.

When the runtime needs to associate that flat build or session state with one agent, it SHALL rely on persisted canonical agent name, authoritative `agent_id`, persisted terminal metadata, and other explicit runtime metadata rather than on bucket names in the directory hierarchy.

Whenever runtime-owned directory naming needs one path component that stands for one agent rather than one session, backend, or service instance, the runtime SHALL use authoritative `agent_id` for that directory name instead of canonical agent name.

#### Scenario: Build flow defaults generated homes and manifests to the Houmao runtime root
- **WHEN** a developer runs a build flow without an explicit runtime-root override
- **THEN** the generated brain home and manifest are written under `~/.houmao/runtime`

#### Scenario: Build flow does not require tool-family buckets in the default layout
- **WHEN** a developer runs a build flow without an explicit runtime-root override
- **THEN** the generated home path is rooted under `~/.houmao/runtime/homes/<home-id>/`
- **AND THEN** the generated manifest path is rooted under `~/.houmao/runtime/manifests/<home-id>.yaml`
- **AND THEN** those default paths do not require an intermediate tool- or family-grouping bucket

#### Scenario: Start-session defaults durable session state to the Houmao runtime root
- **WHEN** a developer starts a runtime-owned session without an explicit runtime-root override
- **THEN** the session manifest and other durable runtime-owned session artifacts are rooted under `~/.houmao/runtime`

#### Scenario: Runtime-root env-var override redirects durable runtime state
- **WHEN** `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** a developer starts a runtime-owned session without an explicit runtime-root override
- **THEN** the session manifest and other durable runtime-owned session artifacts are rooted under `/tmp/houmao-runtime`

### Requirement: Runtime materializes canonical agent name and authoritative `agent_id` for system-owned association
For runtime-owned sessions, the runtime SHALL persist canonical agent name as a strong human-facing metadata field for normal operator use, but it SHALL NOT treat canonical agent name as the authoritative writable-state key.

The runtime SHALL materialize an authoritative `agent_id` in persisted runtime-owned metadata and in any shared-registry publication derived from that session, and that `agent_id` SHALL replace registry-specific `agent_key` for cross-module identity association.

The session-manifest schema for this change SHALL bump to the next version and SHALL expose canonical agent name and authoritative `agent_id` as first-class top-level manifest fields rather than burying them inside `backend_state`.

When the caller does not provide an explicit `agent_id`, the runtime SHALL first reuse a previously persisted `agent_id` for the same built or resumed agent when one exists in manifest metadata, build metadata, or equivalent runtime-owned metadata.

Only when no explicit `agent_id` and no previously persisted `agent_id` exist SHALL the runtime bootstrap the initial `agent_id` as the full lowercase `md5(canonical agent name).hexdigest()`.

When runtime-controlled start, resume, or publication logic encounters an existing association for the same `agent_id` but a different canonical agent name, the runtime SHALL emit a warning and continue treating that `agent_id` as authoritative for system-owned writable association.

When runtime-controlled lookup encounters more than one live or persisted association for the same canonical agent name but different authoritative `agent_id` values, the runtime SHALL surface ambiguity rather than silently treating those associations as one agent.

#### Scenario: Start-session bootstraps a default agent id from the canonical agent name when no persisted id exists
- **WHEN** a developer starts a runtime-owned session with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the caller does not provide an explicit `agent_id`
- **AND WHEN** no previously persisted `agent_id` exists for that same built or resumed agent
- **THEN** the runtime materializes the full lowercase `md5("AGENTSYS-gpu").hexdigest()` value as the session's initial authoritative `agent_id`
- **AND THEN** persisted runtime-owned metadata for that session records both the canonical agent name and the bootstrapped `agent_id`

#### Scenario: Start-session reuses a previously persisted agent id
- **WHEN** a developer starts or resumes a runtime-owned session for an agent whose existing persisted metadata already carries `agent_id=abc123`
- **AND WHEN** the caller does not provide an explicit replacement `agent_id`
- **THEN** the runtime reuses `agent_id=abc123`
- **AND THEN** it does not silently replace that authoritative identity by recomputing from the current canonical agent name

#### Scenario: Agent-keyed runtime-owned directories use agent id rather than canonical agent name
- **WHEN** runtime-owned directory derivation needs one path component that stands for one agent
- **THEN** the runtime uses that agent's authoritative `agent_id` for the directory name
- **AND THEN** canonical agent name remains an operator-facing metadata field rather than the writable directory key

#### Scenario: Explicit agent id reused with a different canonical name triggers a warning
- **WHEN** runtime-owned metadata or shared-registry publication already associates `agent_id=abc123` with canonical agent name `AGENTSYS-gpu`
- **AND WHEN** a later runtime-controlled start or publication explicitly uses `agent_id=abc123` with canonical agent name `AGENTSYS-editor`
- **THEN** the runtime emits a warning about the different-name same-id association
- **AND THEN** the runtime still treats `agent_id=abc123` as the authoritative writable-state identity

#### Scenario: Same canonical name with different agent ids is reported as ambiguous
- **WHEN** runtime-controlled lookup sees more than one live or persisted session metadata surface for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** those metadata surfaces carry different authoritative ids such as `agent_id=abc123` and `agent_id=def456`
- **THEN** the runtime reports that canonical-name lookup is ambiguous
- **AND THEN** it requires disambiguation by `agent_id`, manifest path, or another explicit metadata surface

### Requirement: Tmux session names are unique live-session handles rather than authoritative agent names
For tmux-backed runtime sessions, the runtime SHALL treat the tmux session name as a unique handle for one live session rather than as the source of truth for canonical agent name or authoritative `agent_id`.

The runtime SHALL choose and persist the tmux session name explicitly for each started tmux-backed session rather than relying on tmux collision auto-renaming as an identity mechanism.

Persisted runtime metadata for a tmux-backed session SHALL record at minimum:
- canonical agent name,
- authoritative `agent_id`,
- the actual tmux session name used for that live session.

The session-manifest schema for this change SHALL also expose that actual tmux session name as a first-class top-level manifest field rather than only as backend-specific state.

When runtime-controlled logic needs to recover the true canonical agent name or authoritative `agent_id` for a tmux-backed live session, it SHALL read persisted manifest metadata or shared-registry publication rather than inferring that identity from the tmux session name alone.

#### Scenario: Tmux-backed start persists the actual tmux session name separately from canonical agent name
- **WHEN** the runtime starts a tmux-backed session for canonical agent name `AGENTSYS-gpu`
- **AND WHEN** the runtime chooses live tmux session name `houmao-session-abc123`
- **THEN** persisted runtime metadata records canonical agent name `AGENTSYS-gpu`
- **AND THEN** that same metadata also records tmux session name `houmao-session-abc123` as a distinct live-session handle

#### Scenario: Runtime learns true agent identity from manifest or registry rather than from tmux session name
- **WHEN** runtime-controlled logic needs to inspect tmux-backed live session `houmao-session-abc123`
- **THEN** it reads persisted manifest metadata or shared-registry publication to recover canonical agent name and authoritative `agent_id`
- **AND THEN** it does not assume the tmux session name itself equals the canonical agent name

### Requirement: Runtime creates and reuses a per-agent job dir for each started session
For each runtime-owned started session, the runtime SHALL derive a per-agent job dir at `<working-directory>/.houmao/jobs/<session-id>/`.

When no explicit job-dir override is supplied and `AGENTSYS_LOCAL_JOBS_DIR` is set to an absolute directory path for that launch or started agent, the runtime SHALL derive the effective per-agent job dir as:
- `<AGENTSYS_LOCAL_JOBS_DIR>/<session-id>/`

The runtime SHALL create that directory before the session needs runtime-managed scratch space and SHALL expose its absolute path to the launched session through `AGENTSYS_JOB_DIR`.

The per-agent job dir SHALL be intended for session-local logs, temporary outputs, and destructive scratch work, and SHALL NOT replace the durable runtime-owned session root under the effective runtime root.

Resume and later runtime-controlled work for the same persisted session SHALL continue to use the same derived per-agent job dir rather than allocating a replacement directory for that same session id.

For this change, runtime-controlled stop behavior SHALL NOT automatically remove the job dir.

#### Scenario: Start-session creates the job dir and publishes its binding
- **WHEN** a developer starts a runtime-owned session with working directory `/repo/app`
- **AND WHEN** the generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the runtime creates `/repo/app/.houmao/jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the started session environment includes `AGENTSYS_JOB_DIR` pointing to that absolute path

#### Scenario: Resume reuses the same job dir for the same session
- **WHEN** the runtime resumes control of a previously started session whose working directory and session id already determine one per-agent job dir
- **THEN** resumed runtime-controlled work continues to use that same per-agent job dir
- **AND THEN** the runtime does not allocate a different destructive-scratch directory for that same logical session

#### Scenario: Local-jobs-dir env-var override relocates the effective job dir
- **WHEN** `AGENTSYS_LOCAL_JOBS_DIR` is set to `/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a runtime-owned session whose generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the runtime creates `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the started session environment includes `AGENTSYS_JOB_DIR` pointing to that absolute path

#### Scenario: Stop-session does not auto-clean the job dir in this version
- **WHEN** a runtime-owned session has created a job dir for one session id
- **AND WHEN** a developer later stops that session through runtime-controlled stop behavior
- **THEN** the runtime leaves the job dir in place in this version
- **AND THEN** later cleanup of that scratch directory remains manual

## MODIFIED Requirements

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
When filesystem mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under a reserved runtime-owned namespace and SHALL populate the filesystem mailbox binding env contract before mailbox-related work is expected from the agent.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

When no explicit filesystem mailbox content root override is supplied and `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before publishing `AGENTSYS_MAILBOX_FS_ROOT`.

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the active session skill destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to the effective mailbox content root for that session

#### Scenario: Start session defaults filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived default path

#### Scenario: Mailbox-root env-var override redirects the effective mailbox root
- **WHEN** `AGENTSYS_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived path

## ADDED Requirements

### Requirement: Runtime defaults new build and session state to the Houmao runtime root
When the caller does not provide an explicit runtime-root override, the runtime SHALL default new Houmao-managed build and session state to `~/.houmao/runtime`.

At minimum, this default SHALL apply to:
- generated brain homes and manifests for build flows,
- runtime-owned session roots for started sessions,
- other durable runtime-owned session artifacts that are derived from the effective runtime root.

Explicit runtime-root overrides SHALL continue to take precedence over the default.

#### Scenario: Build flow defaults generated homes and manifests to the Houmao runtime root
- **WHEN** a developer runs a build flow without an explicit runtime-root override
- **THEN** the generated brain home and manifest are written under `~/.houmao/runtime`

#### Scenario: Start-session defaults durable session state to the Houmao runtime root
- **WHEN** a developer starts a runtime-owned session without an explicit runtime-root override
- **THEN** the session manifest and other durable runtime-owned session artifacts are rooted under `~/.houmao/runtime`

### Requirement: Runtime creates and reuses a per-agent job dir for each started session
For each runtime-owned started session, the runtime SHALL derive a per-agent job dir at `<working-directory>/.houmao/jobs/<session-id>/`.

The runtime SHALL create that directory before the session needs runtime-managed scratch space and SHALL expose its absolute path to the launched session through `AGENTSYS_JOB_DIR`.

The per-agent job dir SHALL be intended for session-local logs, temporary outputs, and destructive scratch work, and SHALL NOT replace the durable runtime-owned session root under the effective runtime root.

Resume and later runtime-controlled work for the same persisted session SHALL continue to use the same derived per-agent job dir rather than allocating a replacement directory for that same session id.

#### Scenario: Start-session creates the job dir and publishes its binding
- **WHEN** a developer starts a runtime-owned session with working directory `/repo/app`
- **AND WHEN** the generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the runtime creates `/repo/app/.houmao/jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the started session environment includes `AGENTSYS_JOB_DIR` pointing to that absolute path

#### Scenario: Resume reuses the same job dir for the same session
- **WHEN** the runtime resumes control of a previously started session whose working directory and session id already determine one per-agent job dir
- **THEN** resumed runtime-controlled work continues to use that same per-agent job dir
- **AND THEN** the runtime does not allocate a different destructive-scratch directory for that same logical session

## MODIFIED Requirements

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
When filesystem mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under a reserved runtime-owned namespace and SHALL populate the filesystem mailbox binding env contract before mailbox-related work is expected from the agent.

When no explicit filesystem mailbox content root override is supplied, the runtime SHALL derive the effective filesystem mailbox content root from the independent Houmao mailbox root rather than from the effective runtime root.

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the active session skill destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to the effective mailbox content root for that session

#### Scenario: Start session defaults filesystem mailbox root from the Houmao mailbox root
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled and no explicit filesystem mailbox content root override
- **THEN** the runtime derives the effective filesystem mailbox content root from the Houmao mailbox root default
- **AND THEN** the runtime sets `AGENTSYS_MAILBOX_FS_ROOT` to that derived default path

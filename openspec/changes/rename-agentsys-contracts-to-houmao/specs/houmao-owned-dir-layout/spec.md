## MODIFIED Requirements

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

### Requirement: Canonical agent name is a strong human-facing label and `agent_id` is the authoritative global identity
Canonical agent name SHALL use the `HOUMAO-<name>` prefix family as the strong human-facing label for system-owned agents, while `agent_id` remains the authoritative global identity.

When the system bootstraps an initial `agent_id` from canonical agent name, it SHALL use the full lowercase `md5("HOUMAO-<name>").hexdigest()` value.

#### Scenario: Agent-id bootstrap hashes the HOUMAO canonical name
- **WHEN** canonical agent name `HOUMAO-chris` is used for a new agent without an explicit or previously persisted `agent_id`
- **THEN** the system bootstraps the initial authoritative id as the full lowercase `md5("HOUMAO-chris").hexdigest()`

#### Scenario: Name-based lookup reflects the HOUMAO canonical label
- **WHEN** two different agents both use canonical agent name `HOUMAO-chris`
- **THEN** name-based lookup for `HOUMAO-chris` may require disambiguation by `agent_id` or another persisted metadata surface


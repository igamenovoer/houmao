## ADDED Requirements

### Requirement: Cleanup commands support structured dry-run planning
Every `houmao-mgr` cleanup command introduced by this capability SHALL accept `--dry-run`.

When `--dry-run` is present, the command SHALL classify candidate artifacts, preserved artifacts, and blocked deletions using the same resolution and safety rules as ordinary execution, but it SHALL NOT delete or mutate any filesystem state.

Cleanup results for both dry-run and execute modes SHALL be structured and SHALL identify the resolved cleanup scope plus the reason for each planned, applied, blocked, or preserved action.

#### Scenario: Operator previews a cleanup plan without deleting anything
- **WHEN** an operator runs a supported cleanup command with `--dry-run`
- **THEN** the command returns a structured result that includes planned actions, blocked actions, and preserved artifacts
- **AND THEN** the command does not delete, rename, or mutate any candidate artifact during that run

### Requirement: `houmao-mgr admin cleanup runtime` exposes host-scoped runtime janitors
`houmao-mgr` SHALL expose a local `admin cleanup runtime` command family for cleanup work rooted under the effective runtime root.

At minimum, that family SHALL include:

- `sessions`
- `builds`
- `logs`
- `mailbox-credentials`

These commands SHALL operate on local Houmao-owned runtime state and SHALL NOT require a running pair authority.

#### Scenario: Operator sees host-scoped runtime cleanup commands
- **WHEN** an operator runs `houmao-mgr admin cleanup runtime --help`
- **THEN** the help output lists `sessions`, `builds`, `logs`, and `mailbox-credentials`
- **AND THEN** the command family is presented as local runtime maintenance rather than a server-backed admin API

### Requirement: `houmao-mgr agents cleanup` resolves one local managed session from explicit or current-session authority
`houmao-mgr` SHALL expose a local `agents cleanup` command family for cleanup work that targets one managed-agent session envelope.

At minimum, that family SHALL include:

- `session`
- `logs`
- `mailbox`

Each `agents cleanup` command SHALL accept one cleanup authority from:

- `--agent-id <id>`
- `--agent-name <name>`
- `--manifest-path <path>`
- `--session-root <path>`

When none of those are provided and the command is run inside the owning tmux session, the command SHALL resolve the target through current-session metadata by:

1. preferring `AGENTSYS_MANIFEST_PATH`,
2. otherwise falling back to `AGENTSYS_AGENT_ID` plus exactly one fresh shared-registry record,
3. validating that the resolved manifest belongs to the current tmux session.

These commands SHALL remain local-only maintenance commands and SHALL NOT accept `--port`.

#### Scenario: Current-session cleanup resolves through tmux-published manifest authority
- **WHEN** an operator runs `houmao-mgr agents cleanup session` from inside a managed tmux session
- **AND WHEN** that tmux session publishes a valid `AGENTSYS_MANIFEST_PATH`
- **THEN** `houmao-mgr` resolves the cleanup target from that manifest
- **AND THEN** the operator does not need to pass an explicit selector or path

#### Scenario: Current-session cleanup falls back through shared registry when manifest metadata is stale
- **WHEN** an operator runs `houmao-mgr agents cleanup logs` from inside a managed tmux session
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing, blank, or stale in that session
- **AND WHEN** `AGENTSYS_AGENT_ID` resolves exactly one fresh shared-registry record
- **THEN** `houmao-mgr` resolves the cleanup target from that record's `runtime.manifest_path`
- **AND THEN** it still validates that the resolved manifest belongs to the current tmux session before cleaning anything

#### Scenario: Explicit manifest path remains valid after the live registry is gone
- **WHEN** an operator runs `houmao-mgr agents cleanup session --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND WHEN** the managed session has already been stopped and no fresh registry record remains
- **THEN** `houmao-mgr` uses that manifest as the cleanup authority
- **AND THEN** the command does not require the session to remain live just to address its artifacts

### Requirement: `houmao-mgr agents cleanup session` removes stopped session envelopes and optionally the job dir
For one resolved local managed session, `houmao-mgr agents cleanup session` SHALL classify the runtime-owned session root as removable only when the resolved session no longer appears live on the local host.

When the operator requests `--include-job-dir`, the command SHALL also classify the manifest-persisted `job_dir` for removal as part of the same cleanup result.

The command SHALL block removal when the resolved session still appears live rather than deleting the active session envelope.

#### Scenario: Stopped session cleanup removes the session root and requested job dir
- **WHEN** an operator runs `houmao-mgr agents cleanup session --manifest-path /abs/path/runtime/sessions/local_interactive/session-1/manifest.json --include-job-dir`
- **AND WHEN** the resolved session no longer appears live on the local host
- **THEN** the cleanup result removes the session root
- **AND THEN** it also removes the manifest-persisted `job_dir`

#### Scenario: Live session cleanup is blocked
- **WHEN** an operator runs `houmao-mgr agents cleanup session --agent-id abc123`
- **AND WHEN** the resolved managed session still appears live on the local host
- **THEN** the cleanup result reports that session-root removal is blocked
- **AND THEN** the command does not delete the live session envelope

### Requirement: `houmao-mgr admin cleanup runtime builds` removes only unreferenced build artifacts
`houmao-mgr admin cleanup runtime builds` SHALL evaluate build artifacts under the effective runtime root by pairing generated brain manifests with their referenced runtime homes.

The command SHALL classify a build-manifest/runtime-home pair as removable only when no preserved runtime session manifest still references that build manifest.

The command MAY also classify broken half-pairs as removable when the manifest or home counterpart is missing.

#### Scenario: Unreferenced build pair is removable
- **WHEN** a generated brain manifest and its runtime home exist under the effective runtime root
- **AND WHEN** no preserved runtime session manifest still references that brain manifest
- **THEN** `houmao-mgr admin cleanup runtime builds` classifies that manifest-home pair as removable
- **AND THEN** the cleanup result does not treat the pair as protected durable state

#### Scenario: Referenced build pair is preserved
- **WHEN** a generated brain manifest and runtime home still exist under the effective runtime root
- **AND WHEN** a preserved runtime session manifest still references that brain manifest
- **THEN** `houmao-mgr admin cleanup runtime builds` preserves that manifest-home pair
- **AND THEN** the cleanup result identifies the pair as referenced rather than stale

### Requirement: Runtime log cleanup excludes durable gateway and manifest state
`houmao-mgr admin cleanup runtime logs` and `houmao-mgr agents cleanup logs` SHALL remove only log-style or ephemeral runtime artifacts.

At minimum, runtime log cleanup MAY target:

- gateway running logs,
- gateway run-directory live-instance files,
- inactive server-root log files,
- inactive server-root run-instance files.

Runtime log cleanup SHALL NOT treat these artifacts as disposable log output in this change:

- `manifest.json`
- `gateway/queue.sqlite`
- `gateway/events.jsonl`
- `gateway/state.json`

#### Scenario: Log cleanup preserves durable gateway state
- **WHEN** an operator runs a supported runtime log cleanup command
- **THEN** the command may remove human-oriented log files and ephemeral live-instance files
- **AND THEN** it preserves durable gateway artifacts such as `queue.sqlite`, `events.jsonl`, `state.json`, and `manifest.json`

### Requirement: Runtime mailbox credential cleanup removes only unreferenced credential refs
`houmao-mgr admin cleanup runtime mailbox-credentials` SHALL evaluate runtime-owned Stalwart credential files by `credential_ref`.

The command SHALL classify a credential file as removable only when no preserved runtime session manifest still references that `credential_ref`.

#### Scenario: Referenced credential file is preserved
- **WHEN** a runtime-owned Stalwart credential file exists under the effective runtime root
- **AND WHEN** at least one preserved runtime session manifest still references that file's `credential_ref`
- **THEN** `houmao-mgr admin cleanup runtime mailbox-credentials` preserves that credential file
- **AND THEN** the cleanup result identifies the file as still referenced

#### Scenario: Unreferenced credential file is removable
- **WHEN** a runtime-owned Stalwart credential file exists under the effective runtime root
- **AND WHEN** no preserved runtime session manifest still references that file's `credential_ref`
- **THEN** `houmao-mgr admin cleanup runtime mailbox-credentials` classifies that credential file as removable
- **AND THEN** the cleanup result does not require manual source-code inspection to identify it as stale

### Requirement: `houmao-mgr agents cleanup mailbox` removes only session-local mailbox secret material
`houmao-mgr agents cleanup mailbox` SHALL target mailbox secret material scoped to one resolved managed-agent session.

At minimum, that command SHALL operate on the session-local mailbox secret directory under the resolved session root when mailbox secret material is present there.

The command SHALL NOT treat shared mailbox-root canonical message content or runtime-owned shared credential files as part of this session-scoped cleanup action.

#### Scenario: Session mailbox cleanup removes only session-local secret files
- **WHEN** an operator runs `houmao-mgr agents cleanup mailbox` against one resolved managed-agent session
- **AND WHEN** that session root contains session-local mailbox secret material
- **THEN** the cleanup result targets only that session-local mailbox secret material
- **AND THEN** it does not delete shared mailbox-root canonical message content or runtime-owned shared credential files as part of the same action

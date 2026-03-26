## ADDED Requirements

### Requirement: Passive server headless launch publishes shared-registry state
`POST /houmao/agents/headless/launches` SHALL explicitly publish a `LiveAgentRegistryRecordV2` for the launched headless agent after `start_runtime_session()` succeeds and before the launch is reported as successful.

The published record SHALL make the new agent discoverable to later passive-server routes and other registry consumers.

#### Scenario: Successful launch becomes discoverable
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with valid launch inputs
- **THEN** the response status code is 200
- **AND THEN** a fresh `LiveAgentRegistryRecordV2` exists for the launched agent
- **AND THEN** later passive-server routes can resolve the launched agent by a shared-registry reference

### Requirement: Passive server headless launch validates manifest, role, and mailbox inputs
Before launch, the passive server SHALL validate that `working_directory` is an existing directory, `agent_def_dir` is an existing directory, `brain_manifest_path` is an existing file, and `tool` matches the manifest `inputs.tool`.

If `role_name` is present, the passive server SHALL validate that the role exists before attempting launch.

If mailbox options are present, the passive server SHALL forward the full mailbox configuration needed by the selected transport, including Stalwart-specific fields.

#### Scenario: Tool mismatch returns client validation error
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` where `tool` does not match the manifest `inputs.tool`
- **THEN** the response status code is 422

#### Scenario: Invalid role returns client validation error
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a `role_name` that does not exist under the resolved agent definition directory
- **THEN** the response status code is 422

#### Scenario: Stalwart mailbox options are forwarded during launch
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with `mailbox.transport = "stalwart"` and the related Stalwart connection fields
- **THEN** the passive server passes those Stalwart mailbox fields into the runtime launch call

### Requirement: Passive server rebuild resumes live managed headless controllers
On startup, the passive server SHALL scan persisted `ManagedHeadlessAuthorityRecord` entries and call `resume_runtime_session()` for each authority whose tmux session is still live.

If resume succeeds, the rebuilt in-memory handle SHALL support turn submission, interrupt, and stop without requiring a relaunch.

If the tmux session is gone or resume fails irrecoverably, the passive server SHALL log the stale authority and clean it up.

#### Scenario: Live managed headless agent is resumable after restart
- **WHEN** the passive server starts and a persisted headless authority has a live tmux session plus a valid manifest
- **THEN** the in-memory handle is rebuilt with a resumable `RuntimeSessionController`
- **AND THEN** `POST /houmao/agents/{agent_ref}/turns` remains available after restart

#### Scenario: Dead or unrecoverable authority is cleaned up
- **WHEN** the passive server starts and a persisted headless authority cannot be resumed because the tmux session is gone or the persisted runtime state is unusable
- **THEN** the passive server logs the failure
- **AND THEN** the stale authority record is removed

### Requirement: Passive server finalizes headless turn records from durable artifact evidence
When a managed headless turn completes, the passive server SHALL refresh the persisted `ManagedHeadlessTurnRecord` from the turn artifact directory and/or the runtime completion payload.

The finalized turn record SHALL include the correct `status`, `completed_at_utc`, `returncode`, `completion_source`, and artifact paths for `stdout` and `stderr` when those files exist.

#### Scenario: Completed turn persists artifact paths
- **WHEN** a managed headless turn completes successfully
- **THEN** the persisted turn record contains `stdout_path` and `stderr_path` when those artifacts were written
- **AND THEN** `GET /houmao/agents/{agent_ref}/turns/{turn_id}` exposes those paths

#### Scenario: Events and artifacts load from finalized record
- **WHEN** a caller later requests `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` or `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
- **THEN** the passive server reads the finalized record and durable artifacts
- **AND THEN** the response does not fail solely because artifact paths were never persisted

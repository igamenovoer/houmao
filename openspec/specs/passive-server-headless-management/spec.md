# passive-server-headless-management Specification

## Purpose
TBD - synced from change passive-server-requests-and-headless. Update Purpose after archive.

## Requirements

### Requirement: Passive server can launch native headless agents
The passive server SHALL expose `POST /houmao/agents/headless/launches` that accepts a launch request and creates a headless agent session.

The request body SHALL include `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and optionally `role_name`, `agent_name`, `agent_id`, and `mailbox` options.

The endpoint SHALL reject invalid launch inputs with HTTP 422, call `start_runtime_session()` to create the headless session, establish the server-managed launch state, and return launch metadata for later managed follow-up operations.

#### Scenario: Successful headless launch
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with valid tool, working_directory, agent_def_dir, and brain_manifest_path
- **THEN** the response status code is 200
- **AND THEN** the response body contains `tracked_agent_id`, `manifest_path`, `session_root`, and `detail`
- **AND THEN** a `ManagedHeadlessAuthorityRecord` is persisted to disk

#### Scenario: Invalid working directory returns 422
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a nonexistent `working_directory`
- **THEN** the response status code is 422
- **AND THEN** the response body explains the validation failure

#### Scenario: Unsupported backend returns 422
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a tool whose resolved backend is not one of `claude_headless`, `codex_headless`, or `gemini_headless`
- **THEN** the response status code is 422

### Requirement: Passive server headless launch publishes shared-registry state
`POST /houmao/agents/headless/launches` SHALL explicitly publish a `LiveAgentRegistryRecordV2` for the launched headless agent after `start_runtime_session()` succeeds and before the launch is reported as successful.

The published record SHALL make the new agent discoverable to later passive-server routes and other registry consumers.

If shared-registry publication fails after the runtime session starts, the passive server SHALL stop the launched session, avoid leaving partial managed state behind, and report the launch as failed instead of returning success.

#### Scenario: Successful launch becomes discoverable
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with valid launch inputs
- **THEN** the response status code is 200
- **AND THEN** a fresh `LiveAgentRegistryRecordV2` exists for the launched agent
- **AND THEN** later passive-server routes can resolve the launched agent by a shared-registry reference

#### Scenario: Publish failure rolls back managed launch
- **WHEN** `start_runtime_session()` succeeds but publishing the `LiveAgentRegistryRecordV2` fails during `POST /houmao/agents/headless/launches`
- **THEN** the passive server stops the launched session
- **AND THEN** no stale managed authority or shared-registry record is left behind
- **AND THEN** the launch request does not return HTTP 200

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

### Requirement: Passive server can submit turns to managed headless agents
The passive server SHALL expose `POST /houmao/agents/{agent_ref}/turns` that accepts a prompt and submits it as a new turn to a managed headless agent.

The request body SHALL include a `prompt` field (non-empty string).

The endpoint SHALL only accept turns for headless agents launched by this server instance. If the agent is not a server-managed headless agent, the endpoint SHALL return HTTP 400.

#### Scenario: Successful turn submission
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/turns` with `{"prompt": "analyze this"}` for a managed headless agent
- **THEN** the response status code is 200
- **AND THEN** the response body contains `tracked_agent_id`, `turn_id`, `turn_index`, `status`, and `detail`

#### Scenario: Non-headless agent returns 400
- **WHEN** a caller sends `POST /houmao/agents/{agent_ref}/turns` for an agent not managed as headless by this server
- **THEN** the response status code is 400

### Requirement: Passive server can query headless turn status
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/turns/{turn_id}` returning the status of a specific turn.

The response SHALL include `tracked_agent_id`, `turn_id`, `turn_index`, `status`, `started_at_utc`, and optionally `completed_at_utc`, `returncode`, `completion_source`, `stdout_path`, `stderr_path`, `error`.

#### Scenario: Active turn returns status
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}` for an active turn
- **THEN** the response status code is 200
- **AND THEN** the `status` field is `"active"`

#### Scenario: Completed turn returns full status
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}` for a completed turn
- **THEN** the response status code is 200
- **AND THEN** the `status` field is `"completed"`
- **AND THEN** `completed_at_utc` and `returncode` are present

#### Scenario: Unknown turn returns 404
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}` for a nonexistent turn
- **THEN** the response status code is 404

### Requirement: Passive server can query headless turn events
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` returning the event log for a specific turn.

Each event SHALL include `kind`, `message`, `turn_index`, `timestamp_utc`, and optionally `payload`.

#### Scenario: Events returned for completed turn
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for a completed turn
- **THEN** the response status code is 200
- **AND THEN** the response body contains an `entries` list with event objects

#### Scenario: Empty events for fresh turn
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events` for a turn that has just started
- **THEN** the response status code is 200
- **AND THEN** the `entries` list may be empty

### Requirement: Passive server can retrieve headless turn artifacts
The passive server SHALL expose `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/{name}` returning the text content of a named artifact.

Supported artifact names SHALL include `stdout` and `stderr`.

The response SHALL use `text/plain` content type.

#### Scenario: Stdout artifact retrieved
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout` for a completed turn
- **THEN** the response status code is 200
- **AND THEN** the response content type is `text/plain`
- **AND THEN** the response body contains the captured stdout text

#### Scenario: Unknown artifact returns 404
- **WHEN** a caller sends `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/unknown` for any turn
- **THEN** the response status code is 404

### Requirement: Passive server rebuilds headless agent handles on restart
On startup, the `HeadlessAgentService` SHALL scan persisted `ManagedHeadlessAuthorityRecord` entries from the `ManagedHeadlessStore`.

For each persisted authority whose tmux session is still live, the service SHALL call `resume_runtime_session()` from the stored manifest and persisted runtime state to rebuild the in-memory handle with a resumable `RuntimeSessionController`.

The rebuilt handle SHALL support turn submission, interrupt, and stop without requiring a relaunch.

For authorities whose tmux sessions are gone or whose persisted runtime state cannot be resumed irrecoverably, the service SHALL log a warning and clean up the stale authority record.

#### Scenario: Live headless agent resumed on restart
- **WHEN** the passive server starts and a persisted authority record has a live tmux session plus a valid manifest
- **THEN** the in-memory handle is rebuilt with a resumable `RuntimeSessionController`
- **AND THEN** the agent is available for turn submission, interrupt, and stop without relaunch

#### Scenario: Dead headless agent cleaned up on restart
- **WHEN** the passive server starts and a persisted authority record has no live tmux session or has unrecoverable persisted runtime state
- **THEN** a warning is logged
- **AND THEN** the stale authority record is cleaned up

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

## ADDED Requirements

### Requirement: Passive server can launch native headless agents
The passive server SHALL expose `POST /houmao/agents/headless/launches` that accepts a launch request and creates a headless agent session.

The request body SHALL include `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and optionally `role_name`, `agent_name`, `agent_id`, and `mailbox` options.

The endpoint SHALL validate that `working_directory` exists and is a directory, `agent_def_dir` exists and is a directory, `brain_manifest_path` exists as a file, and `tool` matches the manifest's `inputs.tool`.

The endpoint SHALL call `start_runtime_session()` to create the headless session, publish a `LiveAgentRegistryRecordV2` to the shared registry, persist a `ManagedHeadlessAuthorityRecord` via `ManagedHeadlessStore`, and store an in-memory handle.

#### Scenario: Successful headless launch
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with valid tool, working_directory, agent_def_dir, and brain_manifest_path
- **THEN** the response status code is 200
- **AND THEN** the response body contains `tracked_agent_id`, `manifest_path`, `session_root`, and `detail`
- **AND THEN** a `LiveAgentRegistryRecordV2` is published to the shared registry
- **AND THEN** a `ManagedHeadlessAuthorityRecord` is persisted to disk

#### Scenario: Invalid working directory returns 422
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a nonexistent `working_directory`
- **THEN** the response status code is 422
- **AND THEN** the response body explains the validation failure

#### Scenario: Tool mismatch returns 422
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` where `tool` does not match the manifest's `inputs.tool`
- **THEN** the response status code is 422

#### Scenario: Unsupported backend returns 422
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a tool whose resolved backend is not one of `claude_headless`, `codex_headless`, or `gemini_headless`
- **THEN** the response status code is 422

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

For each persisted authority whose tmux session is still live, the service SHALL attempt to resume a `RuntimeSessionController` from the stored manifest and rebuild the in-memory handle.

For authorities whose tmux sessions are gone, the service SHALL log a warning and optionally clean up the stale authority record.

#### Scenario: Live headless agent resumed on restart
- **WHEN** the passive server starts and a persisted authority record has a live tmux session
- **THEN** the in-memory handle is rebuilt
- **AND THEN** the agent is available for turn submission and status queries

#### Scenario: Dead headless agent cleaned up on restart
- **WHEN** the passive server starts and a persisted authority record has no live tmux session
- **THEN** a warning is logged
- **AND THEN** the stale authority record is cleaned up

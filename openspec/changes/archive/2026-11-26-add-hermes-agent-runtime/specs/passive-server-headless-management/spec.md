# Spec Delta

## MODIFIED Requirements

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

#### Scenario: Hermes Client Exit Does Not Settle the Native Turn

- **WHEN** an owned Hermes CLI exits without valid settlement evidence
- **THEN** the passive server retains the active or uncertain request and its durable CLI artifacts
- **AND THEN** it sets terminal status and completion time only after attributable settlement or explicit authorized disposition

### Requirement: Passive server launches qualified one-shot headless agents

`POST /houmao/agents/headless/launches` SHALL accept `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and optional `role_name`, `agent_name`, `agent_id`, and `mailbox`. It SHALL reject invalid inputs with HTTP 422, use `start_runtime_session()` for a qualified one-shot backend, persist server-managed authority, and return launch metadata.

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
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a tool whose resolved backend is not one of `claude_headless`, `codex_headless`, `kimi_headless`, `dsh_headless`, or `hermes_headless`
- **THEN** the response status code is 422

#### Scenario: Successful Kimi headless launch
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with valid Kimi tool inputs that resolve to `kimi_headless`
- **THEN** the response status code is 200
- **AND THEN** the response body contains `tracked_agent_id`, `manifest_path`, `session_root`, and `detail`
- **AND THEN** the launched Kimi agent can accept later managed turn submissions through the passive server

#### Scenario: Successful DSH Native Headless Launch
- **WHEN** a caller supplies valid DSH inputs that resolve to `dsh_headless`
- **THEN** the passive server returns normal managed launch metadata
- **AND THEN** later prompt, interrupt, stop, and usage operations use the saved DSH authority

#### Scenario: A service is presented to the headless-only endpoint

- **WHEN** a caller asks the passive headless endpoint to launch the persistent DSH ACP backend
- **THEN** the endpoint rejects the combination without starting a service

#### Scenario: Successful Hermes Headless Launch

- **WHEN** a caller supplies valid Hermes headless inputs, `hermes` is on the selected execution context's PATH, and the native launch succeeds
- **THEN** the endpoint returns the normal managed headless launch metadata
- **AND THEN** later submissions and inspections use the saved Hermes owner and the finite CLI turn contract

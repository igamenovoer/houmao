## MODIFIED Requirements

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
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a tool whose resolved backend is not one of `claude_headless`, `codex_headless`, `gemini_headless`, or `kimi_headless`
- **THEN** the response status code is 422

#### Scenario: Successful Kimi headless launch
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with valid Kimi tool inputs that resolve to `kimi_headless`
- **THEN** the response status code is 200
- **AND THEN** the response body contains `tracked_agent_id`, `manifest_path`, `session_root`, and `detail`
- **AND THEN** the launched Kimi agent can accept later managed turn submissions through the passive server

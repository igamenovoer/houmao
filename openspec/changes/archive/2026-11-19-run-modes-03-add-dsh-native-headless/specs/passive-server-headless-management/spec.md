# Spec Delta

## ADDED Requirements

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
- **WHEN** a caller sends `POST /houmao/agents/headless/launches` with a tool whose resolved backend is not one of `claude_headless`, `codex_headless`, `kimi_headless`, or `dsh_headless`
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

## MODIFIED Requirements

### Requirement: Passive Server Preserves DSH Headless Execution Evidence

Server-managed DSH headless turns SHALL expose canonical semantic events and preserve raw native CLI output as a distinct provider-debug artifact. Restart recovery SHALL preserve exact native session selection, active-attempt ownership, terminal results, and shared usage identities without replaying an admitted prompt.

#### Scenario: DSH Events and Raw Output Are Queried
- **WHEN** a caller retrieves a completed DSH turn's event stream and stdout artifact
- **THEN** events contain normalized semantic records and the raw provider artifact retains the CLI's newline-delimited JSON
- **AND THEN** neither response is replaced by rendered tmux console text

#### Scenario: Passive Server Restarts After Native Admission
- **WHEN** the passive server restarts while an owned DSH attempt is active or durably terminal
- **THEN** it recovers or reconciles that attempt from its authority and evidence
- **AND THEN** it does not start another process or resend the prompt merely to reconstruct status

## REMOVED Requirements

### Requirement: Passive server can launch native headless agents

**Reason**: The headless endpoint's DSH success case previously required an ACP process.

**Migration**: Use the native CLI backend for DSH headless births and the project service birth for ACP.

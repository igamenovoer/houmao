## ADDED Requirements

### Requirement: `houmao-passive-server` provides a health endpoint that identifies the passive server
The passive server SHALL expose `GET /health` returning a JSON payload with `status` and `houmao_service` fields.

The `houmao_service` field SHALL be `"houmao-passive-server"` to distinguish it from the existing `houmao-server`.

The health endpoint SHALL NOT extend `CaoHealthResponse`, SHALL NOT include a `service` field with value `"cli-agent-orchestrator"`, and SHALL NOT include `child_cao` metadata.

#### Scenario: Health returns passive server identity
- **WHEN** a caller sends `GET /health` to a running `houmao-passive-server`
- **THEN** the response status code is 200
- **AND THEN** the response body contains `{"status": "ok", "houmao_service": "houmao-passive-server"}`

#### Scenario: Health response does not include CAO compatibility fields
- **WHEN** a caller sends `GET /health` to a running `houmao-passive-server`
- **THEN** the response body does not contain a `service` key
- **AND THEN** the response body does not contain a `child_cao` key

### Requirement: `houmao-passive-server` provides a current-instance endpoint
The passive server SHALL expose `GET /houmao/server/current-instance` returning a JSON payload with the server's PID, API base URL, server root path, and startup timestamp.

The response schema version SHALL be `1`.

The response SHALL NOT include `child_cao` metadata.

#### Scenario: Current-instance returns live server metadata
- **WHEN** a caller sends `GET /houmao/server/current-instance` to a running `houmao-passive-server`
- **THEN** the response status code is 200
- **AND THEN** the response body contains `schema_version`, `status`, `pid`, `api_base_url`, `server_root`, and `started_at_utc` fields
- **AND THEN** `pid` matches the server's actual process ID
- **AND THEN** `api_base_url` matches the configured listen address
- **AND THEN** `server_root` is a directory path under the configured runtime root

### Requirement: `houmao-passive-server` provides a graceful shutdown endpoint
The passive server SHALL expose `POST /houmao/server/shutdown` that initiates graceful server shutdown.

The endpoint SHALL return a 200 response with `{"status": "ok"}` before the shutdown completes.

The server process SHALL exit after in-flight requests drain.

#### Scenario: Shutdown terminates the server
- **WHEN** a caller sends `POST /houmao/server/shutdown` to a running `houmao-passive-server`
- **THEN** the response status code is 200
- **AND THEN** the response body contains `{"status": "ok"}`
- **AND THEN** the server process terminates within a reasonable timeout

### Requirement: `houmao-passive-server` is configurable via `PassiveServerConfig`
The passive server SHALL accept configuration through a `PassiveServerConfig` Pydantic model.

`PassiveServerConfig` SHALL include at minimum:
- `api_base_url` (string, default `"http://127.0.0.1:9891"`)
- `runtime_root` (Path, default from `resolve_runtime_root()`)

`api_base_url` SHALL be normalized (trailing slash removed, scheme validated).

`runtime_root` SHALL be expanded and resolved to an absolute path.

The server root SHALL be derived as `{runtime_root}/houmao_servers/{host}-{port}` from the parsed `api_base_url`, following the same convention as the existing server.

#### Scenario: Default configuration uses port 9891
- **WHEN** a `PassiveServerConfig` is created with no arguments
- **THEN** `api_base_url` is `"http://127.0.0.1:9891"`
- **AND THEN** `runtime_root` is the resolved default runtime root

#### Scenario: Server root is derived from api_base_url
- **WHEN** a `PassiveServerConfig` is created with `api_base_url="http://0.0.0.0:9895"`
- **THEN** the derived `server_root` is `{runtime_root}/houmao_servers/0.0.0.0-9895`

### Requirement: `houmao-passive-server` is launchable via CLI entrypoint
The system SHALL provide a `houmao-passive-server` console_scripts entrypoint.

The CLI SHALL use Click and provide a `serve` subcommand that starts the FastAPI application via uvicorn.

The `serve` subcommand SHALL accept `--host`, `--port`, and `--runtime-root` options to override defaults.

#### Scenario: CLI starts the server on the default port
- **WHEN** a user runs `houmao-passive-server serve`
- **THEN** the server starts listening on `127.0.0.1:9891`
- **AND THEN** `GET /health` returns 200

#### Scenario: CLI accepts port override
- **WHEN** a user runs `houmao-passive-server serve --port 9895`
- **THEN** the server starts listening on `127.0.0.1:9895`

### Requirement: `houmao-passive-server` writes current-instance metadata on startup
On startup, the passive server SHALL create its `server_root` directory tree and write a `current_instance.json` file under `{server_root}/run/`.

This file SHALL contain the same fields as the `/houmao/server/current-instance` response.

On shutdown, the server SHALL remove the `current_instance.json` file.

#### Scenario: Current-instance file exists while server is running
- **WHEN** the passive server starts successfully
- **THEN** `{server_root}/run/current_instance.json` exists on disk
- **AND THEN** its `pid` field matches the server process ID

#### Scenario: Current-instance file is cleaned up on shutdown
- **WHEN** the passive server shuts down gracefully
- **THEN** `{server_root}/run/current_instance.json` no longer exists on disk

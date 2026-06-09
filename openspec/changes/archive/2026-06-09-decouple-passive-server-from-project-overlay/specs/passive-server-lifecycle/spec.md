## MODIFIED Requirements

### Requirement: `houmao-passive-server` is configurable via `PassiveServerConfig`
The passive server SHALL accept configuration through a `PassiveServerConfig` Pydantic model.

`PassiveServerConfig` SHALL include at minimum:
- `api_base_url` (string, default `"http://127.0.0.1:9891"`)
- `runtime_root` (Path, default from `resolve_runtime_root()`)
- `registry_root` (Path, default from `resolve_registry_root()`)

`api_base_url` SHALL be normalized (trailing slash removed, scheme validated).

`runtime_root` SHALL be expanded and resolved to an absolute path.

`registry_root` SHALL be expanded and resolved to an absolute path.

The server root SHALL be derived as `{runtime_root}/houmao_servers/{host}-{port}` from the parsed `api_base_url`, following the same convention as the existing server.

The default configuration SHALL NOT require a Houmao project overlay.

#### Scenario: Default configuration uses port 9891
- **WHEN** a `PassiveServerConfig` is created with no arguments
- **THEN** `api_base_url` is `"http://127.0.0.1:9891"`
- **AND THEN** `runtime_root` is the resolved default global runtime root
- **AND THEN** `registry_root` is the resolved default shared registry root

#### Scenario: Server root is derived from api_base_url
- **WHEN** a `PassiveServerConfig` is created with `api_base_url="http://0.0.0.0:9895"`
- **THEN** the derived `server_root` is `{runtime_root}/houmao_servers/0.0.0.0-9895`

#### Scenario: Default configuration works without project overlay
- **WHEN** no Houmao project overlay is discoverable from the current directory
- **AND WHEN** a `PassiveServerConfig` is created with no arguments
- **THEN** configuration succeeds using global runtime and registry defaults

### Requirement: `houmao-passive-server` is launchable via CLI entrypoint
The system SHALL provide a `houmao-passive-server` console_scripts entrypoint.

The CLI SHALL use Click and provide a `serve` subcommand that starts the FastAPI application via uvicorn.

The `serve` subcommand SHALL accept `--host`, `--port`, `--runtime-root`, and `--registry-root` options to override defaults.

The `serve` subcommand SHALL NOT require a Houmao project overlay when `--runtime-root` and `HOUMAO_GLOBAL_RUNTIME_DIR` are omitted.

#### Scenario: CLI starts the server on the default port
- **WHEN** a user runs `houmao-passive-server serve`
- **THEN** the server starts listening on `127.0.0.1:9891`
- **AND THEN** `GET /health` returns 200

#### Scenario: CLI accepts port override
- **WHEN** a user runs `houmao-passive-server serve --port 9895`
- **THEN** the server starts listening on `127.0.0.1:9895`

#### Scenario: CLI accepts registry root override
- **WHEN** a user runs `houmao-passive-server serve --registry-root /tmp/houmao-registry`
- **THEN** the server uses `/tmp/houmao-registry` as its shared registry root for discovery and passive-server-owned registry mutations

#### Scenario: CLI starts without project overlay
- **WHEN** no Houmao project overlay is discoverable from the current directory
- **AND WHEN** a user runs `houmao-passive-server serve`
- **THEN** the server starts using global runtime and registry defaults instead of failing with project-overlay guidance

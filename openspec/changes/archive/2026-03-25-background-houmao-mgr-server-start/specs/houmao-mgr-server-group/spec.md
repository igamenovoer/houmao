## MODIFIED Requirements

### Requirement: `houmao-mgr server` group exposes server lifecycle commands
`houmao-mgr` SHALL expose a `server` command group for managing the `houmao-server` process lifecycle.

At minimum, the `server` group SHALL include:

- `start` - start the houmao-server process
- `stop` - gracefully stop a running houmao-server
- `status` - display server health, uptime, and active session count

#### Scenario: Operator starts the server through houmao-mgr
- **WHEN** an operator runs `houmao-mgr server start`
- **THEN** `houmao-mgr` starts or reuses the `houmao-server` process using the same uvicorn startup path as `houmao-server serve`
- **AND THEN** the default `start` behavior runs the server detached in the background rather than blocking the invoking terminal
- **AND THEN** the command prints a startup status result that reports the resolved server URL and whether startup succeeded

#### Scenario: Operator starts the server with configuration options
- **WHEN** an operator runs `houmao-mgr server start --api-base-url http://127.0.0.1:9889 --runtime-root /tmp/houmao`
- **THEN** `houmao-mgr` passes those configuration options to the server startup path
- **AND THEN** the detached startup result reports the configured server URL and the owned server runtime identity for that listener when startup succeeds

#### Scenario: Operator explicitly requests foreground startup
- **WHEN** an operator runs `houmao-mgr server start --foreground`
- **THEN** `houmao-mgr` starts the `houmao-server` process in the current foreground process rather than detaching it
- **AND THEN** the server respects the same startup option surface as `houmao-server serve`

#### Scenario: Operator reruns start while the server is already healthy
- **WHEN** an operator runs `houmao-mgr server start`
- **AND WHEN** a healthy `houmao-server` is already reachable on the resolved listener URL
- **THEN** `houmao-mgr` reports a successful startup result for the existing instance rather than spawning a duplicate listener

#### Scenario: Detached start fails before the server becomes healthy
- **WHEN** an operator runs `houmao-mgr server start`
- **AND WHEN** the detached child process exits early or does not become healthy within the startup wait budget
- **THEN** the command reports an unsuccessful startup result
- **AND THEN** the result includes enough detail for the operator to identify the target server URL and inspect the owned startup logs

#### Scenario: Operator checks server status
- **WHEN** an operator runs `houmao-mgr server status`
- **THEN** `houmao-mgr` contacts the server health endpoint
- **AND THEN** the command displays whether the server is running, its URL, and a summary of active sessions

#### Scenario: Server status reports when no server is running
- **WHEN** an operator runs `houmao-mgr server status` and no server is reachable
- **THEN** the command reports that no server is running
- **AND THEN** it does not raise a Python exception or stack trace

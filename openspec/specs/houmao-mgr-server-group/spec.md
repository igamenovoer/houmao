## Purpose
Define the `houmao-mgr server` lifecycle and server-session management command surface.
## Requirements
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

### Requirement: `houmao-mgr server sessions` subgroup exposes session management
`houmao-mgr` SHALL expose a `server sessions` subgroup for inspecting and managing server-owned sessions.

At minimum, the `server sessions` subgroup SHALL include:

- `list` - list active server-managed sessions
- `show <session>` - display detail for one session
- `shutdown` - shutdown sessions (with `--all` or `--session <name>`)

These commands SHALL contact the running `houmao-server` to retrieve or mutate session state.

#### Scenario: Operator lists server sessions
- **WHEN** an operator runs `houmao-mgr server sessions list`
- **THEN** `houmao-mgr` queries the running server for active sessions
- **AND THEN** the command displays session names and their status

#### Scenario: Operator shuts down all server sessions
- **WHEN** an operator runs `houmao-mgr server sessions shutdown --all`
- **THEN** `houmao-mgr` requests shutdown of all sessions through the server API
- **AND THEN** the corresponding tmux sessions are terminated

#### Scenario: Operator shuts down a specific server session
- **WHEN** an operator runs `houmao-mgr server sessions shutdown --session <name>`
- **THEN** `houmao-mgr` requests shutdown of only that session through the server API
- **AND THEN** other sessions remain unaffected

### Requirement: `houmao-mgr server stop` gracefully shuts down the server
`houmao-mgr server stop` SHALL send a graceful shutdown signal to the running `houmao-server` process.

#### Scenario: Operator stops the server
- **WHEN** an operator runs `houmao-mgr server stop`
- **THEN** `houmao-mgr` sends a shutdown request to the server
- **AND THEN** the server performs its shutdown sequence (persist state, stop supervisor, cleanup)

#### Scenario: Stop reports when no server is running
- **WHEN** an operator runs `houmao-mgr server stop` and no server is reachable
- **THEN** the command reports that no server is running to stop
- **AND THEN** it exits cleanly without an error stack trace

### Requirement: `houmao-mgr server start` resolves the runtime root project-aware by default
When `houmao-mgr server start` runs in project context without an explicit `--runtime-root`, the effective runtime root SHALL default to `<active-overlay>/runtime`.

When no active project overlay exists and no stronger override is supplied, the command SHALL ensure `<cwd>/.houmao` exists and use `<cwd>/.houmao/runtime` as the resulting default runtime root.

Explicit `--runtime-root` input SHALL continue to win over project-aware defaults.

#### Scenario: Server start uses overlay-local runtime by default in project context
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr server start` without `--runtime-root`
- **THEN** the command starts or reuses `houmao-server` using `/repo/.houmao/runtime` as the effective runtime root
- **AND THEN** owned server artifacts for that start path are written under the overlay-local runtime root

#### Scenario: Explicit runtime-root override still wins for server start
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr server start --runtime-root /tmp/houmao-server-runtime`
- **THEN** the command uses `/tmp/houmao-server-runtime` as the effective runtime root
- **AND THEN** it does not replace that explicit override with `/repo/.houmao/runtime`

### Requirement: Server help and startup wording describe project-aware runtime-root selection
Maintained `houmao-mgr server ...` and `houmao-server ...` operator-facing help text plus startup or status wording SHALL describe project-aware runtime-root selection consistently.

When no explicit runtime-root override wins and project context is active, help text SHALL describe the default server artifact scope as the active project runtime root.

When `--runtime-root` or `HOUMAO_GLOBAL_RUNTIME_DIR` wins, operator-facing wording SHALL describe that scope as an explicit runtime-root selection rather than as an active project runtime root.

#### Scenario: Server help text describes the project-aware runtime-root default
- **WHEN** an operator runs `houmao-mgr server start --help` or `houmao-server serve --help`
- **THEN** the help output explains that `--runtime-root` overrides the active project runtime root when project context is active
- **AND THEN** it does not imply that maintained server artifacts always default to the shared runtime root

#### Scenario: Startup result describes the resolved runtime-root source accurately
- **WHEN** an operator starts a server without an explicit runtime-root override in project context
- **THEN** the startup result describes the resolved server artifact scope as the active project runtime root
- **AND THEN** the wording changes when an explicit runtime-root override is supplied so the explicit override remains visible to the operator


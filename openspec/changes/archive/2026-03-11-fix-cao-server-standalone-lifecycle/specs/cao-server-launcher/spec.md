## MODIFIED Requirements

### Requirement: Start (or reuse) a local CAO server
The system SHALL provide a CAO server launcher that can health-check a CAO API
base URL and, when configured for a supported upstream base URL, bootstrap a
standalone detached local `cao-server` service and wait until it becomes
healthy.

Supported upstream base URLs are currently restricted to:
- `http://localhost:9889`
- `http://127.0.0.1:9889`

When `start` launches a new service, the launched `cao-server` SHALL NOT depend
on the continued lifetime of the invoking launcher command after `start`
returns.

#### Scenario: Start returns without starting when CAO is already healthy
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** `GET /health` returns a JSON payload with `status="ok"`
- **THEN** the launcher reports success
- **AND THEN** it reports that no new CAO server process was started

#### Scenario: Start bootstraps a standalone detached service when unhealthy and base URL is supported
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** CAO is not healthy at that base URL
- **THEN** the launcher starts a standalone detached `cao-server` service
- **AND THEN** it waits until `GET /health` reports `status="ok"` or a configured timeout elapses
- **AND THEN** it reports success when CAO becomes healthy
- **AND THEN** a later separate launcher `status` call can still reach that CAO service after the original `start` command has exited

#### Scenario: Start refuses to start CAO for an unsupported base URL
This scenario is defined as a defense-in-depth behavior. In the intended usage,
config validation should already reject unsupported `base_url` values.

- **WHEN** the launcher is asked to start CAO at a base URL that is not supported
- **THEN** the launcher fails fast with an explicit error
- **AND THEN** it does not attempt to start a `cao-server` process

### Requirement: Launcher writes pid and log artifacts under the runtime root
When the launcher starts a `cao-server` process, it SHALL persist service
artifacts under a deterministic path rooted at the configured runtime root.

The launcher SHALL record at least:
- a pid file containing the started process pid,
- a server log file capturing stdout/stderr, and
- a structured ownership artifact describing the standalone service context.

The launcher SHALL partition artifacts by base URL host/port:
`runtime_root/cao-server/<host>-<port>/`.

The launcher SHOULD additionally write a structured diagnostics file (for
example `launcher_result.json`) in the same directory to simplify debugging.

#### Scenario: Start writes pid, log, and ownership artifacts in the `<host>-<port>` directory
- **WHEN** the launcher starts a local `cao-server` process at base URL `http://localhost:9889`
- **THEN** it writes `runtime_root/cao-server/localhost-9889/cao-server.pid`
- **AND THEN** it writes `runtime_root/cao-server/localhost-9889/cao-server.log`
- **AND THEN** it writes a structured ownership artifact in `runtime_root/cao-server/localhost-9889/`
- **AND THEN** the launcher reports the pid and artifact paths in its result payload

### Requirement: Stop is pidfile-based with best-effort identity verification
The launcher SHALL provide a `stop` operation that reads the pidfile under the
base URL artifact directory and performs best-effort identity verification
before killing the detached service.

The stop operation SHALL:
- verify the process exists,
- best-effort verify the process command line indicates `cao-server`,
- use launcher-managed artifact metadata for diagnostics and ownership checks,
- refuse to kill if verification fails (with actionable diagnostics), and
- remove stale pidfile state when the recorded process no longer exists.

The stop operation SHALL send SIGTERM, wait up to 10 seconds, then send SIGKILL
as a fallback.

#### Scenario: Stop refuses to kill when verification fails
- **WHEN** the launcher is asked to stop CAO at `http://localhost:9889`
- **AND WHEN** the pidfile exists but the pid cannot be verified as `cao-server`
- **THEN** the launcher refuses to kill the process

#### Scenario: Stop terminates a detached service launched by an earlier start command
- **WHEN** the launcher previously started a standalone detached `cao-server` service at `http://localhost:9889`
- **AND WHEN** the `stop` command is run in a later separate process
- **THEN** the launcher terminates that `cao-server` service
- **AND THEN** the pidfile-tracked artifact state no longer describes a running CAO service

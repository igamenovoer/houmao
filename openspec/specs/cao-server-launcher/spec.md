# cao-server-launcher Specification

## Purpose
TBD - created by archiving change cao-server-launcher. Update Purpose after archive.
## Requirements
### Requirement: Launcher is configured via a server config file
The launcher SHALL accept a server config file as its primary configuration
input.

The launcher SHALL support TOML config files.

The config file SHALL include at least:
- CAO API `base_url`,
- `runtime_root` for pid/log artifacts,
- proxy policy (`clear` or `inherit`), and
- optional trusted home directory (applied as CAO server process `HOME`).

#### Scenario: Config file defines launcher inputs
- **WHEN** a developer provides a launcher TOML config file containing `base_url`, `runtime_root`, and `proxy_policy`
- **THEN** the launcher loads the config successfully and uses those values for `status`, `start`, and `stop` operations

### Requirement: Launcher config files are schema-validated
The launcher SHALL validate the config file against a schema and fail fast with
actionable errors when the config is invalid.

The launcher SHALL reject:
- unknown keys (typo protection),
- invalid enum values (for example proxy policy not in `{clear, inherit}`), and
- structurally invalid values (for example malformed base URLs or non-positive
  timeouts).

The launcher SHALL currently restrict `base_url` to upstream-supported values:
- `http://localhost:9889`
- `http://127.0.0.1:9889`

This restriction exists because upstream `cao-server` host/port is currently
hard-coded and not known to be configurable.

#### Scenario: Unknown config keys are rejected
- **WHEN** the launcher loads a config file that contains an unknown key
- **THEN** the launcher fails with an explicit validation error

#### Scenario: Invalid enum values are rejected
- **WHEN** the launcher loads a config file whose proxy policy value is not one of `clear` or `inherit`
- **THEN** the launcher fails with an explicit validation error

#### Scenario: Unsupported base_url values are rejected
- **WHEN** the launcher loads a config file whose `base_url` is not one of the supported upstream values
- **THEN** the launcher fails with an explicit validation error

### Requirement: Start (or reuse) a local CAO server
The system SHALL provide a CAO server launcher that can health-check a CAO API
base URL and, when configured for a supported upstream base URL, start a local
`cao-server` process and wait until it becomes healthy.

Supported upstream base URLs are currently restricted to:
- `http://localhost:9889`
- `http://127.0.0.1:9889`

#### Scenario: Start returns without starting when CAO is already healthy
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** `GET /health` returns a JSON payload with `status="ok"`
- **THEN** the launcher reports success
- **AND THEN** it reports that no new CAO server process was started

#### Scenario: Start starts local server when unhealthy and base URL is supported
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** CAO is not healthy at that base URL
- **THEN** the launcher starts a background `cao-server` process
- **AND THEN** it waits until `GET /health` reports `status="ok"` or a configured timeout elapses
- **AND THEN** it reports success when CAO becomes healthy

#### Scenario: Start refuses to start CAO for an unsupported base URL
This scenario is defined as a defense-in-depth behavior. In the intended usage,
config validation should already reject unsupported `base_url` values.

- **WHEN** the launcher is asked to start CAO at a base URL that is not supported
- **THEN** the launcher fails fast with an explicit error
- **AND THEN** it does not attempt to start a `cao-server` process

### Requirement: Status reports CAO health without side effects
The launcher SHALL provide a `status` operation that reports CAO health at the
configured base URL without starting or stopping any processes.

#### Scenario: Status reports healthy
- **WHEN** the launcher is asked for CAO status at `http://localhost:9889`
- **AND WHEN** `GET /health` returns a JSON payload with `status="ok"`
- **THEN** the launcher reports that CAO is healthy

### Requirement: Launcher writes pid and log artifacts under the runtime root
When the launcher starts a `cao-server` process, it SHALL persist process
artifacts under a deterministic path rooted at the configured runtime root.

The launcher SHALL record at least:
- a pid file containing the started process pid, and
- a server log file capturing stdout/stderr.

The launcher SHALL partition artifacts by base URL host/port:
`runtime_root/cao-server/<host>-<port>/`.

The launcher SHOULD additionally write a structured diagnostics file (for
example `launcher_result.json`) in the same directory to simplify debugging.

#### Scenario: Start writes pid and log files in the `<host>-<port>` directory
- **WHEN** the launcher starts a local `cao-server` process at base URL `http://localhost:9889`
- **THEN** it writes `runtime_root/cao-server/localhost-9889/cao-server.pid`
- **AND THEN** it writes `runtime_root/cao-server/localhost-9889/cao-server.log`
- **AND THEN** the launcher reports the pid and log path in its result payload

### Requirement: Stop is pidfile-based with best-effort identity verification
The launcher SHALL provide a `stop` operation that reads the pidfile under the
base URL artifact directory and performs best-effort identity verification
before killing the process.

The stop operation SHALL:
- verify the process exists,
- best-effort verify the process command line indicates `cao-server`, and
- refuse to kill if verification fails (with actionable diagnostics).

The stop operation SHALL send SIGTERM, wait up to 10 seconds, then send SIGKILL
as a fallback.

#### Scenario: Stop refuses to kill when verification fails
- **WHEN** the launcher is asked to stop CAO at `http://localhost:9889`
- **AND WHEN** the pidfile exists but the pid cannot be verified as `cao-server`
- **THEN** the launcher refuses to kill the process

### Requirement: Launcher uses `cao-server` from `PATH`
The launcher SHALL invoke `cao-server` as found on `PATH` and SHALL NOT run CAO
server from vendored sources under `extern/` (for example by injecting
`PYTHONPATH`).

#### Scenario: Missing `cao-server` executable is reported
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** `cao-server` is not found on `PATH`
- **THEN** the launcher fails fast with an explicit error describing how to install CAO

### Requirement: Proxy policy is configurable for the launched CAO server process
The launcher SHALL support a proxy policy that controls which proxy-related
environment variables are present in the launched `cao-server` process
environment.

Allowed policy values are exactly:
- `clear` (default)
- `inherit`

Proxy environment variables controlled by the policy are:
- `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`
- `http_proxy`, `https_proxy`, `all_proxy`

#### Scenario: Proxy policy clear unsets proxy vars
- **WHEN** the launcher starts a `cao-server` process with proxy policy `clear`
- **THEN** the launched process environment does not include any of the controlled proxy variables

#### Scenario: Proxy policy inherit preserves proxy vars
- **WHEN** the launcher starts a `cao-server` process with proxy policy `inherit`
- **THEN** the launched process environment includes the controlled proxy variables that were present in the caller environment

The launcher SHALL preserve and merge `NO_PROXY` and/or `no_proxy` in the target
server environment so loopback hosts bypass any configured proxy settings.

#### Scenario: Launched server environment includes loopback NO_PROXY entries
- **WHEN** the launcher starts a `cao-server` process for base URL `http://localhost:9889`
- **THEN** the launched process environment includes `NO_PROXY` and/or `no_proxy`
- **AND THEN** the configured value includes at least `localhost`, `127.0.0.1`, and `::1`

### Requirement: Trusted home directory controls CAO workdir acceptance
The launcher SHALL support an optional “trusted home” directory setting that is
applied to the launched `cao-server` process as its `HOME` value.

This setting exists to control CAO’s workdir validation behavior (which
restricts working directories to the CAO process home tree).

CAO writes its own state under `HOME/.aws/cli-agent-orchestrator/`, so the chosen
`HOME` directory must be writable (even if the repo workdirs under it are
read-only).

#### Scenario: Launcher overrides HOME when trusted home is configured
- **WHEN** the launcher starts `cao-server` with a configured trusted-home directory `H`
- **THEN** the launched process environment sets `HOME=H`

#### Scenario: Missing trusted home is rejected
- **WHEN** the launcher is asked to start `cao-server` with a trusted-home directory that does not exist
- **THEN** the launcher fails fast with an explicit configuration error


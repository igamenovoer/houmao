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
- optional `runtime_root` for launcher artifacts and default home derivation,
- optional `home_dir` (applied as the CAO server process `HOME`),
- optional proxy policy (`clear` or `inherit`), and
- optional `startup_timeout_seconds`.

When `runtime_root` is omitted from config and CLI overrides, the launcher SHALL resolve the effective runtime root from the shared Houmao runtime-root contract before deriving launcher artifacts or a default `home_dir`.

The launcher CLI SHALL additionally support one-shot arguments that override
supported config-file values for a single invocation without modifying the file
on disk.

At minimum, the launcher SHALL support CLI overrides for:
- `base_url`
- `runtime_root`
- `home_dir`
- `proxy_policy`
- `startup_timeout_seconds`

#### Scenario: Config file defines launcher inputs
- **WHEN** a developer provides a launcher TOML config file containing `base_url`, `runtime_root`, and `proxy_policy`
- **THEN** the launcher loads the config successfully and uses those values for `status`, `start`, and `stop` operations

#### Scenario: CLI override replaces config-file base_url for one invocation
- **WHEN** a developer runs launcher `start` with config file `base_url = "http://127.0.0.1:9889"`
- **AND WHEN** the same command also passes CLI override `--base-url http://127.0.0.1:9991`
- **THEN** the launcher uses `http://127.0.0.1:9991` as the effective base URL for that invocation
- **AND THEN** the config file on disk remains unchanged

### Requirement: Launcher config files are schema-validated
The launcher SHALL validate the config file against a schema and fail fast with
actionable errors when the config is invalid.

The launcher SHALL reject:
- unknown keys (typo protection),
- invalid enum values (for example proxy policy not in `{clear, inherit}`), and
- structurally invalid values (for example malformed base URLs or non-positive
  timeouts).

The launcher SHALL accept loopback `base_url` values only when all of the
following are true:
- the URL uses the `http` scheme,
- the host is `localhost` or `127.0.0.1`, and
- the URL includes an explicit port.

The launcher SHALL reject non-loopback hosts, missing ports, and malformed CAO
base URLs.

#### Scenario: Unknown config keys are rejected
- **WHEN** the launcher loads a config file that contains an unknown key
- **THEN** the launcher fails with an explicit validation error

#### Scenario: Invalid enum values are rejected
- **WHEN** the launcher loads a config file whose proxy policy value is not one of `clear` or `inherit`
- **THEN** the launcher fails with an explicit validation error

#### Scenario: Non-default loopback port values are accepted
- **WHEN** the launcher loads a config file whose `base_url` is `http://127.0.0.1:9991`
- **THEN** the launcher accepts that config as a supported loopback CAO target

#### Scenario: Invalid CLI override values are rejected
- **WHEN** the launcher is invoked with a CLI override whose effective `base_url` uses a non-loopback host or omits an explicit port
- **THEN** the launcher fails with an explicit validation error for that override

#### Scenario: Unsupported base_url values are rejected
- **WHEN** the launcher loads a config file whose `base_url` uses a non-loopback host or omits an explicit port
- **THEN** the launcher fails with an explicit validation error

### Requirement: Start (or reuse) a local CAO server
The system SHALL provide a CAO server launcher that can health-check a CAO API
base URL and, when configured for a supported upstream base URL, bootstrap a
standalone detached local `cao-server` service and wait until it becomes
healthy.

Supported launcher-managed base URLs are restricted to:
- `http://localhost:<port>`
- `http://127.0.0.1:<port>`

When `start` launches a new service, the launched `cao-server` SHALL NOT depend
on the continued lifetime of the invoking launcher command after `start`
returns.

When the launcher spawns `cao-server`, it SHALL derive the requested port from
`base_url` and pass that port to the launched process using CAO's supported
port-selection mechanism.

If the requested `base_url` does not become healthy within the configured
timeout after a spawn attempt, the launcher SHALL fail explicitly and SHALL NOT
report success against a different loopback port.

#### Scenario: Start returns without starting when CAO is already healthy
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** `GET /health` returns a JSON payload with `status="ok"`
- **THEN** the launcher reports success
- **AND THEN** it reports that no new CAO server process was started

#### Scenario: Start bootstraps a standalone detached service on a supported non-default port
- **WHEN** the launcher is asked to start CAO at `http://127.0.0.1:9991`
- **AND WHEN** CAO is not healthy at that base URL
- **THEN** the launcher starts a standalone detached `cao-server` service configured for port `9991`
- **AND THEN** it waits until `GET /health` reports `status="ok"` at `http://127.0.0.1:9991` or a configured timeout elapses
- **AND THEN** it reports success when CAO becomes healthy at that requested base URL

#### Scenario: Requested non-default port is not honored by the installed CAO server
- **WHEN** the launcher is asked to start CAO at `http://127.0.0.1:9991`
- **AND WHEN** the spawned `cao-server` process never becomes healthy at that requested base URL within the configured timeout
- **THEN** the launcher fails with an explicit startup error
- **AND THEN** it does not report success by falling back to a different loopback CAO port

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
When the launcher starts a `cao-server` process, it SHALL persist service
artifacts under a deterministic path rooted at the configured runtime root.

The launcher SHALL record at least:
- a pid file containing the started process pid,
- a server log file capturing stdout/stderr, and
- a structured ownership artifact describing the standalone service context.

The launcher SHALL partition artifacts by base URL host/port under a launcher-specific subtree:
`runtime_root/cao_servers/<host>-<port>/launcher/`.

The launcher SHOULD additionally write a structured diagnostics file (for
example `launcher_result.json`) in the same directory to simplify debugging.

Legacy launcher artifact directories under `runtime_root/cao-server/<host>-<port>/` are not part of a compatibility contract and MAY be removed manually after cutover.

#### Scenario: Start writes pid, log, and ownership artifacts in the launcher subtree
- **WHEN** the launcher starts a local `cao-server` process at base URL `http://localhost:9889`
- **THEN** it writes `runtime_root/cao_servers/localhost-9889/launcher/cao-server.pid`
- **AND THEN** it writes `runtime_root/cao_servers/localhost-9889/launcher/cao-server.log`
- **AND THEN** it writes a structured ownership artifact in `runtime_root/cao_servers/localhost-9889/launcher/`
- **AND THEN** the launcher reports the pid and artifact paths in its result payload

#### Scenario: Legacy cao-server artifact path is not used as a fallback
- **WHEN** a launcher runtime root still contains legacy artifacts under `runtime_root/cao-server/localhost-9889/`
- **AND WHEN** launcher logic resolves artifact paths after this change
- **THEN** it uses `runtime_root/cao_servers/localhost-9889/launcher/` and sibling `home/` as the authoritative layout
- **AND THEN** it does not require fallback reads from the old `cao-server/` path

### Requirement: Stop is pidfile-based with best-effort identity verification
The launcher SHALL provide a `stop` operation that reads the pidfile under the
base URL artifact directory and performs best-effort identity verification
before killing the process.

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

### Requirement: Launcher stop SHALL persist structured diagnostics from a fresh runtime root
The launcher SHALL ensure the parent directory for `launcher_result.json`
exists before writing structured `stop` results under
`runtime_root/cao_servers/<host>-<port>/launcher/`.

This requirement SHALL apply even when `stop` returns early because no pidfile
exists, because the tracked pid is stale, or because process verification fails.

The launcher SHALL return a structured `stop` result payload instead of raising
a filesystem error solely because the runtime artifact directory did not exist
before the `stop` command began.

#### Scenario: Stop without a preexisting artifact directory returns structured already-stopped output
- **WHEN** a developer runs launcher `stop` for `http://127.0.0.1:9889`
- **AND WHEN** the resolved `runtime_root/cao_servers/127.0.0.1-9889/launcher/` directory does not yet exist
- **AND WHEN** no pidfile exists for that config
- **THEN** the launcher returns a structured `already_stopped` result payload
- **AND THEN** it writes `launcher_result.json` under the resolved artifact directory
- **AND THEN** it does not fail solely because the artifact directory was missing before the command

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
server environment for supported loopback CAO base URLs so loopback hosts bypass
any configured proxy settings on the selected port.

#### Scenario: Launched server environment includes loopback NO_PROXY entries on a non-default port
- **WHEN** the launcher starts a `cao-server` process for base URL `http://localhost:9991`
- **THEN** the launched process environment includes `NO_PROXY` and/or `no_proxy`
- **AND THEN** the configured value includes at least `localhost`, `127.0.0.1`, and `::1`

### Requirement: Launcher home directory anchors CAO state and process HOME
The launcher SHALL treat CAO `HOME` as launcher-owned mutable service state that is distinct from the shared registry root and from agent workdirs.

The launcher SHALL support an optional `home_dir` setting that is applied to the launched `cao-server` process as its `HOME` value.

When launcher config and CLI overrides do not provide an explicit `runtime_root`, and `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to an absolute directory path, the launcher SHALL use that env-var value as the effective runtime root before deriving launcher artifacts or a default `home_dir`.

When launcher config does not provide an explicit `home_dir`, the launcher SHALL derive a default CAO home for that base URL under the effective runtime root as:
- `<runtime_root>/cao_servers/<host>-<port>/home/`

When launcher config provides an explicit `home_dir`, the launcher SHALL use that explicit path instead of the derived default.

The chosen `home_dir` exists to choose the CAO state/profile-store root under `HOME/.aws/cli-agent-orchestrator/`.

The effective CAO home SHALL remain writable because CAO writes its own state there.

The launcher SHALL NOT define or document a repo-owned rule that CAO session workdirs must live under `home_dir` or the user home tree. Workdir acceptance for later CAO-backed sessions belongs to the installed CAO server behavior, while the launcher owns only the launched process `HOME` and state-root configuration.

#### Scenario: Launcher start derives a default CAO home from the runtime root
- **WHEN** the launcher starts `cao-server` for base URL `http://localhost:9889`
- **AND WHEN** launcher config omits `home_dir`
- **THEN** the launcher uses `<runtime_root>/cao_servers/localhost-9889/home/` as the effective CAO `HOME`

#### Scenario: Explicit home_dir override is preserved
- **WHEN** the launcher starts `cao-server` for base URL `http://localhost:9889`
- **AND WHEN** launcher config explicitly provides `home_dir = "/data/custom/cao-home"`
- **THEN** the launcher uses `/data/custom/cao-home` as the effective CAO `HOME`
- **AND THEN** it does not replace that explicit path with the derived default

#### Scenario: Runtime-root env-var override relocates launcher artifacts and default home
- **WHEN** `AGENTSYS_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** launcher config and CLI overrides do not provide an explicit `runtime_root`
- **AND WHEN** launcher config omits `home_dir`
- **THEN** the launcher uses `/tmp/houmao-runtime` as the effective runtime root
- **AND THEN** it derives the default CAO `HOME` under `/tmp/houmao-runtime/cao_servers/<host>-<port>/home/`

#### Scenario: Launcher overrides HOME when home_dir is configured
- **WHEN** the launcher starts `cao-server` with a configured `home_dir` value `H`
- **THEN** the launched process environment sets `HOME=H`

#### Scenario: Missing home_dir is rejected
- **WHEN** the launcher is asked to start `cao-server` with a configured `home_dir` that does not exist
- **THEN** the launcher fails fast with an explicit configuration error

#### Scenario: Launcher guidance does not require session workdirs under home_dir
- **WHEN** a developer follows repo-owned launcher docs or examples
- **THEN** those docs describe `home_dir` as the CAO state/profile-store anchor
- **AND THEN** they do not instruct the developer to place session workdirs under `home_dir` solely because of a repo-owned launcher rule

### Requirement: User-facing launcher CLI uses the Houmao name
The repository SHALL publish the supported user-facing CAO launcher CLI under the name `houmao-cao-server`.

Repo-owned docs, examples, scripts, and help text SHALL teach `houmao-cao-server` as the current launcher command and SHALL NOT present `gig-cao-server` as a current user-facing launcher surface.

#### Scenario: Launcher command examples use the canonical binary name
- **WHEN** a developer follows a repo-owned launcher example or help page
- **THEN** the example uses `houmao-cao-server`
- **AND THEN** it does not instruct the developer to run `gig-cao-server`

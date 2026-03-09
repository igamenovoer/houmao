## MODIFIED Requirements

### Requirement: Launcher uses `cao-server` from `PATH`
The launcher SHALL invoke `cao-server` as found on `PATH` and SHALL NOT run CAO
server from vendored sources under `extern/` (for example by injecting
`PYTHONPATH`).

Active installation guidance for satisfying this prerequisite SHALL point users
at a fork-backed CAO source rather than `awslabs/cli-agent-orchestrator` or the
ambiguous package-name install `uv tool install cli-agent-orchestrator`.

#### Scenario: Missing `cao-server` executable is reported
- **WHEN** the launcher is asked to start CAO at `http://localhost:9889`
- **AND WHEN** `cao-server` is not found on `PATH`
- **THEN** the launcher fails fast with an explicit error describing how to install fork-backed CAO

### Requirement: Launcher preflights exact required executable and fails fast with install guidance
The launcher SHALL preflight required CAO executable availability (`cao-server`)
on `PATH` before launch/manage operations and SHALL fail immediately with
actionable installation instructions when unavailable.

Those installation instructions SHALL identify a fork-backed CAO install source
and SHALL NOT direct users to `awslabs/cli-agent-orchestrator` or
`uv tool install cli-agent-orchestrator`.

#### Scenario: Missing `cao-server` fails with actionable guidance
- **WHEN** a user invokes launcher operation requiring `cao-server` and executable is not found on `PATH`
- **THEN** launcher exits before starting CAO operations
- **AND THEN** error output identifies missing `cao-server` and includes fork-backed installation guidance

#### Scenario: Present `cao-server` allows launcher flow to continue
- **WHEN** a user invokes launcher operation requiring `cao-server` and executable exists on `PATH`
- **THEN** launcher proceeds with normal start/status/stop behavior

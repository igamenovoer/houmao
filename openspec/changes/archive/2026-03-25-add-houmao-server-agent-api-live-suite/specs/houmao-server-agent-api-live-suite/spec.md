# houmao-server-agent-api-live-suite Specification

## ADDED Requirements

### Requirement: Canonical live suite SHALL provision an isolated `houmao-server` authority for managed-agent API verification
The system SHALL provide one canonical live suite for basic `houmao-server` managed-agent API verification.

The suite SHALL start a real `houmao-server` subprocess under one suite-owned run root with isolated runtime, registry, jobs, log, and home directories.

The suite SHALL use a repo-local `tmp/` run-root prefix by default and SHALL allow an operator-provided run-root override path.

The suite SHALL fail before server startup if required local executables, including `tmux` plus the selected provider executables, or required credential material for the selected live lanes are missing.

For Codex lanes in this capability version, the suite SHALL treat API-key-mode credential inputs as required prerequisites.

The suite SHALL verify `GET /health` on its owned `houmao-server` before any lane provisioning begins.

The suite SHALL preserve its run-root artifacts after both success and failure so operators can inspect logs, HTTP snapshots, and lane state without re-running the suite.

#### Scenario: Suite starts a real isolated `houmao-server`
- **WHEN** an operator starts the canonical live suite with valid prerequisites
- **THEN** the suite starts one real `houmao-server` under a suite-owned isolated run root
- **AND THEN** if the operator did not provide an override path, that run root lives under the suite's repo-local `tmp/` default prefix
- **AND THEN** the suite verifies `GET /health` successfully before lane provisioning starts
- **AND THEN** the suite records the selected API base URL plus suite-owned runtime, registry, jobs, and log directories under that run root

#### Scenario: Missing prerequisites block the suite before server startup
- **WHEN** an operator starts the suite without `tmux`, without one selected provider executable, or without one required credential input for a selected lane
- **THEN** the suite fails before starting `houmao-server`
- **AND THEN** the failure output identifies the missing prerequisite directly

### Requirement: Canonical live suite SHALL launch four direct managed-agent lanes without gateway
The suite SHALL support both one all-lanes aggregate run and operator-selected per-lane runs in its first version.

The suite SHALL cover four real managed-agent lanes in its first version:

- Claude TUI
- Codex TUI
- Claude headless
- Codex headless

The suite SHALL create TUI lanes through the CAO-compatible creation path plus managed-agent registration, and SHALL create headless lanes through the native headless managed-agent launch route.

The suite SHALL create TUI lanes with an explicit configurable CAO session-creation timeout budget rather than relying on the REST-client implicit default.

The suite SHALL NOT attach or depend on a gateway for any of those lanes in this capability version.

#### Scenario: Operator selects one subset of lanes for a live run
- **WHEN** an operator starts the suite while selecting one subset of the supported lanes
- **THEN** the suite provisions only the selected lanes
- **AND THEN** the same discovery, prompt, and stop verification rules apply to that selected subset

#### Scenario: TUI lanes are admitted through creation plus registration
- **WHEN** the suite provisions one Claude TUI lane or one Codex TUI lane
- **THEN** it creates the TUI session through the CAO-compatible session-creation route
- **AND THEN** it registers that launched session through the managed-agent registration route so the lane becomes addressable on `/houmao/agents/*`

#### Scenario: Headless lanes are admitted through the native managed-agent launch route
- **WHEN** the suite provisions one Claude headless lane or one Codex headless lane
- **THEN** it launches that lane through `POST /houmao/agents/headless/launches`
- **AND THEN** the launched lane becomes addressable on `/houmao/agents/*` without requiring CAO session registration

### Requirement: Canonical live suite SHALL verify managed-agent discovery and state through public `houmao-server` routes
After lane provisioning, the suite SHALL verify managed-agent discovery and inspection through the public `houmao-server` routes rather than through wrapper CLIs or direct filesystem scraping.

At minimum, the suite SHALL verify:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/state/detail`

For TUI lanes, the suite SHALL verify `/state/detail` response field `detail.transport = "tui"`.

For headless lanes, the suite SHALL verify `/state/detail` response field `detail.transport = "headless"`.

#### Scenario: Shared discovery lists all four launched lanes
- **WHEN** the suite provisions all four managed-agent lanes successfully
- **THEN** `GET /houmao/agents` returns all four lanes
- **AND THEN** each returned entry is identifiable by the suite’s recorded lane identity and transport kind

#### Scenario: Per-lane detail reflects the correct managed transport
- **WHEN** the suite inspects one launched lane through `GET /houmao/agents/{agent_ref}/state/detail`
- **THEN** the returned detail payload identifies the lane’s actual transport
- **AND THEN** TUI lanes report `transport = "tui"` while headless lanes report `transport = "headless"`

### Requirement: Canonical live suite SHALL verify prompt submission through the transport-neutral managed-agent request route
The suite SHALL submit one prompt to every launched lane through `POST /houmao/agents/{agent_ref}/requests`.

The suite SHALL verify that prompt submission succeeds through the shared transport-neutral request route for both TUI and headless lanes.

The suite SHALL verify post-request state progression through `houmao-server` state routes.

For headless lanes, the suite SHALL also verify durable turn evidence when the accepted request response returns a headless turn handle.

#### Scenario: TUI prompt submission is accepted and changes observable server state
- **WHEN** the suite submits one prompt to a launched TUI lane through `POST /houmao/agents/{agent_ref}/requests`
- **THEN** the request is accepted through the shared managed-agent request route
- **AND THEN** later `GET /houmao/agents/{agent_ref}/state` output shows observable post-request progress through shared state fields such as an active turn, turn phase progression, or `last_turn.result` moving beyond `"none"`

#### Scenario: Headless prompt submission is accepted and exposes durable turn evidence
- **WHEN** the suite submits one prompt to a launched headless lane through `POST /houmao/agents/{agent_ref}/requests`
- **THEN** the request is accepted through the shared managed-agent request route
- **AND THEN** if the accepted response includes a `headless_turn_id`, the suite can inspect that turn through the headless turn-status route until it reaches a terminal state

### Requirement: Canonical live suite SHALL stop all launched lanes through the managed-agent stop route
The suite SHALL stop every launched lane through `POST /houmao/agents/{agent_ref}/stop`.

For TUI lanes, the suite SHALL treat the managed-agent stop route as the authoritative stop action rather than deleting raw CAO sessions directly as the primary control path.

After lane cleanup finishes, the suite SHALL terminate its owned `houmao-server` process and preserve that shutdown result in the run artifacts.

After the suite finishes, it SHALL preserve the stop results and any best-effort cleanup evidence in the run artifacts.

#### Scenario: Successful suite run stops every lane through `houmao-server`
- **WHEN** the suite completes a successful verification run
- **THEN** it stops each launched lane through `POST /houmao/agents/{agent_ref}/stop`
- **AND THEN** it terminates the owned `houmao-server` process after lane cleanup completes
- **AND THEN** the run artifacts record one stop result per launched lane plus the server-shutdown result

#### Scenario: Partial-failure cleanup still preserves stop evidence
- **WHEN** one or more lanes fail after the suite has already started `houmao-server`
- **THEN** the suite performs best-effort managed-agent stop and cleanup for the lanes it already created
- **AND THEN** it still performs owned-server shutdown after that cleanup phase
- **AND THEN** it preserves the cleanup results, server-shutdown result, and failure evidence in the run artifacts

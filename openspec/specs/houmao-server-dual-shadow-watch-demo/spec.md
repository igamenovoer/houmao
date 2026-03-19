## Purpose
Define the standalone Houmao-owned dual shadow-watch demo pack that validates the `houmao-server + houmao-srv-ctrl` pair through an interactive Claude/Codex monitoring workflow.

## Requirements

### Requirement: Repository SHALL provide a standalone Houmao-server dual shadow-watch demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo-pack directory at `scripts/demo/houmao-server-dual-shadow-watch/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `scripts/demo_driver.py`
- `scripts/watch_dashboard.py`

The pack SHALL implement its own operator workflow and SHALL NOT source, invoke, or depend on sibling demo-pack shell wrappers to perform startup, monitoring, inspection, or teardown.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-dual-shadow-watch/`
- **THEN** the required files are present
- **AND THEN** the pack can be understood and run from that directory without requiring another demo pack as its orchestrator

### Requirement: Demo startup SHALL provision demo-owned projection dummy-project workdirs and a demo-owned Houmao server
The Houmao-server dual shadow-watch demo SHALL provision a tracked projection-oriented dummy-project fixture from `tests/fixtures/dummy-projects/` into demo-owned per-agent workdirs under the run root.

At minimum, startup SHALL create isolated workdirs for the Claude and Codex sessions rather than pointing either session at the repository checkout.

Each provisioned workdir SHALL be initialized as a fresh standalone git-backed workspace for that run. The workdir SHALL NOT be a git worktree of the main repository and SHALL NOT reuse tracked `.git` metadata from the source fixture.

The same start flow SHALL start one demo-owned `houmao-server` instance on a demo-selected loopback base URL with a demo-local runtime root rather than assuming an unrelated operator-managed `houmao-server` instance already exists.

#### Scenario: Startup creates isolated dummy-project workdirs and a demo-owned server
- **WHEN** the operator starts the Houmao-server dual shadow-watch demo
- **THEN** the run root contains separate demo-owned project copies for the Claude and Codex sessions
- **AND THEN** each session starts from its own copied dummy-project workdir
- **AND THEN** neither session points at the repository checkout as its live agent workdir
- **AND THEN** the demo starts or verifies one demo-owned `houmao-server` listener before attempting any agent launch

### Requirement: Demo SHALL expose one canonical interactive runner surface with fail-fast preflight and bounded lifecycle behavior
The canonical operator path for this demo SHALL be:

- start the demo through the demo-owned runner surface,
- attach to the Claude, Codex, and monitor tmux sessions,
- interact with the live TUIs while observing the monitor,
- inspect state and artifacts, and
- stop the run cleanly.

Before the runner surface attempts launch, it SHALL check required prerequisites and fail fast with a non-zero result plus a diagnostic message when a required prerequisite is missing or unusable.

At minimum, that preflight SHALL cover the required local command surfaces, the demo-owned loopback listener selection, and the required agent/profile/provider configuration for the selected live sessions.

Any wait for server start, delegated session launch, monitor readiness, inspect readiness, or stop completion SHALL be bounded by an explicit timeout rather than hanging indefinitely.

#### Scenario: Missing prerequisite fails before launch work begins
- **WHEN** the operator starts the demo and a required binary, profile, port, or provider configuration is unavailable
- **THEN** the runner exits with a non-zero result before attempting a live launch
- **AND THEN** the failure output identifies the missing or unusable prerequisite

#### Scenario: Lifecycle wait times out explicitly instead of hanging
- **WHEN** the demo starts or stops and the required Houmao server or live session state does not become ready before the configured timeout
- **THEN** the runner exits with a non-zero timeout failure
- **AND THEN** the run preserves logs or artifacts useful for diagnosing where the wait stalled

### Requirement: Demo startup SHALL launch one Claude session, one Codex session, and one monitor session through the supported Houmao pair
The start flow SHALL launch:

- one Claude session through `houmao-srv-ctrl launch`,
- one Codex session through `houmao-srv-ctrl launch`, and
- one separate tmux monitor session.

For supported Claude and Codex sessions in this pack, the effective persisted Houmao session identity SHALL remain `houmao_server_rest` and the effective parsing posture SHALL remain `shadow_only`.

Startup SHALL persist structured state for the run, including at minimum the run root, the Houmao server base URL, the two session names, each terminal id, each tmux session name, and the monitor tmux session name.

Startup SHALL surface attach commands for the Claude session, the Codex session, and the monitor session so the operator can manually interact with both TUIs while watching the dashboard.

#### Scenario: Successful startup surfaces three live tmux sessions through the Houmao pair
- **WHEN** the operator runs the demo start command with prerequisites satisfied
- **THEN** the demo launches one Claude session and one Codex session through `houmao-srv-ctrl` against the demo-owned `houmao-server`
- **AND THEN** the resulting tracked sessions are registered in `houmao-server`
- **AND THEN** the demo starts a separate tmux session for the monitor dashboard
- **AND THEN** startup output includes attach commands for the Claude session, the Codex session, and the monitor session

#### Scenario: Startup persists Houmao-server-backed session identity
- **WHEN** the operator starts the Houmao-server dual shadow-watch demo
- **THEN** the persisted run state records the Houmao server base URL plus the launched session and terminal identities
- **AND THEN** follow-up demo commands treat `houmao-server` as the session authority instead of bypassing it through raw CAO control paths

### Requirement: Monitor SHALL consume Houmao-server tracked state every 0.5 seconds and render a `rich` dashboard
The monitor process SHALL poll each tracked terminal through `houmao-server` every `0.5` seconds.

For each poll, the monitor SHALL consume the authoritative tracked-state payload exposed by `houmao-server` for that terminal. The monitor SHALL NOT require direct CAO terminal-output polling or a demo-local parser stack in order to render current live state.

The live monitor session SHALL render a `rich` dashboard that makes it easy to compare both agents side by side. At minimum, the dashboard SHALL show each session's current transport/process/parse state, parser-facing surface fields, lifecycle state, and lifecycle timing needed for operator validation.

The monitor SHALL keep a rolling transition log in the display so an operator can see state changes as they happen rather than only the latest steady-state row.

#### Scenario: Monitor updates current server-owned state on a fixed cadence
- **WHEN** the monitor session is active while the demo is running
- **THEN** it refreshes the displayed state for both agents every `0.5` seconds
- **AND THEN** the dashboard reflects the latest tracked state returned by `houmao-server` for each terminal

### Requirement: Change SHALL define HTT case plans and an implemented autotest layout for the demo
The change SHALL store design-phase HTT case plans under `openspec/changes/add-houmao-server-dual-shadow-watch-demo/testplans/`.

At minimum, the change SHALL define case plans for:

- a preflight/start/inspect/stop lifecycle case, and
- an interactive shadow-state validation case.

Each case plan SHALL:

- cover both the automatic and interactive variants for that case,
- describe the intended implemented assets,
- describe the intended runner surface,
- describe ordered steps,
- describe expected evidence,
- describe failure signals, and
- include at least one Mermaid `sequenceDiagram`.

The intended implemented test assets SHALL live under `scripts/demo/houmao-server-dual-shadow-watch/autotest/` and SHALL include:

- a standalone harness,
- one or more automatic case scripts,
- one or more interactive case guides,
- and shared helpers under `autotest/helpers/`.

Interactive guides SHALL be independent step-by-step procedures. They SHALL NOT reduce to instructions that only say to run the automatic script.

#### Scenario: Design-phase case plans exist for both automatic and interactive testing
- **WHEN** a maintainer inspects `openspec/changes/add-houmao-server-dual-shadow-watch-demo/testplans/`
- **THEN** the change contains case plans for the automatic preflight/lifecycle path and the interactive shadow-state validation path
- **AND THEN** each case plan includes a Mermaid sequence diagram plus explicit automatic and interactive test guidance

#### Scenario: Intended implemented autotest layout is explicit
- **WHEN** a maintainer reads the change artifacts before implementation
- **THEN** they can tell where the future standalone harness, automatic case scripts, interactive guides, and shared helpers are supposed to live
- **AND THEN** the interactive guides are described as first-class procedures rather than wrappers around the automatic scripts

### Requirement: Monitor SHALL expose server-owned parser, lifecycle, and timing fields needed for manual validation
For each agent, the live monitor SHALL expose at minimum:

- `transport_state`
- `process_state`
- `parse_status`
- parser availability
- parser business state
- parser input mode
- parser UI context
- readiness state
- completion state
- projection-change indicator
- lifecycle timing information needed to understand unknown, candidate-complete, and stalled transitions
- recent anomaly codes

The monitor SHOULD also surface concise session metadata such as tool, terminal id, tmux session name, parser preset/version, detail text, and a short dialog tail when that information is available from `houmao-server`.

#### Scenario: Operator can distinguish parser state from lifecycle state without local reclassification
- **WHEN** the operator watches the monitor during manual interaction
- **THEN** the display separates raw tracked parser-facing fields from higher-level readiness and completion state
- **AND THEN** the operator can tell whether a surprising lifecycle transition came from transport loss, TUI-down state, parser availability, operator-blocked state, unknown timing, or projection change
- **AND THEN** that interpretation comes from server-owned tracked state rather than a second demo-local tracker

### Requirement: Demo SHALL persist server-consumer monitor evidence and stop cleanly
The demo run SHALL persist machine-readable monitor artifacts under the run root.

At minimum, the monitor SHALL write:

- one sample artifact stream covering every poll tick, and
- one transition artifact stream covering server-observed state changes.

The canonical runner surface and any implemented automatic case SHALL preserve deterministic or caller-provided output locations for logs and evidence rather than scattering test artifacts into unrelated repository paths.

The demo SHALL provide a stop flow that terminates both launched sessions through the Houmao server authority, terminates the monitor session, stops the demo-owned `houmao-server` when this run started it, and preserves the recorded monitor artifacts and logs for later inspection.

#### Scenario: Stop preserves state-watch evidence
- **WHEN** the operator stops the Houmao-server dual shadow-watch demo after watching live state transitions
- **THEN** both agent sessions and the monitor session are terminated
- **AND THEN** any demo-owned `houmao-server` process started for that run is stopped
- **AND THEN** the run root still contains the persisted monitor samples and transitions for post-run inspection

### Requirement: README SHALL teach the Houmao-owned manual state-validation workflow
The demo-pack README SHALL document:

- prerequisites,
- the standalone purpose of the pack,
- the dummy-project workdir posture,
- the supported `houmao-server + houmao-srv-ctrl` pair boundary,
- the start, inspect, attach, and stop workflow,
- the meaning of the displayed lifecycle and timing states, and
- concrete manual interactions the operator can perform to validate state changes.

The README SHALL make clear that the monitor is intended to validate live Houmao-owned parser and lifecycle behavior while the user manually interacts with Claude Code and Codex TUIs.

#### Scenario: Maintainer can follow the README to perform a Houmao-server-based manual validation run
- **WHEN** a maintainer follows the README from a fresh checkout with prerequisites satisfied
- **THEN** they can start the demo, attach to the Claude and Codex sessions, watch the monitor session, and stop the run without hidden setup steps
- **AND THEN** the README explains that `houmao-server` is the authoritative live tracking surface for what the monitor displays

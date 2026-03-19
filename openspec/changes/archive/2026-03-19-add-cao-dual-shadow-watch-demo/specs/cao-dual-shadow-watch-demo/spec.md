## ADDED Requirements

### Requirement: Repository SHALL provide a standalone dual shadow-watch demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo-pack directory at `scripts/demo/cao-dual-shadow-watch/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `scripts/demo_driver.py`
- `scripts/watch_dashboard.py`

The pack SHALL implement its own operator workflow and SHALL NOT source, invoke, or depend on sibling demo-pack shell wrappers to perform startup, monitoring, inspection, or teardown.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/cao-dual-shadow-watch/`
- **THEN** the required files are present
- **AND THEN** the pack can be understood and run from that directory without requiring another demo pack as its orchestrator

### Requirement: Demo startup SHALL provision demo-owned projection dummy-project workdirs
The dual shadow-watch demo SHALL provision a tracked projection-oriented dummy-project fixture from `tests/fixtures/dummy-projects/` into demo-owned per-agent workdirs under the run root.

At minimum, startup SHALL create isolated workdirs for the Claude and Codex sessions rather than pointing either session at the repository checkout.

Each provisioned workdir SHALL be initialized as a fresh standalone git-backed workspace for that run. The workdir SHALL NOT be a git worktree of the main repository and SHALL NOT reuse tracked `.git` metadata from the source fixture.

#### Scenario: Startup creates isolated dummy-project workdirs for both agents
- **WHEN** the operator starts the dual shadow-watch demo
- **THEN** the run root contains separate demo-owned project copies for the Claude and Codex sessions
- **AND THEN** each session starts from its own copied dummy-project workdir
- **AND THEN** neither session points at the repository checkout as its live agent workdir

### Requirement: Demo startup SHALL launch one Claude session, one Codex session, and one monitor session in `shadow_only`
The start flow SHALL manage one shared loopback CAO server for the demo run and SHALL launch:

- one Claude Code `cao_rest` session,
- one Codex `cao_rest` session, and
- one separate tmux monitor session.

Both CAO runtime sessions SHALL be started with `--cao-parsing-mode shadow_only`.

Startup SHALL persist structured state for the run, including at minimum the run root, the two agent identities, each session's tmux session name, each terminal id, and the monitor tmux session name.

Startup SHALL surface attach commands for all three tmux sessions so the operator can manually interact with the agent TUIs while watching the monitor.

#### Scenario: Successful startup surfaces three live sessions
- **WHEN** the operator runs the demo start command with prerequisites satisfied
- **THEN** houmao starts one Claude CAO session and one Codex CAO session with `shadow_only`
- **AND THEN** houmao starts a separate tmux session for the monitor dashboard
- **AND THEN** startup output includes attach commands for the Claude session, the Codex session, and the monitor session

#### Scenario: Startup persists `shadow_only` as the demo posture
- **WHEN** the operator starts the dual shadow-watch demo
- **THEN** the persisted run state records `shadow_only` as the effective parsing posture for both launched sessions
- **AND THEN** follow-up demo commands do not silently downgrade to `cao_only`

### Requirement: Monitor SHALL poll both live terminals every 0.5 seconds and render a `rich` dashboard
The monitor process SHALL poll each live CAO terminal every 0.5 seconds.

For each poll, the monitor SHALL fetch `mode=full` output for the target terminal and parse it with the runtime `ShadowParserStack` selected for that tool.

The live monitor session SHALL render a `rich` dashboard that makes it easy to compare both agents side-by-side. At minimum, the dashboard SHALL show each session's current parser-facing surface state and the derived lifecycle state used for operator validation.

The monitor SHALL keep a rolling transition log in the display so an operator can see state changes as they happen rather than only the latest steady-state row.

#### Scenario: Monitor updates current parser state on a fixed cadence
- **WHEN** the monitor session is active while the demo is running
- **THEN** it refreshes the displayed state for both agents every 0.5 seconds
- **AND THEN** the dashboard reflects the latest parsed `mode=full` terminal snapshot for each tool

### Requirement: Monitor SHALL expose parser and lifecycle fields needed for `shadow_only` validation
For each agent, the live monitor SHALL expose at minimum:

- parser availability
- parser business state
- parser input mode
- parser UI context
- readiness state
- completion state
- projection-change indicator
- baseline-invalidation indicator
- recent anomaly codes

The monitor SHOULD also surface concise session metadata such as tool, terminal id, tmux session name, parser preset/version, and a short projected-dialog tail when that information is available.

#### Scenario: Operator can distinguish parser state from lifecycle state
- **WHEN** the operator watches the monitor during manual interaction
- **THEN** the display separates raw parser fields such as `business_state` and `input_mode` from higher-level readiness and completion state
- **AND THEN** the operator can see whether a surprising lifecycle transition came from parser availability, operator-blocked state, unknown state, or projection change

### Requirement: Monitor SHALL derive readiness and completion states from shadow-only lifecycle semantics
The monitor SHALL derive readiness states using the same shadow-surface posture as runtime `shadow_only` monitoring:

- `failed` for unsupported or disconnected surfaces
- `blocked` for operator-blocked surfaces
- `unknown` and `stalled` for unknown-for-stall surfaces
- `ready` only for submit-ready surfaces
- `waiting` for other known non-ready surfaces

The monitor SHALL derive completion state over time using a ready-baseline plus post-submit activity model:

- `inactive` before a completion watch is armed
- `in_progress` after post-submit activity is observed and the session remains working
- `candidate_complete` when the session returns to submit-ready after post-submit activity but before the stability window has elapsed
- `completed` only after the configured stability window elapses without another reset
- `blocked`, `failed`, `unknown`, and `stalled` when the parsed surface enters those states during completion monitoring

By default, the monitor SHALL use:

- `unknown_to_stalled_timeout_seconds = 30.0`
- `completion_stability_seconds = 1.0`

The completion tracker SHALL reset its stability timing when the normalized projection changes or when the parser returns to a non-complete state before the stability window expires.

#### Scenario: Operator-blocked surface is shown as blocked instead of ready
- **WHEN** a live terminal surface requires operator intervention
- **THEN** the monitor shows `blocked` readiness or completion state for that agent
- **AND THEN** it does not report that surface as ready or completed

#### Scenario: Sustained idle after work becomes completed
- **WHEN** the monitor has armed completion tracking from a previously ready baseline
- **AND WHEN** the agent later becomes submit-ready after post-submit activity
- **AND WHEN** the parsed surface remains stable for `completion_stability_seconds`
- **THEN** the monitor shows the session as `completed`

#### Scenario: Continuous unknown state enters stalled
- **WHEN** the parsed surface remains unknown for stall purposes continuously for `unknown_to_stalled_timeout_seconds`
- **THEN** the monitor shows `stalled` for the affected lifecycle path
- **AND THEN** it records that transition as an explicit stalled event

### Requirement: Demo SHALL persist monitor evidence and stop cleanly
The demo run SHALL persist machine-readable monitor artifacts under the run root.

At minimum, the monitor SHALL write:

- one sample artifact stream covering every poll tick, and
- one transition artifact stream covering only lifecycle or parser-state changes.

The demo SHALL provide a stop flow that terminates both runtime sessions, terminates the monitor session, and preserves the recorded monitor artifacts and logs for later inspection.

#### Scenario: Stop preserves state-watch evidence
- **WHEN** the operator stops the dual shadow-watch demo after watching live state transitions
- **THEN** both agent sessions and the monitor session are terminated
- **AND THEN** the run root still contains the persisted monitor samples and transitions for post-run inspection

### Requirement: README SHALL teach the manual state-validation workflow
The demo-pack README SHALL document:

- prerequisites,
- the standalone purpose of the pack,
- the dummy-project workdir posture,
- the `shadow_only` requirement,
- the start, inspect, attach, and stop workflow,
- the meaning of the displayed readiness and completion states, and
- concrete manual interactions the operator can perform to validate state changes.

The README SHALL make clear that the monitor is intended to validate live shadow parser and lifecycle behavior while the user manually interacts with Claude Code and Codex TUIs.

#### Scenario: Maintainer can follow the README to perform a manual shadow-state validation run
- **WHEN** a maintainer follows the README from a fresh checkout with prerequisites satisfied
- **THEN** they can start the demo, attach to the Claude and Codex sessions, watch the monitor session, and stop the run without hidden setup steps
- **AND THEN** the README explains which visible transitions the maintainer should expect to see while interacting with the live TUIs

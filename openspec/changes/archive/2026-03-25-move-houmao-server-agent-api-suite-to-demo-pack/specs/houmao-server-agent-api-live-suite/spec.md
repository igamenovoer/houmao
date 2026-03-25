## ADDED Requirements

### Requirement: Repository SHALL provide the canonical direct managed-agent API validator as a self-contained demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo pack at `scripts/demo/houmao-server-agent-api-demo-pack/` for direct `houmao-server` managed-agent API validation.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `autotest/run_autotest.sh`
- `inputs/`
- `expected_report/report.json`
- `scripts/sanitize_report.py`
- `scripts/verify_report.py`
- one pack-owned Python helper entrypoint or helper module surface used by the shell wrappers
- `agents/`
- `autotest/case-*.sh`
- `autotest/case-*.md`
- `autotest/helpers/`

The pack SHALL own its tracked native selector inputs, role prompts, config skeletons, and tutorial inputs instead of relying on `tests/manual/` or `tests/fixtures/agents/` as the source of truth for the canonical workflow.

#### Scenario: Demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-agent-api-demo-pack/`
- **THEN** the required pack files and directories are present
- **AND THEN** the pack can be understood and run from that directory as the canonical direct `houmao-server` API validation workflow

#### Scenario: Canonical pack does not depend on the old manual suite layout
- **WHEN** a maintainer inspects the canonical direct managed-agent API validation assets
- **THEN** the tracked selector and tutorial inputs used by that workflow live under the new demo-pack directory
- **AND THEN** the workflow does not require `tests/manual/manual_houmao_server_agent_api_live_suite.py` or `tests/fixtures/agents/` as its documented source of truth

### Requirement: Demo pack SHALL provide pack-local real-agent HTT cases through a standalone harness
The demo pack SHALL provide a standalone real-agent HTT harness at `scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh`.

The initial supported HTT case set SHALL include:

- `real-agent-preflight`
- `real-agent-all-lanes-auto`
- `real-agent-interrupt-recovery`

For each supported case, the pack SHALL provide:

- one executable implementation at `autotest/case-*.sh`, and
- one same-basename interactive companion guide at `autotest/case-*.md`

The interactive guides SHALL be independent step-by-step procedures. They SHALL explain what the agent should do, what to observe, and what success or failure looks like at each step. They SHALL NOT reduce to "run the automatic script."

Shared shell libraries and reusable helper functions used by multiple HTT cases SHALL live under `autotest/helpers/`.

`run_demo.sh` SHALL remain the tutorial/demo wrapper and SHALL NOT own HTT case selection.

#### Scenario: Maintainer can discover the supported pack-local HTT assets
- **WHEN** a maintainer inspects `scripts/demo/houmao-server-agent-api-demo-pack/autotest/`
- **THEN** the directory contains one `case-*.sh` executable and one same-basename `case-*.md` companion document per supported HTT case
- **AND THEN** shared shell libraries and helper functions live under `autotest/helpers/`
- **AND THEN** `autotest/run_autotest.sh` is the documented harness that selects and runs those cases

#### Scenario: Harness accepts explicit case execution
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-all-lanes-auto --demo-output-dir <path>`
- **THEN** the harness dispatches to the matching pack-owned case implementation
- **AND THEN** the selected case writes its machine-readable result and per-phase logs under that selected demo output directory
- **AND THEN** the caller does not need the old manual suite to reach the canonical HTT path

### Requirement: Demo pack SHALL expose stepwise, unattended, and HTT validation surfaces
The demo pack SHALL expose one stepwise operator workflow through `run_demo.sh` and one pack-local real-agent HTT workflow through `autotest/run_autotest.sh`.

At minimum, `run_demo.sh` SHALL support:

- `start`
- `inspect`
- `prompt`
- `interrupt`
- `verify`
- `stop`
- `auto`

The `auto` workflow SHALL execute `start -> inspect -> prompt -> verify -> stop` for the selected lanes.

`run_demo.sh auto` SHALL be the canonical non-interactive demo path for this capability.

`autotest/run_autotest.sh --case real-agent-all-lanes-auto` SHALL exercise that same canonical path with stricter preflight, bounded phase execution, machine-detectable pass/fail status, and preserved per-phase evidence.

The stepwise workflow SHALL preserve enough state under the selected output root for later commands to target the same demo-owned `houmao-server` authority and the same launched lanes after `start`.

The HTT workflow SHALL preserve machine-readable case results plus per-phase logs under `<demo-output-dir>/control/autotest/` and `<demo-output-dir>/logs/autotest/`.

#### Scenario: Stepwise commands reuse one selected run after startup
- **WHEN** an operator runs `start` and later runs `inspect`, `prompt`, `interrupt`, `verify`, or `stop`
- **THEN** those later commands target the same persisted run state and owned `houmao-server` authority created by `start`
- **AND THEN** the operator does not need to rediscover lane identities manually between those commands

#### Scenario: Pack-local HTT runner preserves case evidence
- **WHEN** a maintainer runs `autotest/run_autotest.sh`
- **THEN** the runner writes machine-readable case results under `<demo-output-dir>/control/autotest/`
- **AND THEN** it also preserves per-phase command logs under `<demo-output-dir>/logs/autotest/` for debugging live-agent failures

#### Scenario: Missing prerequisites block the HTT harness before startup
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-preflight --demo-output-dir <path>` without one required executable, credential input, pack-owned selector asset, or safe output-root posture
- **THEN** the case exits non-zero before any `houmao-server` startup or lane provisioning begins
- **AND THEN** the failure output identifies the missing or unsafe prerequisite directly

### Requirement: Demo-pack verification artifacts SHALL be sanitized and snapshotable
The demo pack SHALL build a verification report for the canonical workflow and SHALL compare only sanitized content against the tracked expected report.

At minimum, verification SHALL produce:

- `report.json`
- `report.sanitized.json`
- comparison against `expected_report/report.json`

Snapshot refresh mode SHALL update the tracked expected report using sanitized content only.

#### Scenario: Verify compares sanitized content to the tracked expected report
- **WHEN** an operator runs the demo-pack `verify` command after a successful run
- **THEN** the pack writes both raw and sanitized verification artifacts under the selected output root
- **AND THEN** it compares the sanitized content against `expected_report/report.json`

#### Scenario: Snapshot refresh updates only sanitized expected output
- **WHEN** a maintainer runs the demo-pack verification flow with snapshot-refresh enabled
- **THEN** the pack refreshes `expected_report/report.json` from sanitized content only
- **AND THEN** the snapshot update does not depend on committing raw timestamps, ids, or absolute paths

## MODIFIED Requirements

### Requirement: Canonical live suite SHALL provision an isolated `houmao-server` authority for managed-agent API verification
The system SHALL provide one canonical direct `houmao-server` managed-agent API validation workflow through the demo pack.

That workflow SHALL start a real `houmao-server` subprocess under one pack-owned output root with isolated runtime, registry, jobs, log, and home directories.

The workflow SHALL use a pack-local generated output root under `scripts/demo/houmao-server-agent-api-demo-pack/outputs/` by default and SHALL allow an operator-provided output-root override path.

The workflow SHALL fail before server startup if required local executables, including `tmux` plus the selected provider executables, or required credential material for the selected live lanes are missing.

For Codex lanes in this capability version, the workflow SHALL treat API-key-mode credential inputs as required prerequisites.

The workflow SHALL resolve startup selectors and related launch assets from the demo pack's owned `agents/` tree rather than from ambient shell state or test-fixture-only paths.

The workflow SHALL verify `GET /health` on its owned `houmao-server` before any lane provisioning begins.

The workflow SHALL preserve its output-root artifacts after both success and failure so operators can inspect logs, HTTP snapshots, and lane state without re-running the pack.

#### Scenario: Demo-pack startup provisions a real isolated `houmao-server`
- **WHEN** an operator starts the canonical demo pack with valid prerequisites
- **THEN** the pack starts one real `houmao-server` under a pack-owned isolated output root
- **AND THEN** if the operator did not provide an override path, that output root lives under the pack's generated `outputs/` tree
- **AND THEN** the pack verifies `GET /health` successfully before lane provisioning starts
- **AND THEN** the pack records the selected API base URL plus pack-owned runtime, registry, jobs, and log directories under that output root

#### Scenario: Missing prerequisites block the pack before server startup
- **WHEN** an operator starts the pack without `tmux`, without one selected provider executable, or without one required credential input for a selected lane
- **THEN** the pack fails before starting `houmao-server`
- **AND THEN** the failure output identifies the missing prerequisite directly

#### Scenario: Startup uses pack-owned launch assets
- **WHEN** the pack starts one direct managed-agent API validation run
- **THEN** the selector resolution and related launch assets come from the pack-owned `agents/` tree
- **AND THEN** the run does not rely on a separately exported `AGENTSYS_AGENT_DEF_DIR` from an unrelated shell or test harness

### Requirement: Canonical live suite SHALL launch four direct managed-agent lanes without gateway
The canonical workflow SHALL support both one all-lanes aggregate run and operator-selected per-lane runs in its first demo-pack version.

The workflow SHALL cover four real managed-agent lanes in its first version:

- Claude TUI
- Codex TUI
- Claude headless
- Codex headless

The workflow SHALL create TUI lanes through the CAO-compatible creation path plus managed-agent registration, and SHALL create headless lanes through the native headless managed-agent launch route.

The workflow SHALL create TUI lanes with an explicit configurable CAO session-creation timeout budget rather than relying on the REST-client implicit default.

The workflow SHALL copy one tracked pack-owned dummy project or equivalent minimal workdir fixture into the selected output root and SHALL launch each selected lane against a run-owned copied workdir rather than the repository checkout.

The workflow SHALL NOT attach or depend on a gateway for any of those lanes in this capability version.

#### Scenario: Operator selects one subset of lanes for a live run
- **WHEN** an operator starts the pack while selecting one subset of the supported lanes
- **THEN** the pack provisions only the selected lanes
- **AND THEN** the same discovery, request, verification, and stop rules apply to that selected subset

#### Scenario: TUI lanes are admitted through creation plus registration
- **WHEN** the pack provisions one Claude TUI lane or one Codex TUI lane
- **THEN** it creates the TUI session through the CAO-compatible session-creation route
- **AND THEN** it registers that launched session through the managed-agent registration route so the lane becomes addressable on `/houmao/agents/*`

#### Scenario: Headless lanes are admitted through the native managed-agent launch route
- **WHEN** the pack provisions one Claude headless lane or one Codex headless lane
- **THEN** it launches that lane through `POST /houmao/agents/headless/launches`
- **AND THEN** the launched lane becomes addressable on `/houmao/agents/*` without requiring CAO session registration

#### Scenario: Selected lanes run from copied demo-owned workdirs
- **WHEN** the pack provisions selected lanes for one run
- **THEN** each selected lane receives a copied run-owned workdir derived from the pack's tracked minimal project inputs
- **AND THEN** the pack does not target the main repository checkout as the live lane working directory

### Requirement: Canonical live suite SHALL verify managed-agent discovery and state through public `houmao-server` routes
After lane provisioning, the canonical workflow SHALL verify managed-agent discovery and inspection through the public `houmao-server` routes rather than through wrapper CLIs or direct filesystem scraping.

At minimum, the workflow SHALL verify:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `GET /houmao/agents/{agent_ref}/history`

For TUI lanes, the workflow SHALL verify `/state/detail` response field `detail.transport = "tui"`.

For headless lanes, the workflow SHALL verify `/state/detail` response field `detail.transport = "headless"`.

The stepwise `inspect` surface SHALL present those server-owned discovery and state results for the selected run. When parser-derived dialog tail is exposed for TUI lanes, it SHALL come from `GET /houmao/terminals/{terminal_id}/state` and SHALL remain opt-in rather than default output.

#### Scenario: Shared discovery lists all launched lanes
- **WHEN** the pack provisions all selected managed-agent lanes successfully
- **THEN** `GET /houmao/agents` returns those launched lanes
- **AND THEN** each returned entry is identifiable by the pack's recorded lane identity and transport kind

#### Scenario: Per-lane detail reflects the correct managed transport
- **WHEN** the pack inspects one launched lane through `GET /houmao/agents/{agent_ref}/state/detail`
- **THEN** the returned detail payload identifies the lane's actual transport
- **AND THEN** TUI lanes report `transport = "tui"` while headless lanes report `transport = "headless"`

#### Scenario: Inspect uses server-owned history and optional dialog-tail surfaces
- **WHEN** an operator runs `inspect` for an active demo-pack run
- **THEN** the pack reads bounded managed-agent history through `GET /houmao/agents/{agent_ref}/history`
- **AND THEN** any optional parser-derived dialog tail comes from `GET /houmao/terminals/{terminal_id}/state`
- **AND THEN** the pack does not run a second demo-local parser or tracker to classify live state

### Requirement: Canonical live suite SHALL verify prompt submission through the transport-neutral managed-agent request route
The canonical workflow SHALL validate transport-neutral managed-agent request submission through `POST /houmao/agents/{agent_ref}/requests`.

The workflow SHALL submit one prompt to every launched lane through that shared route.

The stepwise demo-pack surface SHALL also expose explicit interrupt validation through the same managed-agent request route using `request_kind = interrupt`.

The workflow SHALL verify post-request state progression through `houmao-server` state routes.

For headless lanes, the workflow SHALL also verify durable turn evidence when the accepted request response returns a headless turn handle.

#### Scenario: TUI prompt submission is accepted and changes observable server state
- **WHEN** the pack submits one prompt to a launched TUI lane through `POST /houmao/agents/{agent_ref}/requests`
- **THEN** the request is accepted through the shared managed-agent request route
- **AND THEN** later `GET /houmao/agents/{agent_ref}/state` output shows observable post-request progress through shared state fields such as an active turn, turn phase progression, or `last_turn.result` moving beyond `"none"`

#### Scenario: Headless prompt submission is accepted and exposes durable turn evidence
- **WHEN** the pack submits one prompt to a launched headless lane through `POST /houmao/agents/{agent_ref}/requests`
- **THEN** the request is accepted through the shared managed-agent request route
- **AND THEN** if the accepted response includes a `headless_turn_id`, the pack can inspect that turn through the headless turn-status route until it reaches a terminal state

#### Scenario: Interrupt validation uses the shared managed-agent request route
- **WHEN** an operator runs the pack interrupt action while one selected lane has active interruptible work
- **THEN** the pack submits the interrupt through `POST /houmao/agents/{agent_ref}/requests`
- **AND THEN** the request body uses `request_kind = interrupt`
- **AND THEN** the resulting artifact records the server-returned disposition and follow-up state evidence

#### Scenario: Interrupt HTT case preserves post-interrupt evidence
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-interrupt-recovery --demo-output-dir <path>`
- **THEN** the case starts its tracked interrupt lane set, submits a long-running prompt, and issues `request_kind = interrupt` through the shared managed-agent request route
- **AND THEN** it preserves request, state, history, and stop artifacts that show whether the interrupt was accepted and how the selected lanes progressed afterward

### Requirement: Canonical live suite SHALL stop all launched lanes through the managed-agent stop route
The canonical workflow SHALL stop every launched lane through `POST /houmao/agents/{agent_ref}/stop`.

For TUI lanes, the workflow SHALL treat the managed-agent stop route as the authoritative stop action rather than deleting raw CAO sessions directly as the primary control path.

After lane cleanup finishes, the workflow SHALL terminate its owned `houmao-server` process and preserve that shutdown result in the run artifacts.

After the workflow finishes, it SHALL preserve the stop results and any best-effort cleanup evidence in the run artifacts.

The stepwise `stop` action SHALL also mark the persisted local run state inactive after cleanup succeeds or after a stale-session stop outcome is accepted.

#### Scenario: Successful demo-pack run stops every lane through `houmao-server`
- **WHEN** the pack completes a successful verification run
- **THEN** it stops each launched lane through `POST /houmao/agents/{agent_ref}/stop`
- **AND THEN** it terminates the owned `houmao-server` process after lane cleanup completes
- **AND THEN** the run artifacts record one stop result per launched lane plus the server-shutdown result

#### Scenario: Partial-failure cleanup still preserves stop evidence
- **WHEN** one or more lanes fail after the pack has already started `houmao-server`
- **THEN** the pack performs best-effort managed-agent stop and cleanup for the lanes it already created
- **AND THEN** it still performs owned-server shutdown after that cleanup phase
- **AND THEN** it preserves the cleanup results, server-shutdown result, and failure evidence in the run artifacts

#### Scenario: Stepwise stop marks local state inactive after cleanup
- **WHEN** an operator runs the pack stop command after a started run
- **THEN** the pack tears down any still-launched lanes through the managed-agent stop route or an accepted stale-session outcome
- **AND THEN** it updates the persisted local run state to inactive for that selected output root

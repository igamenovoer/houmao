# passive-server-parallel-validation Specification

## Purpose
Define the canonical Step 7 demo-pack validation contract for running the old `houmao-server` and `houmao-passive-server` in parallel against one shared runtime.

## Requirements

### Requirement: Repository SHALL provide the canonical Step 7 parallel validation demo pack
The repository SHALL provide a self-contained Step 7 validation demo pack at `scripts/demo/passive-server-parallel-validation-demo-pack/`.

At minimum, that directory SHALL contain:

- `README.md`
- `run_demo.sh`
- `autotest/run_autotest.sh`
- `autotest/case-parallel-preflight.sh`
- `autotest/case-parallel-preflight.md`
- `autotest/case-parallel-all-phases-auto.sh`
- `autotest/case-parallel-all-phases-auto.md`
- `inputs/`
- `agents/`
- `scripts/sanitize_report.py`
- `scripts/verify_report.py`
- `expected_report/report.json`
- pack-owned helper code or shared shell libraries needed by the wrappers

The pack SHALL own its tracked launch selectors, tutorial inputs, and run-state handling instead of relying on `tests/manual/` as the canonical Step 7 workflow.

#### Scenario: Demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/passive-server-parallel-validation-demo-pack/`
- **THEN** the required pack files and directories are present
- **AND THEN** the Step 7 workflow can be understood from that directory as the canonical parallel validation surface

#### Scenario: Pack-local validation assets are the source of truth
- **WHEN** a maintainer inspects the Step 7 validation assets
- **THEN** the tracked selector and tutorial inputs used by that workflow live under the new demo-pack directory
- **AND THEN** the workflow does not depend on `tests/manual/` as its documented source of truth

### Requirement: Demo pack SHALL expose stepwise and unattended parallel validation surfaces
The Step 7 demo pack SHALL expose a stepwise operator workflow through `run_demo.sh` and a stricter unattended workflow through `autotest/run_autotest.sh`.

At minimum, `run_demo.sh` SHALL support:

- `start`
- `inspect`
- `gateway`
- `headless`
- `stop`
- `verify`
- `auto`

The `auto` workflow SHALL execute `start -> inspect -> gateway -> headless -> stop -> verify`.

At minimum, `autotest/run_autotest.sh` SHALL support explicit execution of:

- `parallel-preflight`
- `parallel-all-phases-auto`

The unattended runner SHALL preserve machine-readable case results and per-phase logs under the selected output root.

#### Scenario: Stepwise commands reuse one selected run after startup
- **WHEN** an operator runs `start` and later runs `inspect`, `gateway`, `headless`, `stop`, or `verify`
- **THEN** those later commands target the same persisted run state and the same two authority instances created by `start`
- **AND THEN** the operator does not need to rediscover server URLs or agent identities manually between those commands

#### Scenario: Unattended runner accepts explicit case execution
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case parallel-all-phases-auto --demo-output-dir <path>`
- **THEN** the harness dispatches to the matching pack-owned case implementation
- **AND THEN** the selected case writes machine-readable result data and per-phase logs under that selected output directory

### Requirement: Parallel validation SHALL provision isolated dual authorities against one shared runtime root
The Step 7 workflow SHALL start one old `houmao-server` and one `houmao-passive-server` against the same pack-owned shared runtime and registry roots while keeping authority-owned logs and instance state separate.

The workflow SHALL:

- use distinct configurable listen ports for the two authorities,
- verify `GET /health` on both authorities before validation phases begin,
- preserve the selected base URLs plus pack-owned runtime, registry, jobs, and log directories under the run output root, and
- fail before agent provisioning if required executables, credential inputs, or chosen ports are unavailable.

The default port posture SHALL support running the old server on `9889` and the passive server on `9891`, while allowing overrides.

#### Scenario: Startup provisions two live authorities over one shared registry
- **WHEN** an operator starts the Step 7 demo pack with valid prerequisites
- **THEN** the pack starts one old `houmao-server` and one `houmao-passive-server`
- **AND THEN** both authorities point at the same shared runtime and registry roots for agent discovery
- **AND THEN** the pack verifies `GET /health` successfully on both before agent provisioning begins

#### Scenario: Missing prerequisites block startup before any authority is launched
- **WHEN** an operator starts the Step 7 demo pack without one required executable, credential input, or available configured port
- **THEN** the pack fails before agent provisioning begins
- **AND THEN** the failure output identifies the missing or unsafe prerequisite directly

### Requirement: Parallel validation SHALL compare shared interactive discovery and managed-state parity across both authorities
The Step 7 workflow SHALL launch at least one shared interactive validation agent through the local managed-agent launch path so that neither authority owns the agent's admission.

After that launch, the workflow SHALL:

- verify that both authorities list and resolve the same shared interactive agent,
- collect managed-agent summary, detail, and history views for that agent from both authorities,
- compare a documented normalized subset of those views for parity, and
- preserve raw authority responses when the comparison passes or fails.

The parity comparison SHALL treat documented authority-owned metadata as non-blocking and SHALL record any mismatch explicitly in the run report rather than silently ignoring it.

#### Scenario: Shared interactive agent appears on both authorities after local launch
- **WHEN** the Step 7 workflow launches one shared interactive validation agent through the local managed-agent path
- **THEN** both `houmao-server` and `houmao-passive-server` can list and resolve that agent from the shared registry-backed world
- **AND THEN** the workflow records parity results for managed summary, detail, and history views for that shared agent

#### Scenario: State mismatch is reported with preserved evidence
- **WHEN** the two authorities return different normalized managed-state results for the same shared interactive agent
- **THEN** the Step 7 workflow marks that parity check as failed
- **AND THEN** it preserves the raw authority responses and comparison diagnostics in the run evidence instead of hiding the mismatch

### Requirement: Parallel validation SHALL verify passive-server gateway proxy behavior against a shared interactive agent
The Step 7 workflow SHALL provision or attach a live gateway for the shared interactive validation agent so the passive server's gateway proxy surface can be exercised.

The workflow SHALL submit a prompt through the passive server's gateway request path and SHALL verify follow-up state evidence from both authorities for that same shared agent.

#### Scenario: Passive-server gateway proxy drives observable shared-agent progress
- **WHEN** the Step 7 workflow submits a prompt for the shared interactive validation agent through the passive server gateway proxy surface
- **THEN** the request is accepted through the passive server
- **AND THEN** later state or history evidence from both authorities shows observable post-request progress for that same shared agent

### Requirement: Parallel validation SHALL verify passive-server headless publication is visible from the old server
The Step 7 workflow SHALL launch at least one headless validation agent through `POST /houmao/agents/headless/launches` on the passive server.

After that launch, the workflow SHALL verify that the old `houmao-server` can discover and resolve the launched headless agent through the shared-registry world without requiring a separate registration path.

The workflow SHALL preserve passive-server launch evidence plus old-server discovery evidence for that headless agent.

#### Scenario: Passive-server-launched headless agent is visible from the old server
- **WHEN** the Step 7 workflow launches one headless validation agent through the passive server
- **THEN** the passive server reports the launch as successful
- **AND THEN** the old `houmao-server` can later list or resolve that same headless agent through its managed-agent routes
- **AND THEN** the run evidence records both the passive launch response and the old-server visibility result

### Requirement: Parallel validation SHALL verify stop propagation across both authorities
The Step 7 workflow SHALL stop at least one shared validation agent through the passive server's managed stop surface.

After the stop request succeeds, the workflow SHALL verify that the agent no longer appears on either authority and that the shared runtime state no longer presents the agent as live.

#### Scenario: Stopping through the passive server removes the agent from both authorities
- **WHEN** the Step 7 workflow stops one shared validation agent through the passive server
- **THEN** the passive server no longer lists or resolves that agent
- **AND THEN** the old `houmao-server` also no longer lists or resolves that same agent
- **AND THEN** the run report records stop-propagation success or failure explicitly

### Requirement: Parallel validation SHALL preserve sanitized reports and raw evidence for review
The Step 7 workflow SHALL build a verification report for the dual-authority run and SHALL compare only sanitized content against the tracked expected report.

At minimum, verification SHALL produce:

- `report.json`
- `report.sanitized.json`
- raw per-phase HTTP snapshots or equivalent request/response evidence for both authorities
- comparison against `expected_report/report.json`

Snapshot refresh mode SHALL update the tracked expected report from sanitized content only.

#### Scenario: Verify compares sanitized parallel-validation output to the tracked expected report
- **WHEN** an operator runs the Step 7 demo-pack `verify` command after a successful parallel run
- **THEN** the pack writes both raw and sanitized verification artifacts under the selected output root
- **AND THEN** it compares the sanitized content against `expected_report/report.json`

#### Scenario: Snapshot refresh updates only sanitized expected output
- **WHEN** a maintainer runs the Step 7 verification flow with snapshot-refresh enabled
- **THEN** the pack refreshes `expected_report/report.json` from sanitized content only
- **AND THEN** the tracked expected output does not depend on raw timestamps, ids, or absolute paths

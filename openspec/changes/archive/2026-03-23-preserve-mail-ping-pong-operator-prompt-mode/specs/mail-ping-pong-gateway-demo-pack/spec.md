## MODIFIED Requirements

### Requirement: Demo startup SHALL reuse the tracked mailbox-demo fixture family and launch one managed headless Claude participant plus one managed headless Codex participant through demo-owned `houmao-server`
The tracked default startup flow SHALL:

- use `tests/fixtures/agents` as the default agent-definition root unless `AGENT_DEF_DIR` overrides it
- reuse the tracked dummy-project fixture family defined for narrow runtime-agent flows
- provision copied dummy-project workdirs under `<output-root>/projects/initiator/` and `<output-root>/projects/responder/`
- build a Claude brain manifest from the tracked `claude/mail-ping-pong-initiator-default.yaml` recipe
- build a Codex brain manifest from the tracked `codex/mail-ping-pong-responder-default.yaml` recipe
- preserve each tracked participant recipe `launch_policy.operator_prompt_mode` when building those brain manifests
- start one demo-owned `houmao-server` under `<output-root>/server/`
- start that demo-owned `houmao-server` in no-child mode for the native managed-headless startup path
- launch one managed headless Claude Code participant and one managed headless Codex participant through the managed-agent headless launch surface
- use explicit demo-specific initiator and responder role names from the same agent-definition root
- place both participants on one shared mailbox root under `<output-root>/mailbox/`
- attach a gateway for each participant after launch
- enable gateway mail-notifier polling for each participant

The tracked default implementation in this change SHALL support the headless/headless participant pairing only. Unsupported transport selections SHALL fail clearly before live run work begins.

The demo SHALL rely on the runtime-owned mailbox system skill for mailbox operations rather than requiring recipe-authored mailbox transport instructions.

Because the startup flow uses native managed-headless Houmao routes rather than `/cao/*` compatibility session control, demo startup readiness SHALL depend on Houmao-server root health and SHALL NOT require child-CAO health.

When a tracked participant recipe requests unattended operator prompt mode, the built brain manifest SHALL retain that mode and the later live managed-headless launch SHALL expose launch posture evidence consistent with unattended rather than silently falling back to interactive posture.

#### Scenario: Successful start yields two managed headless participants with built manifests and attached gateways
- **WHEN** a developer runs `scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh start` with prerequisites satisfied
- **THEN** the run root contains copied dummy-project workdirs for the initiator and responder
- **AND THEN** the demo builds and records one tracked Claude manifest and one tracked Codex manifest before launch
- **AND THEN** those manifests retain the tracked participant recipe operator prompt mode when one was declared
- **AND THEN** the demo starts one managed headless Claude participant and one managed headless Codex participant through demo-owned `houmao-server`
- **AND THEN** both participants resolve to the shared mailbox root under the selected output root
- **AND THEN** both participants report attached gateway state with notifier control available

#### Scenario: Startup does not require child-CAO health for the headless demo-owned server
- **WHEN** the demo-owned `houmao-server` is started in no-child mode for the tracked headless/headless startup path
- **THEN** the start command treats Houmao-server root health as sufficient startup readiness
- **AND THEN** the demo does not fail solely because no child `cao-server` is running

#### Scenario: Unattended recipe launch posture survives into the live managed-headless launch
- **WHEN** a tracked participant recipe for this demo requests `launch_policy.operator_prompt_mode: unattended`
- **THEN** the corresponding built brain manifest records `launch_policy.operator_prompt_mode: unattended`
- **AND THEN** the later live managed-headless participant records unattended live launch posture rather than silently using interactive posture

### Requirement: Headless demo participants SHALL remain watchable through tmux during live execution
For this demo pack, tmux remains an auxiliary inspection surface rather than a source of lifecycle truth. However, when a managed headless participant is actively executing a turn, an operator who attaches to that participant's persisted tmux session SHALL be able to observe rolling console output from the live CLI execution.

This requirement SHALL be satisfied without making tmux observation authoritative for server-managed headless state.

The pack-local interactive guide and helpers SHALL expose the persisted tmux session names and explain what a watcher should inspect before kickoff and during active execution.

#### Scenario: Operator attaches during a live turn and sees rolling console output
- **WHEN** a maintainer starts the demo, attaches to the initiator or responder tmux session, and a headless turn is active
- **THEN** the attached pane shows rolling console output from the underlying CLI invocation
- **AND THEN** the watcher can distinguish visible progress from a stalled or failed turn without needing to infer state from server internals
- **AND THEN** Houmao-server state remains derived from controller-owned execution evidence rather than tmux watching

### Requirement: Demo inspect and report artifacts SHALL expose machine-readable per-role launch posture evidence
The demo pack SHALL record per-role launch posture evidence inside pack-owned control artifacts so automatic runs can verify the operator prompt mode contract without scraping tmux panes or raw runtime internals.

At minimum, the pack-owned `inspect` and `report` artifacts SHALL summarize for each role:

- tracked recipe operator prompt mode
- built brain manifest operator prompt mode
- live launch request operator prompt mode
- whether launch policy was applied

Those fields SHALL be stable enough for automated verification and SHALL be sanitized when they flow into tracked snapshot comparisons.

#### Scenario: Inspect snapshots expose unattended posture for both roles
- **WHEN** the demo runs `inspect` after `start` for tracked unattended recipes
- **THEN** `control/inspect.json` records per-role launch posture summaries
- **AND THEN** those summaries show unattended mode at the tracked recipe, built brain manifest, and live launch request layers
- **AND THEN** they indicate that launch policy was applied for the unattended launch

### Requirement: The repository SHALL expose one canonical automatic hack-through-testing path for this demo pack
The repository SHALL ship a pack-local autotest harness rooted under `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/`.

That autotest surface SHALL include:

- a standalone harness at `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/run-case.sh`
- an automatic case at `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/case-unattended-full-run.sh`
- an independent interactive guide at `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/case-unattended-full-run.md`
- shared helpers under `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/`

The canonical automatic case SHALL:

- accept a deterministic default output root of `.agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output` unless `--demo-output-dir` overrides it
- fail fast with non-zero exit before launch when required commands or tracked fixture inputs are missing
- stop or clean stale demo-owned state under the selected output root before beginning the new run
- execute the bounded sequence `start -> launch-posture-check -> kickoff -> wait -> inspect -> verify -> stop`
- preserve the selected output root and control artifacts on failure
- exit non-zero on failure
- write one machine-readable case result file under `<output-root>/control/autotest/`
- preserve bounded tmux pane snapshots or equivalent watch diagnostics when a failure occurs after participant launch

The interactive guide SHALL be a standalone step-by-step procedure that tells the operator what the agent should do, what to observe, and what success or failure looks like at each step. It SHALL NOT reduce to "run the automatic case script."

#### Scenario: Missing prerequisites fail before live work begins
- **WHEN** a maintainer runs the canonical automatic case without one required command, tracked fixture file, or tracked credential/config root
- **THEN** the case exits non-zero before `run_demo.sh start`
- **AND THEN** it reports the missing prerequisite clearly in stderr and the case result

#### Scenario: Successful automatic case preserves pass/fail evidence
- **WHEN** a maintainer runs the canonical automatic case with prerequisites satisfied
- **THEN** the harness drives the full unattended ping-pong path through pack-owned scripts
- **AND THEN** the case exits zero only when unattended launch posture, bounded wait, inspect, and verify all succeed
- **AND THEN** the selected output root retains `demo_state.json`, inspect/report artifacts, and the case result payload for later inspection
- **AND THEN** the interactive companion procedure can attach to the same tmux sessions and observe rolling console output while the run is active

### Requirement: Repository SHALL keep deterministic pytest coverage alongside the pack-local live-agent autotest harness
The repository SHALL keep pytest-based automated coverage for the mail ping-pong gateway demo pack that validates the tracked fixture defaults, output-root containment, persisted-state resumability, wait timeout behavior, sanitized report contract, and tracked operator prompt mode preservation.

That deterministic coverage SHALL remain fast and hermetic enough for normal automated test runs, and it MAY use stand-ins or fixtures rather than real local Claude/Codex installs.

The pack-local autotest harness introduced by this change SHALL complement, not replace, those deterministic pytest checks.

#### Scenario: Deterministic coverage detects contract drift
- **WHEN** a maintainer runs the demo pack pytest coverage
- **THEN** the tests fail if the tracked startup defaults drift away from the managed headless Claude/Codex pair and its tracked fixture sources
- **AND THEN** the tests fail if generated Houmao state escapes the selected output root
- **AND THEN** the tests fail if built manifests or launch posture summaries drift away from the tracked participant recipe operator prompt mode
- **AND THEN** the tests fail if persisted state, wait timeout behavior, inspection artifacts, or the sanitized report contract drift from the documented structure

# mail-ping-pong-gateway-demo-pack Specification

## Purpose
TBD - created by archiving change add-headless-mail-ping-pong-gateway-demo. Update Purpose after archive.
## Requirements
### Requirement: Repository SHALL provide a standalone mail ping-pong gateway demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo pack at `scripts/demo/mail-ping-pong-gateway-demo-pack/` that teaches asynchronous mailbox conversation through later gateway wake-up.

At minimum, the pack SHALL contain:

- `README.md`
- `run_demo.sh`
- tracked inputs for the default participant definitions, round limit, kickoff contract, and wait defaults
- helper scripts needed to inspect, sanitize, and verify the demo
- `expected_report/report.json`

The pack SHALL implement its own runner surface and SHALL NOT require another demo pack to orchestrate startup, progression, inspection, or teardown.

#### Scenario: Standalone demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/mail-ping-pong-gateway-demo-pack/`
- **THEN** the required runner, helper, input, and expected-report assets are present
- **AND THEN** the pack can be understood and run from its own directory without a sibling pack acting as its controller

### Requirement: Demo runner SHALL keep all Houmao-generated state under one selected `outputs/` root
The demo runner SHALL accept a `--demo-output-dir <path>` option that selects the generated-state root for the run. When omitted, the runner SHALL default to `scripts/demo/mail-ping-pong-gateway-demo-pack/outputs/`.

If `--demo-output-dir` is relative, the runner SHALL resolve it from the repository root.

For a normal run, all Houmao-generated state owned by the demo SHALL live under the selected output root, including at minimum:

- `control/`
- `server/`
- `runtime/`
- `registry/`
- `mailbox/`
- `jobs/`
- `projects/initiator/`
- `projects/responder/`

The runner SHALL redirect the effective Houmao runtime, registry, mailbox, and local jobs roots so the demo does not write those generated files to the operator defaults outside the selected output root.

#### Scenario: Default run keeps generated state under the pack-local outputs root
- **WHEN** a developer runs `scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh` without `--demo-output-dir`
- **THEN** the runner selects the pack-local `outputs/` directory as the run root
- **AND THEN** demo-owned runtime, registry, mailbox, jobs, copied project, server, and report artifacts are created only under that selected output root

#### Scenario: Explicit output root relocates all generated Houmao state together
- **WHEN** a developer runs the demo pack with `--demo-output-dir tmp/demo/headless-ping-pong`
- **THEN** the runner resolves that path from the repository root
- **AND THEN** the effective Houmao runtime, registry, mailbox, and jobs roots all relocate under the resolved output root for that run

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

### Requirement: Kickoff SHALL establish one persisted thread-key contract for the conversation
Before kickoff, the demo SHALL generate one run-specific thread key and persist it in `control/demo_state.json`.

The kickoff prompt submitted to the initiator SHALL include, at minimum:

- the thread key
- the configured round limit
- the responder identity to target
- the message subject or body convention that carries the thread key and round number
- the rule that the responder replies in the same thread
- the rule that the initiator stops after reading reply `N`, where `N` is the configured round limit

The tracked default conversation SHALL carry the thread key and current round in every outgoing message so the run can be reconstructed from mailbox artifacts and normalized demo events.

#### Scenario: Kickoff persists and communicates one thread key
- **WHEN** a developer runs `kickoff` or the automatic workflow after a successful `start`
- **THEN** the demo persists one run-specific thread key in `control/demo_state.json`
- **AND THEN** the submitted kickoff request communicates that thread key and the round-limit contract to the initiator
- **AND THEN** the first outgoing message carries the same thread key for later responder and verifier use

### Requirement: Tracked ping-pong turns use gateway-first shared mailbox actions when gateways are attached
When the tracked mail ping-pong demo runs with attached loopback gateways for its participants, the demo SHALL keep routine mailbox work on the shared gateway mailbox facade rather than teaching the participants to reconstruct direct filesystem helper flows during ordinary turns.

The tracked kickoff contract SHALL communicate the business inputs for the first send action, including the responder target, thread key, round limit, subject convention, and reply policy, without requiring the initiator prompt to restate direct filesystem delivery mechanics as the normal path.

Later notifier-driven turns SHALL identify one actionable unread ping-pong message through shared mailbox references, including thread and queued-work context sufficient for a bounded reply turn, and SHALL expect the participant to complete the bounded mailbox action for that target, including the follow-up read-state update after successful processing.

The tracked initiator and responder role overlays SHALL remain focused on ping-pong policy such as round semantics, who replies next, and when to stop rather than on transport-local mailbox implementation details.

#### Scenario: Kickoff remains policy-thin for an attached gateway run
- **WHEN** a developer starts the demo and submits kickoff for a run whose initiator has a live loopback gateway mailbox facade
- **THEN** the kickoff prompt tells the initiator what first ping-pong message to send and which thread policy to follow
- **AND THEN** the prompt does not need to restate direct filesystem helper recipes as the normal attached-session path

#### Scenario: Responder wake-up completes one bounded shared-mailbox task
- **WHEN** the responder later wakes through gateway notifier after receiving the first ping-pong message
- **THEN** the responder turn is framed around one actionable unread target identified through shared mailbox references
- **AND THEN** the responder is expected to reply in the same thread, mark the processed message read after success, and end the turn without transport-local mailbox reconstruction

### Requirement: Automatic workflow SHALL complete a fixed-round asynchronous mailbox conversation through later gateway wake-up
The default automatic workflow SHALL complete a two-agent conversation with default round limit `5`.

The workflow SHALL submit exactly one direct kickoff request to the initiator. After that kickoff, later turns SHALL progress through actionable mailbox state plus gateway wake-up rather than through direct manual prompt submission after every message.

During the conversation:

- the initiator SHALL send the first request mail and end its turn immediately after send
- the responder SHALL later wake, read the request, reply in the same thread, and end its turn immediately after send
- the initiator SHALL later wake on the reply, decide whether the configured round limit has been reached, and either send the next request in the same thread or stop without sending another message

For configured round limit `N`, success SHALL require `2 * N` sent messages and `2 * N + 1` completed turns in one conversation thread. For the tracked default `N = 5`, success therefore requires `10` sent messages and `11` completed turns.

#### Scenario: Default automatic run completes five exchanges on one thread
- **WHEN** a developer runs the demo pack automatic workflow with prerequisites satisfied
- **THEN** the pack submits one kickoff request to the initiator
- **AND THEN** the initiator and responder complete five mailbox round trips on one thread through later gateway wake-up
- **AND THEN** the run records ten sent messages and eleven completed turns before the demo is considered successful

### Requirement: Stepwise workflow SHALL preserve live state for inspection, pause, continue, bounded wait, verification, and stop
The runner SHALL provide stepwise commands that act on the same persisted live run state after `start`.

At minimum, the runner SHALL support:

- `kickoff`
- `wait`
- `inspect`
- `pause`
- `continue`
- `verify`
- `stop`

`pause` SHALL stop later conversation progression by disabling notifier-driven wake-up without destroying the live participants. `continue` SHALL restore notifier-driven progression for the same live run. `inspect`, `verify`, and `stop` SHALL resolve the same persisted run identity from `control/demo_state.json`.

`wait` SHALL use bounded polling with tracked defaults for poll cadence and timeout, SHALL report visible progress while it is polling, and SHALL fail explicitly with an incomplete reason when the timeout expires instead of hanging indefinitely.

#### Scenario: Operator pauses and resumes one live conversation
- **WHEN** an operator runs `start`, then `kickoff`, then `pause` against a live run
- **THEN** both participants remain available for later inspection
- **AND THEN** later turns stop progressing until the operator runs `continue`
- **AND THEN** the same persisted run can then be inspected, verified, waited, and stopped without recreating it

#### Scenario: Wait times out explicitly and preserves the run for diagnosis
- **WHEN** the operator runs `wait` and the conversation does not satisfy the success contract before the configured timeout
- **THEN** `wait` exits with an explicit incomplete or timeout result
- **AND THEN** the run artifacts remain available for `inspect`, `verify`, and `stop`

### Requirement: Persisted demo-owned state and event artifacts SHALL expose the minimum fields needed for resumability and verification
`control/demo_state.json` SHALL persist enough run-owned information to let later commands target the same live run. At minimum, it SHALL include:

- output-root identity
- agent-definition root
- server API base URL
- mailbox root
- thread key
- round limit
- wait defaults
- server ownership metadata
- per-participant tracked agent identity, tool, role name, working directory, and brain manifest reference

The normalized conversation event stream SHALL contain, at minimum, these fields on every record:

- `event_type`
- `observed_at_utc`
- `agent_role`
- `tracked_agent_id`
- `thread_key`
- `round_index`

The event stream MAY include additional request, turn, message, and gateway linkage fields when available.

#### Scenario: Persisted state supports later command targeting
- **WHEN** a developer runs `start` and later invokes `inspect`, `pause`, `continue`, `wait`, `verify`, or `stop`
- **THEN** those commands resolve the same live run from `control/demo_state.json`
- **AND THEN** the persisted state contains the minimum fields needed to target the server and both participants without guessing

#### Scenario: Normalized event records carry stable replay keys
- **WHEN** the demo records one normalized conversation event
- **THEN** that record contains at least `event_type`, `observed_at_utc`, `agent_role`, `tracked_agent_id`, `thread_key`, and `round_index`
- **AND THEN** later inspection and verification can correlate that event with the run without scraping raw terminal text

### Requirement: Verification SHALL explain conversation progress through stable message, turn, mailbox, and gateway evidence
The demo pack SHALL build stable demo-owned artifacts that explain whether the conversation completed successfully or stopped incomplete.

At minimum, verification SHALL produce:

- `control/inspect.json`
- `control/report.json`
- `control/report.sanitized.json`
- a normalized conversation event stream owned by the pack

The verification flow SHALL use managed-agent state, durable headless turn linkage, shared mailbox artifacts, and gateway status or audit evidence to report:

- the conversation thread identity
- message and turn counts
- per-role progress through the configured rounds
- later-turn gateway wake-up evidence
- final unread or handled mailbox posture
- the explicit success or incompleteness reason

The sanitized golden report SHALL mask non-deterministic values such as paths, timestamps, runtime ids, request ids, turn ids, and message ids. It SHALL NOT require an exact per-poll gateway notifier sequence in order to compare successfully.

#### Scenario: Verification explains a successful five-round run without exact poll matching
- **WHEN** a maintainer runs `verify` after a valid five-round demo run
- **THEN** the resulting sanitized report includes stable evidence for one thread, ten messages, eleven completed turns, and later-turn gateway wake-up behavior
- **AND THEN** the comparison does not fail merely because two valid runs observed different counts or ordering of empty notifier polls

### Requirement: README SHALL teach the headless-first asynchronous coordination pattern, output-root ownership model, and v1 coverage posture
The demo-pack README SHALL document:

- the concrete goal of the demo
- prerequisites
- the tracked fixture sources for the dummy project, recipes, and role packages
- the headless/headless tracked scope for this change
- the pack-local `outputs/` ownership model
- the automatic workflow
- the stepwise workflow and command meanings
- the pack-local autotest surface, including the canonical automatic case and the interactive companion guide
- the fixed-round asynchronous conversation contract
- the kickoff and thread-key contract
- the meaning of later gateway wake-up versus direct prompt submission
- bounded wait, timeout, and incomplete-run behavior
- verification and snapshot refresh instructions
- the key output artifacts used for inspection
- tmux watchability as an auxiliary diagnostic surface
- the deterministic pytest coverage posture alongside the pack-local live-agent `autotest/` harness

The README SHALL explain that the pack teaches one canonical asynchronous mailbox conversation pattern and that all generated Houmao state for the demo is intentionally contained under the selected output root.

#### Scenario: Reader understands how the conversation progresses, where the state lives, and what coverage surfaces exist
- **WHEN** a developer follows the README for the new demo pack
- **THEN** they can identify the single kickoff step, the later gateway-driven turns, and the fixed-round stop condition
- **AND THEN** they can tell which generated files should appear under the selected output root and why the pack does not write live demo state to the default Houmao roots
- **AND THEN** they can tell how the canonical automatic case, the interactive companion guide, and the deterministic pytest coverage complement one another

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

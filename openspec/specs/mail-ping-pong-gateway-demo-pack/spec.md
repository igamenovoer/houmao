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
- build a Claude brain manifest from the tracked `claude/mailbox-demo-default.yaml` recipe
- build a Codex brain manifest from the tracked `codex/mailbox-demo-default.yaml` recipe
- start one demo-owned `houmao-server` under `<output-root>/server/`
- launch one managed headless Claude Code participant and one managed headless Codex participant through the managed-agent headless launch surface
- use explicit demo-specific initiator and responder role names from the same agent-definition root
- place both participants on one shared mailbox root under `<output-root>/mailbox/`
- attach a gateway for each participant after launch
- enable gateway mail-notifier polling for each participant

The tracked default implementation in this change SHALL support the headless/headless participant pairing only. Unsupported transport selections SHALL fail clearly before live run work begins.

The demo SHALL rely on the runtime-owned mailbox system skill for mailbox operations rather than requiring recipe-authored mailbox transport instructions.

#### Scenario: Successful start yields two managed headless participants with built manifests and attached gateways
- **WHEN** a developer runs `scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh start` with prerequisites satisfied
- **THEN** the run root contains copied dummy-project workdirs for the initiator and responder
- **AND THEN** the demo builds and records one tracked Claude manifest and one tracked Codex manifest before launch
- **AND THEN** the demo starts one managed headless Claude participant and one managed headless Codex participant through demo-owned `houmao-server`
- **AND THEN** both participants resolve to the shared mailbox root under the selected output root
- **AND THEN** both participants report attached gateway state with notifier control available

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
- the fixed-round asynchronous conversation contract
- the kickoff and thread-key contract
- the meaning of later gateway wake-up versus direct prompt submission
- bounded wait, timeout, and incomplete-run behavior
- verification and snapshot refresh instructions
- the key output artifacts used for inspection
- the v1 pytest-based coverage posture and the explicit deferral of a pack-local live-agent `autotest/` harness

The README SHALL explain that the pack teaches one canonical asynchronous mailbox conversation pattern and that all generated Houmao state for the demo is intentionally contained under the selected output root.

#### Scenario: Reader understands how the conversation progresses, where the state lives, and what v1 does not include
- **WHEN** a developer follows the README for the new demo pack
- **THEN** they can identify the single kickoff step, the later gateway-driven turns, and the fixed-round stop condition
- **AND THEN** they can tell which generated files should appear under the selected output root and why the pack does not write live demo state to the default Houmao roots
- **AND THEN** they can tell that this change ships pytest-based regression coverage and does not yet ship a pack-local live-agent `autotest/` harness

### Requirement: Repository SHALL keep pytest-based automated regression coverage for the demo-pack contract in v1
The repository SHALL keep pytest-based automated coverage for the mail ping-pong gateway demo pack that validates the tracked fixture defaults, output-root containment, persisted-state resumability, wait timeout behavior, and sanitized report contract.

This change SHALL NOT require a pack-local live-agent `autotest/` harness in order to treat the demo pack as complete.

That automated coverage MAY use deterministic stand-ins or fixtures rather than requiring a real local Claude Code and Codex installation in the default test suite.

#### Scenario: Automated coverage detects contract drift
- **WHEN** a maintainer runs the demo pack automated coverage
- **THEN** the tests fail if the tracked startup defaults drift away from the managed headless Claude/Codex pair and its tracked fixture sources
- **AND THEN** the tests fail if generated Houmao state escapes the selected output root
- **AND THEN** the tests fail if persisted state, wait timeout behavior, inspection artifacts, or the sanitized report contract drift from the documented structure


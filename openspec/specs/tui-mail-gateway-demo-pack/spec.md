# tui-mail-gateway-demo-pack Specification

## Purpose
TBD - created by archiving change add-tui-mail-gateway-demo-pack. Update Purpose after archive.
## Requirements
### Requirement: Repository SHALL provide a standalone TUI mail gateway demo pack under `scripts/demo/`
The repository SHALL include a self-contained demo pack at `scripts/demo/tui-mail-gateway-demo-pack/` that teaches how one CAO-backed TUI session is awakened by filesystem mailbox unread mail through a live gateway.

At minimum, the pack SHALL contain:

- `README.md`
- `run_demo.sh`
- tracked inputs for tool selection, cadence, delivery contract, and verification defaults
- helper scripts needed to inspect, sanitize, and verify the demo
- `expected_report/report.json`

The pack SHALL implement its own runner surface and SHALL NOT require another demo pack to orchestrate startup, progression, inspection, or teardown.

#### Scenario: Demo-pack layout exists
- **WHEN** a maintainer inspects `scripts/demo/tui-mail-gateway-demo-pack/`
- **THEN** the required runner, helper, input, and expected-report assets are present
- **AND THEN** the pack can be understood and run from its own directory without a sibling pack acting as its controller

### Requirement: Startup SHALL launch one mailbox-enabled TUI session for the selected tool
The demo runner SHALL require explicit tool selection for startup and automatic runs, supporting `claude` and `codex`.

For a selected tool, the tracked startup flow SHALL:

- use `tests/fixtures/agents` as the default agent-definition root unless `AGENT_DEF_DIR` overrides it
- provision a copied dummy-project workdir from `tests/fixtures/dummy-projects/mailbox-demo-python`
- build the selected brain from the tracked lightweight `mailbox-demo` fixture family
- start exactly one `cao_rest` mailbox-enabled session for that selected tool
- attach a live loopback gateway for that session after startup
- enable gateway mail-notifier polling for that session
- persist the selected tool and resulting runtime identity so later commands target the same live session

The startup flow SHALL NOT launch both tools concurrently in one run.

#### Scenario: Claude startup provisions one mailbox-enabled TUI session
- **WHEN** a developer runs the demo pack startup with `--tool claude`
- **THEN** the pack builds the tracked Claude mailbox-demo runtime context
- **AND THEN** it starts exactly one mailbox-enabled Claude `cao_rest` TUI session
- **AND THEN** it attaches a live loopback gateway and enables notifier polling for that same session

#### Scenario: Codex startup provisions one mailbox-enabled TUI session
- **WHEN** a developer runs the demo pack startup with `--tool codex`
- **THEN** the pack builds the tracked Codex mailbox-demo runtime context
- **AND THEN** it starts exactly one mailbox-enabled Codex `cao_rest` TUI session
- **AND THEN** it attaches a live loopback gateway and enables notifier polling for that same session

### Requirement: Demo-owned generated state SHALL stay under one selected output root
The demo runner SHALL accept a `--demo-output-dir <path>` option that selects the generated-state root for the run. When omitted, the runner SHALL default to a tool-specific pack-local output root under `scripts/demo/tui-mail-gateway-demo-pack/outputs/<tool>/`.

If `--demo-output-dir` is relative, the runner SHALL resolve it from the repository root.

All Houmao-generated state owned by the demo SHALL live under the selected output root, including at minimum:

- `control/`
- `cao/`
- `runtime/`
- `mailbox/`
- `deliveries/`
- `project/`
- `evidence/`

The runner SHALL redirect runtime, registry, mailbox, and local jobs roots so the demo does not write generated files to operator defaults outside the selected output root.

#### Scenario: Default output root stays tool-scoped and pack-local
- **WHEN** a developer runs the demo pack without `--demo-output-dir`
- **THEN** the runner selects the pack-local output root for the chosen tool
- **AND THEN** the demo-owned runtime, mailbox, delivery, copied-project, and report artifacts are created only under that selected output root

#### Scenario: Explicit output root relocates all generated Houmao state
- **WHEN** a developer runs the demo pack with `--demo-output-dir tmp/demo/tui-mail-gateway`
- **THEN** the runner resolves that path from the repository root
- **AND THEN** the effective runtime, registry, mailbox, and jobs roots all relocate under the resolved output root for that run

### Requirement: Harness driving SHALL inject one new mail every five seconds only when the mailbox has no unread mail
The demo pack SHALL provide a harness-driven drive loop with default cadence `5` seconds and default turn limit `3`.

At each drive tick, the harness SHALL:

- inspect mailbox unread state for the demo session
- inspect current gateway execution eligibility for the same session
- inject one new mail only when unread count is zero, the gateway can admit work safely, and fewer than three processed turns have completed

Each injected mail SHALL be delivered through the managed mailbox delivery boundary rather than through direct SQLite mutation.

Each injected mail SHALL include, at minimum:

- a run identifier
- a turn index
- a bounded instruction telling the agent to read the mail, acknowledge it in chat, and then mark the processed message read

The harness SHALL stop injecting new mail after three processed turns have completed.

#### Scenario: Harness injects the first mail after startup settles idle
- **WHEN** the operator starts the demo and runs the drive workflow for a new session
- **THEN** the harness waits until the session is eligible for new work
- **AND THEN** it injects exactly one first message on a five-second drive tick

#### Scenario: Harness does not inject another mail while unread mail is still present
- **WHEN** the previously injected message is still unread in the mailbox
- **THEN** later five-second drive ticks do not inject another message
- **AND THEN** the harness waits for the unread state to clear before sending the next mail

#### Scenario: Harness completes exactly three processed turns
- **WHEN** the live session processes mail successfully and marks each processed message read
- **THEN** the harness injects exactly three messages in total
- **AND THEN** it stops sending additional mail after the third processed turn is complete

### Requirement: Demo progression SHALL rely on gateway-first shared mailbox actions for routine turn work
When a live loopback gateway mailbox facade is attached for the demo session, the demo SHALL teach and expect routine mailbox work to stay on the shared gateway mailbox routes rather than on direct transport-local helper reconstruction.

The later wake-up turn contract SHALL be bounded around one nominated unread shared mailbox target at a time.

Success for each processed turn SHALL require:

- the gateway notifier to nominate actionable unread mail
- the agent to inspect that unread mail through the shared mailbox contract
- the agent to mark the processed message read through the shared mailbox state update after successful handling

#### Scenario: Later wake-up turn is framed around one nominated unread target
- **WHEN** the gateway notifier wakes the demo session because unread mail exists
- **THEN** the turn is framed around one actionable unread shared mailbox target
- **AND THEN** the agent is expected to process that target without reconstructing direct filesystem helper flow as the ordinary attached-session path

#### Scenario: Processed message becomes read only after successful handling
- **WHEN** the agent finishes the bounded mailbox action for one nominated unread message
- **THEN** the same processed message is marked read through the shared mailbox state update
- **AND THEN** that read transition becomes the signal that allows a later harness tick to inject the next message

### Requirement: Inspect and verification artifacts SHALL explain three-turn progression through stable mailbox and gateway evidence plus human-review TUI evidence
The demo pack SHALL record machine-readable inspect and report artifacts that explain the run without depending on exact assistant wording.

At minimum, the artifacts SHALL summarize:

- selected tool and live session identity
- notifier enablement and durable notifier-audit evidence
- mailbox unread-state transitions across the three injected messages
- per-turn delivery metadata for the injected messages
- final unread count
- bounded human-review TUI evidence for each processed turn, such as tmux pane snapshots or best-effort output tails

The required sanitized verification contract SHALL NOT compare exact assistant chat wording.

#### Scenario: Verification succeeds without exact transcript assertions
- **WHEN** two valid runs process the same three-turn mail loop but produce different assistant phrasing
- **THEN** the sanitized verification contract can still compare successfully
- **AND THEN** it relies on stable gateway, mailbox, and per-turn evidence instead of exact transcript text

#### Scenario: Inspect artifacts preserve human-review evidence for each processed turn
- **WHEN** a maintainer inspects a completed or in-progress demo run
- **THEN** the demo-owned artifacts include bounded TUI evidence linked to each processed turn
- **AND THEN** the maintainer can review that evidence without the golden report depending on exact wording

### Requirement: Runner SHALL support both automatic and stepwise workflows
The demo pack runner SHALL support an automatic workflow and a stepwise workflow that act on the same persisted run state.

At minimum, the runner SHALL support:

- `auto`
- `start`
- `drive`
- `inspect`
- `verify`
- `stop`

The automatic workflow SHALL execute `start -> drive -> inspect -> verify -> stop`.

The stepwise workflow SHALL preserve enough state for `drive`, `inspect`, `verify`, and `stop` to target the same live run after `start`.

#### Scenario: Automatic workflow completes the full three-turn demo path
- **WHEN** a developer runs the demo pack automatic workflow with prerequisites satisfied
- **THEN** the pack starts one live mailbox-enabled TUI session for the selected tool
- **AND THEN** it drives the three-turn harness workflow, inspects artifacts, verifies the report, and stops the session

#### Scenario: Stepwise workflow reuses persisted run state
- **WHEN** a developer runs `start` and later runs `drive`, `inspect`, `verify`, or `stop`
- **THEN** those later commands target the same persisted live run
- **AND THEN** they do not require the operator to relaunch the session first

### Requirement: Repository SHALL keep automated coverage and operator documentation for the demo-pack contract
The repository SHALL keep automated coverage for the TUI mail gateway demo pack that validates fixture selection, harness gating, artifact structure, and sanitized verification behavior.

The pack README SHALL document:

- the single-agent TUI wake-up goal
- prerequisites
- required tool selection
- the five-second unread-gated harness contract
- the three-turn success condition
- automatic and stepwise commands
- the output-root ownership model
- verification and snapshot refresh steps
- the human-review posture for TUI evidence

#### Scenario: Automated coverage detects harness or artifact drift
- **WHEN** a maintainer runs the demo pack coverage
- **THEN** the tests fail if the tool-selection contract, five-second unread-gated drive loop, or sanitized artifact structure drifts from the tracked contract

#### Scenario: README teaches the operator-facing workflow explicitly
- **WHEN** a developer reads the pack README
- **THEN** the documentation explains how the harness decides when to inject the next message
- **AND THEN** it explains how to run the demo for Claude and Codex separately
- **AND THEN** it explains why TUI evidence is kept for review but not used as an exact golden-text assertion


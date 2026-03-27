# gateway-mail-wakeup-demo-pack Specification

## Purpose
Define the gateway mail wake-up tutorial pack, including serverless startup, mailbox and gateway lifecycle, reporting, and regression coverage.

## Requirements
### Requirement: Repository SHALL provide a gateway mail wake-up tutorial pack under `scripts/demo/`
The repository SHALL include a self-contained gateway mail wake-up tutorial-pack directory under `scripts/demo/` that follows the local runnable tutorial-pack pattern used by existing demo packs.

The tutorial pack SHALL include, at minimum:

- `README.md`
- `run_demo.sh`
- tracked inputs that define the default agent, mailbox addresses, notifier interval, injector interval, and wake-up task
- helper scripts needed to sanitize, verify, and inspect the demo
- `expected_report/report.json`

#### Scenario: Tutorial-pack layout exists
- **WHEN** a developer inspects the gateway wake-up tutorial-pack directory under `scripts/demo/`
- **THEN** the required files and subdirectories are present

### Requirement: Tutorial-pack runner SHALL support both automatic and manual gateway wake-up workflows
The tutorial-pack runner SHALL support both:

- a one-shot automatic workflow that executes the default wake-up scenario end to end, and
- a stateful manual workflow that lets the operator start the live session, inject mail, inspect state, verify outputs, and stop explicitly.

The manual workflow SHALL preserve enough demo-owned state to target the same live agent session and gateway instance across follow-up commands.

#### Scenario: Automatic and manual surfaces both exist
- **WHEN** a developer uses the tutorial pack
- **THEN** they can run one end-to-end default workflow without manual orchestration
- **AND THEN** they can also reuse the same pack to inspect and drive the live wake-up flow step by step

### Requirement: Startup SHALL support separate serverless Claude Code and Codex runs
The gateway wake-up tutorial pack SHALL support tool-specific startup and automatic runs for `claude` and `codex`.

For a selected tool, the tracked startup flow SHALL:

- resolve tracked agent-definition defaults from `tests/fixtures/agents` unless the pack exposes an explicit override,
- provision a copied dummy-project workdir from the tracked mailbox-ready dummy-project fixture,
- start exactly one serverless local interactive managed agent through `houmao-mgr`,
- register a filesystem mailbox binding for that live session through `houmao-mgr`,
- attach a live loopback gateway for that same session after launch, and
- enable gateway mail-notifier polling for that same session.

The startup flow SHALL NOT launch both tools concurrently in one live run.

#### Scenario: Claude startup provisions one serverless mailbox-enabled session
- **WHEN** a developer runs the rewritten demo startup with `--tool claude`
- **THEN** the pack starts exactly one serverless Claude Code managed-agent session through `houmao-mgr`
- **AND THEN** it registers a filesystem mailbox binding for that session
- **AND THEN** it attaches a live loopback gateway and enables notifier polling for that same session

#### Scenario: Codex startup provisions one serverless mailbox-enabled session
- **WHEN** a developer runs the rewritten demo startup with `--tool codex`
- **THEN** the pack starts exactly one serverless Codex managed-agent session through `houmao-mgr`
- **AND THEN** it registers a filesystem mailbox binding for that session
- **AND THEN** it attaches a live loopback gateway and enables notifier polling for that same session

### Requirement: Demo-owned generated state SHALL stay under a pack-local output root
The rewritten demo pack SHALL keep all generated state under a selected output root inside `scripts/demo/gateway-mail-wakeup-demo-pack/` by default.

When the operator does not supply an explicit output-root override, the runner SHALL default to a tool-specific pack-local output root under `scripts/demo/gateway-mail-wakeup-demo-pack/outputs/<tool>/`.

All demo-owned generated state SHALL live under the selected output root, including at minimum:

- `control/`
- `runtime/`
- `registry/`
- `jobs/`
- `mailbox/`
- `deliveries/`
- `project/`
- `outputs/`

The runner SHALL redirect runtime, registry, mailbox, and local jobs roots so the demo does not write generated files to operator defaults outside the selected output root.

The repository SHALL keep a pack-local ignore rule that prevents those generated output roots from being tracked by git.

#### Scenario: Default output root stays pack-local and tool-scoped
- **WHEN** a developer runs the rewritten demo pack without an explicit output-root override
- **THEN** the runner selects the pack-local output root for the chosen tool
- **AND THEN** the demo-owned runtime, registry, mailbox, delivery, copied-project, and report artifacts are created only under that selected output root

#### Scenario: Mailbox root stays inside the selected demo output root
- **WHEN** the rewritten demo provisions filesystem mailbox state for a run
- **THEN** the effective mailbox root lives under the selected pack-local output root
- **AND THEN** the demo does not place mailbox state under a repo-global temp root or operator-default mailbox root outside the pack

### Requirement: Tutorial-pack defaults SHALL use a copied dummy-project and lightweight mailbox-demo agent fixture
The tracked default gateway wake-up tutorial SHALL provision a copied dummy-project workdir under the selected output root by copying a tracked source-only dummy-project fixture into that path and initializing the copied tree as a fresh standalone git-backed workdir before live serverless startup runs.

The tracked default started agent SHALL use lightweight mailbox-demo fixture defaults from `tests/fixtures/agents` rather than the heavyweight `gpu-kernel-coder` family.

The default wake-up tutorial SHALL NOT require the main repository checkout itself to be the launched working directory.

#### Scenario: Default start provisions a copied dummy-project workdir
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the default automatic workflow with the tracked defaults
- **THEN** the demo-owned `project/` path is copied from a tracked dummy-project fixture inside the selected output root
- **AND THEN** the helper initializes that copied tree as a standalone git-backed workdir for the run
- **AND THEN** the resulting `project/` path is not a git worktree of the main repository
- **AND THEN** the started managed session uses tracked lightweight mailbox-demo fixture defaults for the selected tool

#### Scenario: Stale non-managed project directories fail clearly
- **WHEN** the selected output root already contains `project/` and that path is not a pack-managed copied dummy-project repo
- **THEN** the tutorial pack fails explicitly instead of silently reusing that directory
- **AND THEN** the failure tells the maintainer to use a fresh output root or remove the stale directory

### Requirement: Automatic workflow SHALL verify idle-session wake-up through a demo-owned output artifact
The tracked automatic workflow SHALL:

- initialize or validate a demo-owned filesystem mailbox root under the selected output root,
- start one mailbox-enabled serverless local interactive session for the selected tool through `houmao-mgr`,
- use tracked lightweight mailbox-demo fixture defaults for that session,
- register the session against the demo-owned filesystem mailbox root after launch,
- attach the gateway for that session as a post-launch step through `houmao-mgr`,
- enable gateway mail-notifier polling with a one-second interval,
- wait until the live session is observed ready for work through serverless gateway and managed-agent state,
- deliver an instruction that asks the agent to write the current time into a file under the demo-owned output directory through the managed filesystem mailbox delivery boundary, and
- wait for that output file or fail clearly when the wake-up flow does not complete.

The automatic workflow SHALL capture the gateway, mailbox, local runtime, and output-file artifacts needed to explain the observed result.

#### Scenario: Idle serverless session is woken by one injected mail
- **WHEN** a developer runs the automatic workflow for one selected tool with prerequisites satisfied
- **THEN** the pack starts one mailbox-enabled serverless local interactive session from the tracked copied dummy-project workdir using the lightweight mailbox-demo defaults
- **AND THEN** the pack registers mailbox support, attaches the gateway, and enables notifier polling after launch through `houmao-mgr`
- **AND THEN** the pack delivers one managed filesystem email after the session is observed ready for work
- **AND THEN** the gateway wake-up flow becomes observable through captured gateway, mailbox, and local runtime artifacts
- **AND THEN** the agent produces the configured output file under the demo-owned output directory

### Requirement: Manual workflow SHALL support single-message and burst-message injection through operator-friendly inputs
The tutorial pack SHALL let an operator inject mail manually by providing either inline body content or a body file path.

The pack SHALL also support delivering multiple messages in quick succession to the same mailbox-enabled session for burst testing.

Those manual deliveries SHALL execute through the mailbox managed delivery boundary rather than through direct SQLite mutation.

#### Scenario: Operator injects one mail from inline text or a file
- **WHEN** a developer uses the manual workflow to inject a message with inline content or a body file
- **THEN** the pack delivers that message through the managed mailbox delivery path
- **AND THEN** the resulting wake-up behavior can be inspected through the same demo-owned gateway and mailbox artifacts

#### Scenario: Burst delivery verifies unread-set handling without requiring one prompt per message
- **WHEN** a developer injects multiple messages in quick succession through the manual workflow
- **THEN** the pack verifies that all of those messages remain represented in unread mailbox state until processed explicitly
- **AND THEN** it does not require the gateway to emit one wake-up prompt per delivered message in order to treat the burst case as successful

### Requirement: Tutorial-pack verification SHALL report gateway-owned wake-up evidence and unread-set outcomes
The tutorial-pack verification contract SHALL sanitize non-deterministic values and SHALL report, at minimum:

- managed-agent identity and selected-tool evidence for the serverless run,
- notifier enablement and runtime status,
- gateway decision-audit evidence from durable notifier audit history under the gateway root,
- queue or event evidence for any notifier prompt that was enqueued,
- mailbox-local state evidence for the delivered message, including whether the processed message became read,
- output-file evidence for the automatic wake-up case, and
- pack-local output-root ownership evidence for the generated artifacts.

The pack MAY include tmux or dialog evidence as supplemental debugging material, but the required golden report SHALL NOT depend on exact model phrasing or exact per-poll notifier sequencing.

The sanitized golden report SHALL reduce raw notifier audit rows to stable outcome-summary assertions and SHALL NOT require an exact per-poll outcome sequence in `expected_report/report.json`.

#### Scenario: Verification report explains why wake-up succeeded or was skipped
- **WHEN** a maintainer runs the tutorial-pack verification flow
- **THEN** the resulting sanitized report includes enough gateway-owned, mailbox-owned, and local-runtime evidence to explain whether unread mail caused a wake-up prompt, a busy skip, or another explicit notifier decision
- **AND THEN** the report can be compared reproducibly against `expected_report/report.json`

#### Scenario: Verification proves mailbox contract completion rather than file-side effects alone
- **WHEN** the automatic wake-up flow succeeds
- **THEN** the verification contract shows that the delivered mailbox target was processed successfully enough to reach the expected read-state outcome
- **AND THEN** the same report also shows the expected output-file side effect under the demo-owned output directory

#### Scenario: Golden report stays stable without exact poll sequencing
- **WHEN** two valid demo runs observe different counts or ordering of empty notifier polls before mail delivery
- **THEN** the sanitized golden report can still compare successfully as long as the required outcome-summary assertions and artifact evidence match
- **AND THEN** any raw per-poll audit rows may remain available separately for debugging without becoming part of the exact golden comparison

### Requirement: Repository SHALL keep automated regression coverage for the gateway wake-up demo-pack fixture contract
The repository SHALL keep automated coverage for the gateway wake-up demo pack that validates the tracked fixture defaults, serverless lifecycle behavior, copied-project mailbox skill staging, pack-local output ownership, and sanitized report contract.

That automated coverage MAY use deterministic command doubles or artifact fixtures rather than requiring a real local Claude or Codex session in the default test suite.

The repository SHALL also keep a real-agent path suitable for maintainers to validate both Claude Code and Codex serverless lanes against the tracked demo contract.

#### Scenario: Automated coverage detects fixture-default drift
- **WHEN** a maintainer runs the demo pack's automated coverage
- **THEN** the tests fail if the tracked parameters or orchestration behavior drift away from the serverless `houmao-mgr` flow
- **AND THEN** the tests fail if the copied dummy-project no longer stages the expected mailbox skill documents
- **AND THEN** the tests fail if the inspection or sanitized-report contract drifts from the expected artifact structure

#### Scenario: Real-agent coverage exercises both supported tool lanes
- **WHEN** a maintainer runs the demo pack's real-agent validation path
- **THEN** the repository provides a supported way to exercise both Claude Code and Codex against the rewritten serverless wake-up contract
- **AND THEN** the resulting artifacts preserve separate tool-scoped evidence for diagnosis

### Requirement: Tutorial README SHALL teach the gateway wake-up contract and workflows explicitly
The tutorial README SHALL document:

- a concrete gateway wake-up question or goal,
- prerequisites checklist,
- the serverless `houmao-mgr` control flow used by the pack,
- the unread-set notification contract,
- the automatic workflow,
- the manual single-mail and burst-mail workflows,
- the default dummy-project and lightweight mailbox-demo fixture shape,
- separate Claude Code and Codex usage,
- the pack-local output-root ownership model, including the mailbox root,
- explicit run and verify steps mirroring the meaningful runner actions,
- snapshot refresh instructions, and
- an appendix listing key parameters plus input and output files.

The README SHALL explain that gateway notifier behavior is unread-set based and that one reminder prompt may summarize multiple unread messages.

The README SHALL also explain that the gateway wake-up tutorial is a narrow mailbox and runtime-contract demo, so its default fixture shape intentionally uses a copied dummy project rather than a repository worktree.

#### Scenario: Reader understands the serverless fixture shape and burst behavior
- **WHEN** a developer follows the README through setup and manual burst-delivery sections
- **THEN** the documentation identifies the tracked dummy-project and lightweight mailbox-demo defaults used by the tutorial
- **AND THEN** it explains that the walkthrough uses serverless `houmao-mgr` startup, mailbox registration, and post-launch gateway attachment rather than demo-owned `houmao-server`
- **AND THEN** it explains that the gateway is notifying “unread mail exists” rather than “one new mail arrived”
- **AND THEN** the reader can distinguish valid unread-set batching behavior from a missed-message failure

### Requirement: Tutorial-pack lifecycle SHALL use serverless `houmao-mgr` mailbox and gateway flow
The tracked default gateway wake-up tutorial SHALL launch its live mailbox-enabled session through the serverless `houmao-mgr` managed-agent flow instead of through demo-owned `houmao-server`.

The lifecycle SHALL:

- initialize or validate a filesystem mailbox root under the selected output root,
- launch the live session through `houmao-mgr`,
- register filesystem mailbox support after launch through `houmao-mgr`,
- treat gateway attach as a post-launch step,
- use serverless managed-agent authority for later notifier control, inspection targeting, and stop behavior, and
- fail clearly when the selected managed-agent identity cannot be resolved or reused for follow-up commands.

#### Scenario: Default start uses serverless managed-agent flow
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the automatic workflow with the tracked defaults
- **THEN** the pack initializes or reuses a demo-owned filesystem mailbox root under the selected output root
- **AND THEN** the started live session uses the serverless `houmao-mgr` managed-agent launch flow
- **AND THEN** later mailbox registration, gateway attach, notifier, inspect, and stop steps target that same session through serverless managed-agent authority

### Requirement: Provisioned copied dummy-project workdir SHALL expose project-local mailbox skill documents
The tracked default gateway wake-up tutorial SHALL stage the runtime-owned mailbox skill documents into the provisioned copied dummy-project workdir before the live session starts.

The provisioned workdir SHALL expose the visible `skills/mailbox/...` mailbox skill surface only.

The tutorial pack SHALL NOT rely on runtime-home hidden mailbox skill paths or on `skills/.system/mailbox/...` copies for the default unattended wake-up turn.

#### Scenario: Copied dummy-project includes mailbox skill documents before start
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the default automatic workflow with the tracked defaults
- **THEN** the provisioned copied dummy-project workdir contains the projected mailbox skill documents under `skills/mailbox/...`
- **AND THEN** the default wake-up turn can use that project-local mailbox skill surface without rediscovering mailbox instructions elsewhere
- **AND THEN** the provisioned workdir does not depend on `skills/.system/mailbox/...` copies for mailbox-skill discovery

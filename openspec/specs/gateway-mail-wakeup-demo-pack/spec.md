# gateway-mail-wakeup-demo-pack Specification

## Purpose
TBD - created by archiving change add-gateway-mail-wakeup-demo-pack. Update Purpose after archive.

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

### Requirement: Automatic workflow SHALL verify idle-session wake-up through a demo-owned output artifact
The tracked default automatic workflow SHALL:

- start one mailbox-enabled CAO-backed agent session,
- attach the gateway for that session,
- enable gateway mail notifier polling with a one-second interval,
- run a demo-owned helper that checks the agent's live status every three seconds and injects one email only after the session is observed idle,
- deliver an instruction that asks the agent to write the current time into a file under the demo-owned output directory, and
- wait for that output file or fail clearly when the wake-up flow does not complete.

The automatic workflow SHALL capture the gateway, mailbox, and output-file artifacts needed to explain the observed result.

#### Scenario: Idle session is woken by one injected mail
- **WHEN** a developer runs the default automatic workflow with prerequisites satisfied
- **THEN** the pack delivers one email after the agent is observed idle
- **AND THEN** the gateway wake-up flow becomes observable through captured gateway and mailbox artifacts
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

- notifier enablement and runtime status,
- gateway decision-audit evidence from durable notifier audit history under the gateway root,
- queue or event evidence for any notifier prompt that was enqueued,
- mailbox-local unread-state evidence for delivered messages, and
- output-file evidence for the automatic wake-up case.

The pack MAY include terminal-tail or transcript inspection as supplemental debugging evidence, but the required golden report SHALL NOT depend on exact model phrasing.

The sanitized golden report SHALL reduce raw notifier audit rows to stable outcome-summary assertions that remain reproducible across runs, and SHALL NOT require an exact per-poll outcome sequence in `expected_report/report.json`.

#### Scenario: Verification report explains why wake-up succeeded or was skipped
- **WHEN** a maintainer runs the tutorial-pack verification flow
- **THEN** the resulting sanitized report includes enough gateway-owned and mailbox-owned evidence to explain whether unread mail caused a wake-up prompt, a busy skip, or another explicit notifier decision
- **AND THEN** the report can be compared reproducibly against `expected_report/report.json`

#### Scenario: Golden report stays stable without exact poll sequencing
- **WHEN** two valid demo runs observe different counts or ordering of empty notifier polls before mail delivery
- **THEN** the sanitized golden report can still compare successfully as long as the required outcome-summary assertions and artifact evidence match
- **AND THEN** any raw per-poll audit rows may remain available separately for debugging without becoming part of the exact golden comparison

### Requirement: Tutorial README SHALL teach the gateway wake-up contract and workflows explicitly
The tutorial README SHALL document:

- a concrete gateway wake-up question or goal,
- prerequisites checklist,
- implementation idea,
- the unread-set notification contract,
- the automatic workflow,
- the manual single-mail and burst-mail workflows,
- explicit run and verify steps mirroring the meaningful runner actions,
- snapshot refresh instructions, and
- an appendix listing key parameters plus input and output files.

The README SHALL explain that gateway notifier behavior is unread-set based and that one reminder prompt may summarize multiple unread messages.

#### Scenario: Reader can understand burst behavior without assuming one reminder per mail
- **WHEN** a developer follows the README to the manual burst-delivery section
- **THEN** the documentation explains that the gateway is notifying “unread mail exists” rather than “one new mail arrived”
- **AND THEN** the reader can distinguish valid unread-set batching behavior from a missed-message failure

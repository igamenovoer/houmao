## ADDED Requirements

### Requirement: Tutorial-pack lifecycle SHALL use demo-owned `houmao-server` and pair-backed runtime session flow
The tracked default gateway wake-up tutorial SHALL start or reuse demo-owned `houmao-server` state under the selected `<demo-output-dir>` and SHALL launch its live mailbox-enabled session with `backend=houmao_server_rest` against that server.

The tutorial pack SHALL treat gateway attach as a post-launch step and SHALL use server-backed managed-agent authority for later attach, notifier control, inspection targeting, and stop behavior rather than depending on demo-owned CAO launcher management.

The tutorial pack SHALL fail clearly when the selected server-backed managed-agent identity cannot be resolved or reused for follow-up manual commands.

#### Scenario: Default start uses demo-owned `houmao-server` and pair-backed session flow
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the default automatic workflow with the tracked defaults
- **THEN** the pack starts or reuses demo-owned `houmao-server` state under the selected demo output root
- **AND THEN** the started live session uses `backend=houmao_server_rest`
- **AND THEN** later attach, notifier, inspect, and stop steps target that same session through server-backed managed-agent authority

### Requirement: Provisioned copied dummy-project workdir SHALL expose project-local mailbox skill documents
The tracked default gateway wake-up tutorial SHALL stage the runtime-owned mailbox skill documents into the provisioned copied dummy-project workdir before the live session starts.

The provisioned workdir SHALL expose the visible `skills/mailbox/...` mailbox skill surface and MAY mirror the same material under `skills/.system/mailbox/...` for compatibility.

The tutorial pack SHALL NOT rely only on runtime-home hidden mailbox skill paths for the default unattended wake-up turn.

#### Scenario: Copied dummy-project includes mailbox skill documents before start
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the default automatic workflow with the tracked defaults
- **THEN** the provisioned copied dummy-project workdir contains the projected mailbox skill documents under `skills/mailbox/...`
- **AND THEN** the default wake-up turn can use that project-local mailbox skill surface without rediscovering mailbox instructions elsewhere

## MODIFIED Requirements

### Requirement: Automatic workflow SHALL verify idle-session wake-up through a demo-owned output artifact
The tracked default automatic workflow SHALL:

- start or reuse demo-owned `houmao-server` under the selected demo output root,
- start one mailbox-enabled `houmao_server_rest` session from the demo-owned copied dummy-project workdir,
- use the tracked lightweight mailbox-demo blueprint defaults for that session,
- attach the gateway for that session as a post-launch step through server-backed managed-agent authority,
- enable gateway mail notifier polling with a one-second interval,
- run a demo-owned helper that checks the live session's readiness through server-backed state first and gateway status as a fallback, injecting one email only after the session is observed idle,
- deliver an instruction that asks the agent to write the current time into a file under the demo-owned output directory, and
- wait for that output file or fail clearly when the wake-up flow does not complete.

The automatic workflow SHALL capture the server, gateway, mailbox, and output-file artifacts needed to explain the observed result.

#### Scenario: Idle session is woken by one injected mail
- **WHEN** a developer runs the default automatic workflow with prerequisites satisfied
- **THEN** the pack starts one mailbox-enabled `houmao_server_rest` session from the tracked copied dummy-project workdir using the lightweight mailbox-demo defaults
- **AND THEN** the pack attaches the gateway and enables notifier polling after launch through the same demo-owned `houmao-server` authority
- **AND THEN** the pack delivers one email after the session is observed idle
- **AND THEN** the gateway wake-up flow becomes observable through captured server, gateway, and mailbox artifacts
- **AND THEN** the agent produces the configured output file under the demo-owned output directory

### Requirement: Tutorial-pack verification SHALL report gateway-owned wake-up evidence and unread-set outcomes
The tutorial-pack verification contract SHALL sanitize non-deterministic values and SHALL report, at minimum:

- demo-owned server lifecycle and managed-agent identity evidence,
- notifier enablement and runtime status,
- gateway decision-audit evidence from durable notifier audit history under the gateway root,
- queue or event evidence for any notifier prompt that was enqueued,
- mailbox-local unread-state evidence for delivered messages, and
- output-file evidence for the automatic wake-up case.

The pack MAY include terminal-tail or transcript inspection as supplemental debugging evidence, but the required golden report SHALL NOT depend on exact model phrasing, exact per-poll notifier sequencing, or CAO-launcher-specific artifacts.

The sanitized golden report SHALL reduce raw notifier audit rows to stable outcome-summary assertions that remain reproducible across runs, and SHALL NOT require an exact per-poll outcome sequence in `expected_report/report.json`.

#### Scenario: Verification report explains why wake-up succeeded or was skipped
- **WHEN** a maintainer runs the tutorial-pack verification flow
- **THEN** the resulting sanitized report includes enough server-backed, gateway-owned, and mailbox-owned evidence to explain whether unread mail caused a wake-up prompt, a busy skip, or another explicit notifier decision
- **AND THEN** the report can be compared reproducibly against `expected_report/report.json`

#### Scenario: Golden report stays stable without exact poll sequencing
- **WHEN** two valid demo runs observe different counts or ordering of empty notifier polls before mail delivery
- **THEN** the sanitized golden report can still compare successfully as long as the required outcome-summary assertions and artifact evidence match
- **AND THEN** any raw per-poll audit rows may remain available separately for debugging without becoming part of the exact golden comparison

### Requirement: Repository SHALL keep automated regression coverage for the gateway wake-up demo-pack fixture contract
The repository SHALL keep automated coverage for the gateway wake-up demo pack that validates the tracked fixture defaults, server-backed lifecycle behavior, copied-project mailbox skill staging, and sanitized report contract.

That automated coverage MAY use deterministic command doubles or artifact fixtures rather than requiring a real local Claude or Codex session in the default test suite.

#### Scenario: Automated coverage detects fixture-default drift
- **WHEN** a maintainer runs the demo pack's automated coverage
- **THEN** the tests fail if the tracked parameters or orchestration behavior drift back to CAO-owned defaults instead of the server-backed pair flow
- **AND THEN** the tests fail if the copied dummy-project no longer stages the expected mailbox skill documents
- **AND THEN** the tests fail if the inspection or sanitized-report contract drifts from the expected artifact structure

### Requirement: Tutorial README SHALL teach the gateway wake-up contract and workflows explicitly
The tutorial README SHALL document:

- a concrete gateway wake-up question or goal,
- prerequisites checklist,
- implementation idea,
- the unread-set notification contract,
- the automatic workflow,
- the manual single-mail and burst-mail workflows,
- the default dummy-project and lightweight mailbox-demo fixture shape,
- the demo-owned `houmao-server` lifecycle and `houmao_server_rest` session backend,
- the post-launch attach model used by the pack,
- explicit run and verify steps mirroring the meaningful runner actions,
- snapshot refresh instructions, and
- an appendix listing key parameters plus input and output files.

The README SHALL explain that gateway notifier behavior is unread-set based and that one reminder prompt may summarize multiple unread messages.

The README SHALL also explain that the gateway wake-up tutorial is a narrow mailbox and runtime-contract demo, so its default fixture shape intentionally uses a copied dummy project rather than a repository worktree.

#### Scenario: Reader understands the server-backed fixture shape and burst behavior
- **WHEN** a developer follows the README through the setup and manual burst-delivery sections
- **THEN** the documentation identifies the tracked dummy-project and lightweight mailbox-demo defaults used by the tutorial
- **AND THEN** it explains that the walkthrough uses demo-owned `houmao-server` plus a `houmao_server_rest` session rather than the older CAO-owned control path
- **AND THEN** it explains that the gateway is notifying “unread mail exists” rather than “one new mail arrived”
- **AND THEN** the reader can distinguish valid unread-set batching behavior from a missed-message failure

## ADDED Requirements

### Requirement: Tutorial-pack defaults SHALL use a copied dummy-project and lightweight mailbox-demo agent fixture
The tracked default gateway wake-up tutorial SHALL provision `<demo-output-dir>/project` by copying a tracked source-only dummy-project fixture into that path and initializing the copied tree as a fresh standalone git-backed workdir before `start-session` runs.

The tracked default started agent SHALL use the lightweight `mailbox-demo` blueprint family rather than the heavyweight `gpu-kernel-coder` family.

The default wake-up tutorial SHALL NOT require the main repository checkout itself to be the launched working directory.

#### Scenario: Default start provisions a copied dummy-project workdir
- **WHEN** a developer runs `scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start` or the default automatic workflow with the tracked defaults
- **THEN** `<demo-output-dir>/project` is copied from a tracked dummy-project fixture
- **AND THEN** the helper initializes that copied tree as a standalone git-backed workdir for the demo run
- **AND THEN** the resulting `project/` path is not a git worktree of the main repository
- **AND THEN** the started managed session uses the tracked lightweight `mailbox-demo` blueprint defaults

#### Scenario: Stale non-managed project directories fail clearly
- **WHEN** the selected `<demo-output-dir>/project` already exists and is not a pack-managed copied dummy-project repo
- **THEN** the tutorial pack fails explicitly instead of silently reusing that directory
- **AND THEN** the failure tells the maintainer to use a fresh demo output directory or remove the stale directory

### Requirement: Repository SHALL keep automated regression coverage for the gateway wake-up demo-pack fixture contract
The repository SHALL keep automated coverage for the gateway wake-up demo pack that validates the tracked fixture defaults, provisioning behavior, and sanitized report contract.

That automated coverage MAY use deterministic command doubles or artifact fixtures rather than requiring a real local Claude or Codex session in the default test suite.

#### Scenario: Automated coverage detects fixture-default drift
- **WHEN** a maintainer runs the demo pack's automated coverage
- **THEN** the tests fail if the tracked parameters or provisioning behavior drift back to repository-worktree or heavyweight-role defaults
- **AND THEN** the tests fail if the inspection or sanitized-report contract drifts from the expected artifact structure

## MODIFIED Requirements

### Requirement: Automatic workflow SHALL verify idle-session wake-up through a demo-owned output artifact
The tracked default automatic workflow SHALL:

- start one mailbox-enabled CAO-backed agent session from the demo-owned copied dummy-project workdir,
- use the tracked lightweight mailbox-demo blueprint defaults for that session,
- attach the gateway for that session,
- enable gateway mail notifier polling with a one-second interval,
- run a demo-owned helper that checks the agent's live status every three seconds and injects one email only after the session is observed idle,
- deliver an instruction that asks the agent to write the current time into a file under the demo-owned output directory, and
- wait for that output file or fail clearly when the wake-up flow does not complete.

The automatic workflow SHALL capture the gateway, mailbox, and output-file artifacts needed to explain the observed result.

#### Scenario: Idle session is woken by one injected mail
- **WHEN** a developer runs the default automatic workflow with prerequisites satisfied
- **THEN** the pack starts one mailbox-enabled session from the tracked copied dummy-project workdir using the lightweight mailbox-demo defaults
- **AND THEN** the pack delivers one email after the agent is observed idle
- **AND THEN** the gateway wake-up flow becomes observable through captured gateway and mailbox artifacts
- **AND THEN** the agent produces the configured output file under the demo-owned output directory

### Requirement: Tutorial README SHALL teach the gateway wake-up contract and workflows explicitly
The tutorial README SHALL document:

- a concrete gateway wake-up question or goal,
- prerequisites checklist,
- implementation idea,
- the unread-set notification contract,
- the automatic workflow,
- the manual single-mail and burst-mail workflows,
- the default dummy-project and lightweight mailbox-demo fixture shape,
- explicit run and verify steps mirroring the meaningful runner actions,
- snapshot refresh instructions, and
- an appendix listing key parameters plus input and output files.

The README SHALL explain that gateway notifier behavior is unread-set based and that one reminder prompt may summarize multiple unread messages.

The README SHALL also explain that the gateway wake-up tutorial is a narrow mailbox and runtime-contract demo, so its default fixture shape intentionally uses a copied dummy project rather than a repository worktree.

#### Scenario: Reader understands the default fixture shape and burst behavior
- **WHEN** a developer follows the README through the setup and manual burst-delivery sections
- **THEN** the documentation identifies the tracked dummy-project and lightweight mailbox-demo defaults used by the tutorial
- **AND THEN** it explains that the gateway is notifying “unread mail exists” rather than “one new mail arrived”
- **AND THEN** the reader can distinguish valid unread-set batching behavior from a missed-message failure

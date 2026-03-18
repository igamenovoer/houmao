## ADDED Requirements

### Requirement: Tutorial pack SHALL provide pack-local real-agent autotest cases
The mailbox roundtrip tutorial pack SHALL provide pack-local real-agent autotest cases for hack-through-testing under `scripts/demo/mailbox-roundtrip-tutorial-pack/`.

The first supported case set SHALL include:

- `real-agent-roundtrip`
- `real-agent-preflight`
- `real-agent-mailbox-persistence`

The pack SHALL implement those cases under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/` and SHALL expose them through a separate `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh` harness.

For each supported case, the pack SHALL provide:

- one `autotest/case-*.sh` executable script that implements the case steps, and
- one same-basename `autotest/case-*.md` companion document that explains how to run and inspect the implemented case.

The separate `autotest/run_autotest.sh` harness SHALL own case selection and dispatch into those executable case scripts. Shared shell libraries and reusable helper functions used by multiple cases SHALL live under `autotest/helpers/`. `run_demo.sh` SHALL remain reserved for tutorial/demo flow commands rather than HTT case selection.

#### Scenario: Maintainer can discover the supported pack-local autotest assets
- **WHEN** a maintainer inspects `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/`
- **THEN** the directory contains one `case-*.sh` executable and one same-basename `case-*.md` companion document per supported real-agent autotest case
- **AND THEN** the `.md` file explains the implemented invocation shape, inspection steps, and expected evidence for that case
- **AND THEN** the `.sh` file is the pack-owned executable implementation of those case steps
- **AND THEN** shared shell libraries and helper functions are located under `autotest/helpers/`
- **AND THEN** `autotest/run_autotest.sh` is the documented entrypoint that selects and runs those cases

### Requirement: Canonical real-agent autotest SHALL use actual local agents and real credentials
The `real-agent-roundtrip` autotest case SHALL use the actual local `claude` and `codex` executables together with real credential profiles resolved by the selected demo blueprints or explicit autotest configuration.

The case SHALL perform one full `start -> mail send -> mail check -> mail reply -> mail check -> verify -> stop` sequence through the existing runtime-owned direct mail path.

The case SHALL NOT satisfy its contract through fake executables, mailbox-file injection, gateway transport commands, or synthetic mailbox-result reconstruction.

#### Scenario: Successful canonical harness run executes one real sender-to-receiver roundtrip
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-roundtrip --demo-output-dir <path>` with the required local tools and credential profiles available
- **THEN** the case starts one sender session and one receiver session through the normal `start-session` path
- **AND THEN** the sender sends one actual mailbox message to the receiver through the direct runtime mail path
- **AND THEN** the receiver checks mail, sends one reply in the same thread, and the sender checks the reply
- **AND THEN** the case finishes with verification and stop while leaving the raw mailbox artifacts under `<path>`

### Requirement: Real-agent autotest SHALL fail fast on missing prerequisites and bounded-timeout failures
Before it starts any live session, each real-agent autotest case SHALL validate the prerequisites it depends on, including required local executables, credential material, output-root ownership, and supported runtime ownership.

When a required prerequisite is missing, unreadable, or incompatible, the case SHALL fail with a non-zero result before any `start-session` call is attempted.

When a live phase exceeds its configured timeout budget, the case SHALL fail explicitly, preserve the current demo output directory, and report pack-local inspect pointers or equivalent persisted diagnostics for the slow sender or receiver instead of synthesizing success.

#### Scenario: Missing prerequisites block the real-agent path before session startup
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-preflight --demo-output-dir <path>` without one required executable or credential profile
- **THEN** the case exits non-zero before any live sender or receiver session starts
- **AND THEN** the failure output identifies the missing prerequisite directly
- **AND THEN** no successful mailbox roundtrip result is reported

#### Scenario: Timed-out live phases preserve evidence instead of hiding the blocker
- **WHEN** a real-agent autotest phase exceeds its configured timeout budget
- **THEN** the case exits non-zero with timeout diagnostics
- **AND THEN** it preserves the current demo output directory and persisted inspect coordinates for both participants
- **AND THEN** it does not replace the missing direct-path result with a synthetic mailbox success payload

### Requirement: Successful real-agent autotest SHALL leave inspectable mailbox files on disk
After a successful real-agent autotest run, the selected demo output directory SHALL still contain the raw mailbox files needed to inspect the completed roundtrip from disk.

At minimum, the case evidence SHALL identify:

- the sender mailbox directory,
- the receiver mailbox directory,
- the canonical send message document path, and
- the canonical reply message document path.

The `real-agent-mailbox-persistence` case SHALL verify those paths after the run has already stopped and SHALL fail if the final mail files are missing or unreadable.

#### Scenario: Maintainer can inspect the final mail files after stop
- **WHEN** a maintainer runs `autotest/run_autotest.sh --case real-agent-mailbox-persistence --demo-output-dir <path>` successfully
- **THEN** the case confirms that the sender and receiver mailbox directories still exist under `<path>/mailbox/`
- **AND THEN** it opens the canonical send and reply Markdown message documents from disk after `stop`
- **AND THEN** its machine-readable case result records the resolved mailbox and message-document paths
- **AND THEN** the maintainer can inspect the completed roundtrip mail from that reported location without re-running the demo

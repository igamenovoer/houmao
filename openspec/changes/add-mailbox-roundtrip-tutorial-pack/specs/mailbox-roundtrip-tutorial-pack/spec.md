## ADDED Requirements

### Requirement: Repository SHALL provide a mailbox roundtrip tutorial pack under `scripts/demo/`
The repository SHALL include a self-contained mailbox roundtrip tutorial-pack directory under `scripts/demo/` that follows the local runnable tutorial-pack pattern used by existing demo packs.

The tutorial pack SHALL include, at minimum:

- `README.md`
- `run_demo.sh`
- `inputs/demo_parameters.json`
- tracked input files for the initial message body and the reply body
- `scripts/sanitize_report.py`
- `scripts/verify_report.py`
- `expected_report/report.json`

#### Scenario: Tutorial-pack layout exists
- **WHEN** a developer inspects the mailbox tutorial-pack directory under `scripts/demo/`
- **THEN** all required files and subdirectories are present

### Requirement: Tutorial-pack runner SHALL follow self-contained execution mechanics
The tutorial-pack `run_demo.sh` SHALL:

- use robust shell mode (`set -euo pipefail`),
- define repository context and a temporary workspace path,
- check prerequisites before execution,
- copy tracked demo inputs into the temporary workspace before runtime commands execute, and
- support `--snapshot-report` mode for expected-report refresh.

The runner SHALL avoid modifying tracked files outside explicit snapshot mode.

#### Scenario: Runner prepares an isolated workspace from tracked inputs
- **WHEN** a developer runs `run_demo.sh`
- **THEN** the runner creates an isolated workspace and copies the tracked tutorial inputs into it before the mailbox workflow starts

### Requirement: Tutorial-pack runner SHALL start two mailbox-enabled sessions on one shared mailbox root
The tutorial-pack runner SHALL build and start two runtime sessions that both use mailbox support against the same filesystem mailbox root while keeping distinct agent identities, mailbox principal ids, and mailbox addresses.

The runner SHALL capture the structured `start-session` output for both agents, including the redacted mailbox binding payload returned by the runtime.

#### Scenario: Two tutorial agents join the same mailbox root
- **WHEN** a developer runs the tutorial pack with prerequisites satisfied
- **THEN** the pack starts two mailbox-enabled sessions that resolve to one shared mailbox root
- **AND THEN** each session receives its own mailbox principal id and mailbox address
- **AND THEN** the run artifacts include the structured startup payloads for both sessions

### Requirement: Tutorial-pack runner SHALL exercise the external-control mailbox roundtrip through runtime `mail` commands
The tutorial-pack runner SHALL demonstrate the mailbox roundtrip through the supported runtime-owned external-control surfaces rather than through direct managed-script invocation.

At minimum, one successful run SHALL perform:

- `mail send` from the first tutorial agent to the second tutorial agent,
- `mail check` for the receiving agent,
- `mail reply` from the second tutorial agent back into the same thread,
- `mail check` for the original sender, and
- `stop-session` for both tutorial agents.

The reply step SHALL use the parent `message_id` returned by the earlier `mail send` result.

#### Scenario: Successful run completes a mailbox roundtrip
- **WHEN** a developer runs the tutorial pack with prerequisites satisfied
- **THEN** the run executes `mail send`, recipient `mail check`, `mail reply`, sender `mail check`, and session-stop steps in order
- **AND THEN** the `mail reply` step uses the `message_id` returned by the earlier `mail send` result as its parent identifier
- **AND THEN** the run artifacts and final report include the structured outputs from the roundtrip steps

### Requirement: Expected report updates SHALL be sanitized and reproducible
Before writing or comparing expected reports, the tutorial tooling SHALL sanitize non-deterministic values such as absolute paths, timestamps, runtime-specific ids, session-manifest locations, and mailbox message identifiers.

Snapshot refresh mode SHALL update the tracked expected report using sanitized content only.

#### Scenario: Snapshot mode refreshes the expected report with sanitized content
- **WHEN** a maintainer runs `run_demo.sh --snapshot-report`
- **THEN** the tutorial updates `expected_report/report.json` using sanitized payloads only
- **AND THEN** no unrelated tracked files are modified by the tutorial workflow

### Requirement: Tutorial README SHALL teach the mailbox roundtrip as explicit operator steps
The tutorial README SHALL document:

- a title plus concrete question/problem statement,
- prerequisites checklist,
- implementation idea,
- critical example code with inline comments,
- inline critical input and output content,
- an explicit step-by-step walkthrough of the underlying runtime commands used for start, send, check, reply, check, and stop,
- verification instructions against `expected_report/report.json`,
- snapshot refresh workflow, and
- an appendix with key parameters plus input/output file inventory.

The README SHALL present `run_demo.sh` as a convenience wrapper rather than as the only documented way to understand the workflow.

#### Scenario: Reader can follow the roundtrip manually from the README
- **WHEN** a new developer follows the README in order
- **THEN** they can run the mailbox roundtrip through the documented runtime commands without hidden setup steps
- **AND THEN** they can compare the final sanitized output against `expected_report/report.json`

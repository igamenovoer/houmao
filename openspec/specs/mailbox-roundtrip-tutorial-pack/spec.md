# mailbox-roundtrip-tutorial-pack Specification

## Purpose
TBD - created by archiving change add-mailbox-roundtrip-tutorial-pack. Update Purpose after archive.

## Requirements

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

The tracked demo parameters SHALL define the default tutorial pair, including:

- a Claude Code blueprint,
- a Codex blueprint,
- the CAO-backed backend choice,
- agent identities,
- mailbox principal/address pairs, and
- message body file references.

The runner SHALL avoid modifying tracked files outside explicit snapshot mode.

#### Scenario: Runner prepares an isolated workspace from tracked inputs
- **WHEN** a developer runs `run_demo.sh`
- **THEN** the runner creates an isolated workspace and copies the tracked tutorial inputs into it before the mailbox workflow starts

### Requirement: Tutorial-pack runner SHALL start two mailbox-enabled sessions on one shared mailbox root
The tutorial-pack runner SHALL build and start two CAO-backed runtime sessions that both use mailbox support against the same filesystem mailbox root while keeping distinct agent identities, mailbox principal ids, and mailbox addresses.

The runner SHALL use blueprint-driven build and start flow for the tutorial pair, with credential selection owned by the blueprint-bound recipes and mailbox enablement expressed through `start-session --mailbox-*` overrides rather than tutorial-specific mailbox recipe files.

The runner SHALL capture the structured `start-session` output for both agents, including the redacted mailbox binding payload returned by the runtime.

The runner SHALL keep demo-specific persistent state minimal and SHALL rely on the runtime's name-addressed tmux/manifest recovery path for follow-up `mail` and `stop-session` targeting whenever that native mechanism is sufficient.

#### Scenario: Two tutorial agents join the same mailbox root
- **WHEN** a developer runs the tutorial pack with prerequisites satisfied
- **THEN** the pack starts two mailbox-enabled sessions that resolve to one shared mailbox root
- **AND THEN** each session receives its own mailbox principal id and mailbox address
- **AND THEN** the run artifacts include the structured startup payloads for both sessions
- **AND THEN** the sessions were started through the tracked blueprints with mailbox flags supplied on `start-session`

### Requirement: Tutorial-pack runner SHALL exercise the external-control mailbox roundtrip through runtime `mail` commands
The tutorial-pack runner SHALL demonstrate the mailbox roundtrip through the supported runtime-owned external-control surfaces rather than through direct managed-script invocation.

At minimum, one successful run SHALL perform:

- `mail send` from the first tutorial agent to the second tutorial agent,
- `mail check` for the receiving agent,
- `mail reply` from the second tutorial agent back into the same thread,
- `mail check` for the original sender, and
- `stop-session` for both tutorial agents.

The reply step SHALL validate and use the parent `message_id` returned by the earlier `mail send` result. If `mail send` does not yield a usable non-empty `message_id`, the runner SHALL fail clearly instead of guessing a reply parent from `mail check`.

#### Scenario: Successful run completes a mailbox roundtrip
- **WHEN** a developer runs the tutorial pack with prerequisites satisfied
- **THEN** the run executes `mail send`, recipient `mail check`, `mail reply`, sender `mail check`, and session-stop steps in order
- **AND THEN** the `mail reply` step uses the `message_id` returned by the earlier `mail send` result as its parent identifier
- **AND THEN** the run artifacts and final report include the structured outputs from the roundtrip steps
- **AND THEN** each `mail` or `stop-session` step targets the correct agent identity without requiring a richer tutorial-owned session-state file

### Requirement: Expected report updates SHALL be sanitized and reproducible
Before writing or comparing expected reports, the tutorial tooling SHALL sanitize non-deterministic values such as:

- `message_id`
- `thread_id`
- `request_id`
- `bindings_version`
- absolute paths
- runtime roots
- session-manifest locations
- timestamps

The sanitization rules SHALL also cover any equivalent runtime-generated identifiers introduced into the structured report during implementation.

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

The README SHALL make the CAO-backed prerequisite and the default Claude Code plus Codex blueprint pair explicit.

The README SHALL present `run_demo.sh` as a convenience wrapper rather than as the only documented way to understand the workflow.

#### Scenario: Reader can follow the roundtrip manually from the README
- **WHEN** a new developer follows the README in order
- **THEN** they can run the mailbox roundtrip through the documented runtime commands without hidden setup steps
- **AND THEN** they can compare the final sanitized output against `expected_report/report.json`

### Requirement: Tutorial-pack runner SHALL manage loopback CAO lifecycle with aligned launcher state by default
When the mailbox roundtrip tutorial pack targets a supported loopback CAO base URL, the runner SHALL manage CAO lifecycle through a demo-local launcher config rather than assuming an ambient CAO server is already configured correctly.

That default loopback path SHALL:

- write a launcher config under the demo-owned output tree,
- start or reuse CAO through `houmao.cao.tools.cao_server_launcher`,
- validate launcher ownership when reuse occurs,
- align `--cao-profile-store` with the launcher-managed CAO home for the selected base URL, and
- stop launcher-managed CAO on cleanup when the current run started it.

#### Scenario: Default loopback run auto-manages CAO
- **WHEN** a developer runs `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh` against the default loopback CAO base URL
- **THEN** the runner creates or reuses a launcher-managed CAO server for that demo run
- **AND THEN** both `start-session` calls receive a `--cao-profile-store` aligned with that launcher-managed CAO context
- **AND THEN** the runner stops the launcher-managed CAO server on cleanup when this run started it

#### Scenario: Demo-local launcher context controls CAO profile-store alignment
- **WHEN** the tutorial runner starts or reuses loopback CAO through its demo-local launcher config
- **THEN** the resolved `--cao-profile-store` comes from that demo-local launcher context rather than from unrelated ambient or repo-wide launcher state
- **AND THEN** both tutorial `start-session` calls use that resolved store consistently

#### Scenario: Cleanup stops only runner-started loopback CAO after partial or interrupted runs
- **WHEN** the default loopback tutorial path has started launcher-managed CAO and the run exits early, is interrupted, or fails before both agent sessions come up
- **THEN** the runner cleanup still stops that launcher-managed CAO if and only if the current run started it
- **AND THEN** the runner does not stop an external or previously running CAO instance that this run did not start

#### Scenario: Reused untracked CAO ownership fails clearly
- **WHEN** the tutorial runner encounters a healthy CAO server at the selected loopback base URL whose ownership cannot be verified through the launcher-managed artifact context
- **THEN** the runner retries through the launcher stop/start recovery path or fails explicitly with ownership diagnostics
- **AND THEN** it does not silently continue against an unknown CAO ownership context

### Requirement: Tutorial-pack documentation and verification SHALL reflect mailbox-local state explicitly
The mailbox roundtrip tutorial pack SHALL teach and verify the current filesystem mailbox state split:

- shared-root `index.sqlite` is shared structural catalog state,
- each resolved mailbox directory owns `mailbox.sqlite` for mailbox-view state,
- gateway notifier remains optional and is not part of the tutorial's core success path.

The README, generated report, and sanitized expected-report contract SHALL surface that state model explicitly enough that a developer following the tutorial is not left with the stale impression that all mutable mailbox state still lives only in the shared root.

#### Scenario: Tutorial output verifies mailbox-local state artifacts
- **WHEN** the tutorial pack completes successfully
- **THEN** its verification flow confirms that the shared mailbox root contains the shared `index.sqlite`
- **AND THEN** it confirms that both tutorial mailbox directories contain mailbox-local `mailbox.sqlite` state
- **AND THEN** the sanitized report masks those concrete paths reproducibly

#### Scenario: Tutorial remains gateway-optional
- **WHEN** a developer follows the mailbox roundtrip tutorial exactly as documented
- **THEN** the tutorial succeeds through runtime `mail send`, `mail check`, `mail reply`, and `stop-session` commands without requiring gateway attach or mail-notifier enablement
- **AND THEN** any gateway notifier discussion is presented as optional follow-up context rather than as a hidden prerequisite

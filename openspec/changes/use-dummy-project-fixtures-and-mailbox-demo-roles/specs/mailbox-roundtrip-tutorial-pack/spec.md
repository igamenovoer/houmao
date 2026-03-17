## MODIFIED Requirements

### Requirement: Tutorial-pack runner SHALL follow self-contained execution mechanics
The tutorial-pack `run_demo.sh` SHALL:

- use robust shell mode (`set -euo pipefail`),
- define repository context and a temporary workspace path,
- check prerequisites before execution,
- copy tracked demo inputs into the temporary workspace before runtime commands execute,
- provision a tracked dummy-project fixture into the demo-local `project/` workdir before runtime commands execute, and
- support `--snapshot-report` mode for expected-report refresh.

The tracked demo parameters SHALL define the default tutorial pair, including:

- a lightweight mailbox-demo Claude blueprint,
- a lightweight mailbox-demo Codex blueprint,
- the CAO-backed backend choice,
- agent identities,
- mailbox principal/address pairs,
- message body file references, and
- the selected dummy-project fixture.

The runner SHALL avoid modifying tracked files outside explicit snapshot mode.

#### Scenario: Runner prepares an isolated workspace from tracked inputs and a dummy project fixture
- **WHEN** a developer runs `run_demo.sh`
- **THEN** the runner creates an isolated workspace and copies the tracked tutorial inputs into it before the mailbox workflow starts
- **AND THEN** it provisions the selected dummy-project fixture into the demo-local `project/` workdir before any `start-session` call
- **AND THEN** the default tutorial parameters reference the dedicated mailbox-demo blueprints rather than the heavyweight GPU-oriented tutorial pair

### Requirement: Tutorial-pack runner SHALL start two mailbox-enabled sessions on one shared mailbox root
The tutorial-pack runner SHALL build and start two CAO-backed runtime sessions that both use mailbox support against the same filesystem mailbox root while keeping distinct agent identities, mailbox principal ids, and mailbox addresses.

The runner SHALL use blueprint-driven build and start flow for the tutorial pair, with credential selection owned by the blueprint-bound recipes and mailbox enablement expressed through `start-session --mailbox-*` overrides rather than tutorial-specific mailbox recipe files.

The runner SHALL pass the provisioned dummy-project workdir under the selected demo-owned output/home tree to both `start-session` calls instead of targeting a git worktree of the main repository.

The runner SHALL capture the structured `start-session` output for both agents, including the redacted mailbox binding payload returned by the runtime.

The runner SHALL keep demo-specific persistent state minimal and SHALL rely on the runtime's name-addressed tmux/manifest recovery path for follow-up `mail` and `stop-session` targeting whenever that native mechanism is sufficient.

#### Scenario: Two tutorial agents join the same mailbox root from the dummy-project workdir
- **WHEN** a developer runs the tutorial pack with prerequisites satisfied
- **THEN** the pack starts two mailbox-enabled sessions that resolve to one shared mailbox root
- **AND THEN** each session receives its own mailbox principal id and mailbox address
- **AND THEN** both `start-session` calls use the provisioned dummy-project workdir under the selected demo-owned output/home tree
- **AND THEN** the run artifacts include the structured startup payloads for both sessions
- **AND THEN** the sessions were started through the tracked mailbox-demo blueprints with mailbox flags supplied on `start-session`

### Requirement: Tutorial README SHALL teach the mailbox roundtrip as explicit operator steps
The tutorial README SHALL document:

- a title plus concrete question/problem statement,
- prerequisites checklist,
- implementation idea,
- critical example code with inline comments,
- inline critical input and output content,
- an explicit step-by-step walkthrough of the underlying runtime commands used for start, send, check, reply, inspect, check, and stop,
- verification instructions against `expected_report/report.json`,
- snapshot refresh workflow, and
- an appendix with key parameters plus input/output file inventory.

The README SHALL make the CAO-backed prerequisite, the default mailbox-demo Claude/Codex blueprint pair, and the default dummy-project workdir explicit.

The README SHALL explain that the tutorial's default fixture shape is intentionally different from full-repository engineering flows, and it SHALL show how a maintainer uses the pack-local inspect/watch surface to check tmux or terminal logs during slow turns.

The README SHALL present `run_demo.sh` as a convenience wrapper rather than as the only documented way to understand the workflow.

#### Scenario: Reader can follow the roundtrip and inspect slow turns from the README
- **WHEN** a new developer follows the README in order
- **THEN** they can run the mailbox roundtrip through the documented runtime commands without hidden setup steps
- **AND THEN** they can identify the dummy-project/lightweight-blueprint fixture shape used by the tutorial
- **AND THEN** they can use the documented inspect/watch workflow to check a slow sender or receiver session
- **AND THEN** they can compare the final sanitized output against `expected_report/report.json`

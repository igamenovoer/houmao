## ADDED Requirements

### Requirement: Mailbox roundtrip demo SHALL expose pack-local automation commands
The mailbox roundtrip tutorial pack SHALL expose pack-local automation through `run_demo.sh` plus helper-owned scripts under `scripts/demo/mailbox-roundtrip-tutorial-pack/`.

The wrapper SHALL support command-style entrypoints for `auto`, `start`, `roundtrip`, `verify`, and `stop`.

The default invocation MAY remain equivalent to `auto`, but the reusable command entrypoints SHALL still be available for maintainer-driven automation.

#### Scenario: Maintainer can discover automation entrypoints in the pack directory
- **WHEN** a maintainer inspects `scripts/demo/mailbox-roundtrip-tutorial-pack/`
- **THEN** the automation entrypoints and helper scripts live inside that pack directory
- **AND THEN** the pack documentation identifies those entrypoints as the supported mailbox-demo automation surface

#### Scenario: Wrapper accepts stepwise automation commands
- **WHEN** a maintainer invokes `run_demo.sh start`, `run_demo.sh roundtrip`, `run_demo.sh verify`, or `run_demo.sh stop`
- **THEN** the wrapper routes to the corresponding pack-owned automation implementation
- **AND THEN** the caller does not need an external test-only orchestration layer to drive those phases

### Requirement: Stepwise automation SHALL reuse one selected demo output directory
The mailbox roundtrip demo automation commands SHALL operate against one caller-selected demo output directory and SHALL preserve the demo-local worktree, mailbox root, runtime root, and reusable state needed between commands.

`start` SHALL prepare or validate the selected demo output directory and SHALL start the live resources needed for a later `roundtrip`.

`roundtrip` SHALL reuse that same prepared demo output directory rather than provisioning an unrelated second workspace.

`verify` and `stop` SHALL also operate against that same selected demo output directory.

#### Scenario: Start then roundtrip reuse the same demo root
- **WHEN** a maintainer runs `run_demo.sh start --demo-output-dir <path>` and later `run_demo.sh roundtrip --demo-output-dir <path>`
- **THEN** both commands operate on the same nested `project/`, `runtime/`, and `shared-mailbox/` layout under `<path>`
- **AND THEN** the roundtrip step uses the demo-local state prepared for that same path

#### Scenario: Verify reuses existing demo outputs
- **WHEN** a maintainer runs `run_demo.sh verify --demo-output-dir <path>` after a successful stepwise or automatic run
- **THEN** verification builds or compares report artifacts from the existing demo outputs at `<path>`
- **AND THEN** it does not require a second unrelated one-shot demo run

### Requirement: Pack-local automation SHALL support scenario-driven regression runs
The mailbox roundtrip tutorial pack SHALL include pack-local automation scripts that can execute named demo scenarios from inside the pack directory.

The scenario automation SHALL write a machine-readable result summary plus per-scenario demo outputs under a caller-selected automation root.

At minimum, the first scenario set SHALL cover:

- the default job-dir behavior with no `--jobs-dir`,
- an explicit `--jobs-dir` override,
- rerun behavior against an existing valid project worktree, and
- explicit failure when an incompatible project directory already exists.

#### Scenario: Scenario runner executes default implicit jobs-dir coverage
- **WHEN** a maintainer runs the pack-local scenario automation for the default scenario set
- **THEN** one scenario verifies that the mailbox demo keeps per-session job dirs under `<demo-output-dir>/project/.houmao/jobs/...` when no jobs-root override is supplied
- **AND THEN** the scenario result is recorded under the selected automation root

#### Scenario: Scenario runner executes rerun and incompatible-project cases
- **WHEN** a maintainer runs the scenario automation for rerun-oriented cases
- **THEN** one scenario verifies reuse of an existing valid project worktree
- **AND THEN** another scenario verifies a clear failure when `<demo-output-dir>/project` exists but is not a valid git worktree

### Requirement: Automation verification SHALL remain sanitized and snapshot-safe
The pack-local automation surface SHALL reuse the mailbox demo's sanitized report contract for both verification and snapshot refresh.

`verify` SHALL support comparison against the tracked expected report and SHALL support explicit snapshot refresh using sanitized content only.

Any additional automation summaries or machine-readable outputs SHALL avoid embedding unsanitized path- or id-dependent report payloads into tracked expected-report updates.

#### Scenario: Verify compares sanitized output from a stepwise run
- **WHEN** a maintainer runs `run_demo.sh verify` after a stepwise or scenario-driven automation run
- **THEN** the command compares sanitized report content against the tracked expected report
- **AND THEN** the verification result is reported through pack-owned automation outputs

#### Scenario: Snapshot refresh uses sanitized content only
- **WHEN** a maintainer runs `run_demo.sh verify --snapshot-report` or the equivalent pack-local automation snapshot flow
- **THEN** the tracked expected report is refreshed from sanitized content only
- **AND THEN** no unrelated tracked files are modified by that snapshot action

### Requirement: Automation cleanup SHALL be reliable for partial or interrupted runs
The pack-local automation surface SHALL preserve the mailbox demo's cleanup guarantees when runs fail partway through or are interrupted.

When live sessions or a demo-managed CAO were started for a selected demo output directory, cleanup SHALL stop only those live resources that belong to that demo state and SHALL avoid stopping external or preexisting resources that the current automation run did not start.

#### Scenario: Partial automation failure still cleans up demo-owned resources
- **WHEN** a stepwise or scenario-driven automation run fails after starting one or more mailbox sessions or demo-managed CAO
- **THEN** cleanup stops the demo-owned live resources associated with that selected demo output directory
- **AND THEN** cleanup artifacts are written under that same demo output directory for diagnosis

#### Scenario: Cleanup does not stop resources not started by the current automation run
- **WHEN** automation reuses preexisting compatible resources that the current run did not start
- **THEN** later stop or cleanup flows avoid stopping those resources merely because the current run referenced them
- **AND THEN** the automation result records that ownership distinction clearly enough for maintainers to diagnose it

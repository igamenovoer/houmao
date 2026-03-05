# cao-server-launcher-demo-pack Specification

## Purpose
TBD - created by archiving change cao-server-launcher-demo-pack. Update Purpose after archive.
## Requirements
### Requirement: Repository SHALL provide a CAO launcher tutorial-pack demo under `scripts/demo/`
The repository SHALL include a self-contained CAO launcher tutorial-pack demo
directory under `scripts/demo/` that follows the local demo pack patterns used
by existing CAO demos.

The demo pack SHALL include, at minimum:

- `README.md`
- `run_demo.sh`
- `inputs/`
- `scripts/sanitize_report.py`
- `expected_report/report.json`

The demo pack MAY include additional helper scripts (for example, verification
helpers) as long as `scripts/sanitize_report.py` remains the canonical
normalization step for expected-report updates.

#### Scenario: Demo pack layout exists
- **WHEN** a developer inspects the tutorial-pack directory under `scripts/demo/`
- **THEN** all required files and subdirectories are present

### Requirement: Demo runner SHALL follow tutorial-pack execution mechanics
The tutorial pack `run_demo.sh` SHALL:

- use robust shell mode (`set -euo pipefail`),
- define repository context and a temporary workspace path,
- check prerequisites before execution,
- copy tracked demo inputs into the temporary workspace, and
- support `--snapshot-report` mode for expected-report refresh.

The runner SHALL avoid modifying tracked files outside explicit snapshot mode.

#### Scenario: Runner performs setup and input-copy steps
- **WHEN** a developer runs `run_demo.sh`
- **THEN** the runner prepares an isolated workspace and copies tracked inputs before launcher commands execute

### Requirement: Demo runner SHALL execute launcher `status`, `start`, and `stop` with structured outputs
The tutorial pack runner SHALL invoke
`python -m gig_agents.cao.tools.cao_server_launcher` for `status`,
`start`, and `stop`, and SHALL capture JSON outputs into the demo workspace for
verification/report generation.

The runner SHALL verify launcher start/stop behavior using artifact paths under
`runtime_root/cao-server/<host>-<port>/`.

#### Scenario: End-to-end run exercises all launcher commands
- **WHEN** a developer runs the demo with prerequisites satisfied
- **THEN** the run executes launcher `status`, `start`, and `stop` in one flow
- **AND THEN** the run report includes parsed results from those JSON outputs

### Requirement: Expected report updates SHALL be sanitized and reproducible
Before writing or comparing expected reports, the demo tooling SHALL sanitize
non-deterministic values (for example absolute paths, timestamps, and transient
IDs) via `scripts/sanitize_report.py`.

Snapshot refresh mode SHALL update the tracked expected report using sanitized
content only.

#### Scenario: Snapshot mode refreshes expected report only
- **WHEN** a maintainer runs `run_demo.sh --snapshot-report`
- **THEN** the demo updates the tracked expected report in-place using sanitized payloads
- **AND THEN** no unrelated tracked files are modified by the demo workflow

### Requirement: Demo README SHALL provide a complete step-by-step usage tutorial
The demo README SHALL document:

- title + question/problem statement,
- prerequisites checklist,
- implementation idea,
- critical example code with rich inline comments,
- inline critical input and output examples,
- explicit run-and-verify walkthrough mirroring meaningful runner steps,
- snapshot refresh workflow, and
- appendix with key parameters plus input/output file inventory.

#### Scenario: Reader can run and verify from README alone
- **WHEN** a new developer follows the README in order
- **THEN** they can run the demo, locate outputs, and perform verification
  against `expected_report/` without hidden setup steps or black-box script assumptions


## MODIFIED Requirements

### Requirement: Repository SHALL provide a mailbox roundtrip tutorial pack under `scripts/demo/`
The repository SHALL include a self-contained mailbox roundtrip tutorial-pack directory under `scripts/demo/` that follows the local runnable tutorial-pack pattern used by existing demo packs.

The tutorial pack SHALL include, at minimum:

- `README.md`
- `run_demo.sh`
- `autotest/run_autotest.sh`
- `inputs/demo_parameters.json`
- tracked input files for the initial message body and the reply body
- `scripts/sanitize_report.py`
- `scripts/verify_report.py`
- `expected_report/report.json`
- `autotest/case-real-agent-roundtrip.md`
- `autotest/case-real-agent-roundtrip.sh`
- `autotest/case-real-agent-preflight.md`
- `autotest/case-real-agent-preflight.sh`
- `autotest/case-real-agent-mailbox-persistence.md`
- `autotest/case-real-agent-mailbox-persistence.sh`
- `autotest/helpers/`

#### Scenario: Tutorial-pack layout includes pack-local autotest assets
- **WHEN** a developer inspects the mailbox tutorial-pack directory under `scripts/demo/`
- **THEN** the required runner, inputs, verification helpers, and expected-report files are present
- **AND THEN** `run_demo.sh` remains the tutorial/demo wrapper while `autotest/run_autotest.sh` is the dedicated HTT harness
- **AND THEN** the `autotest/` directory contains one `case-*.sh` script and one same-basename companion `case-*.md` document for each supported real-agent autotest case
- **AND THEN** shared autotest shell libraries and helper functions live under `autotest/helpers/`

### Requirement: Tutorial README SHALL teach the mailbox roundtrip as explicit operator steps
The tutorial README SHALL document:

- a title plus concrete question/problem statement,
- prerequisites checklist,
- implementation idea,
- critical example code with inline comments,
- inline critical input and output content,
- an explicit step-by-step walkthrough of the underlying runtime commands used for start, send, check, reply, inspect, check, and stop,
- verification instructions against `expected_report/report.json`,
- snapshot refresh workflow,
- the canonical real-agent HTT/autotest path and how it differs from deterministic stand-in regression coverage, and
- the separate responsibilities of `run_demo.sh` versus `autotest/run_autotest.sh`, and
- the implemented `autotest/` directory plus the rule that each supported case ships as a same-basename `.sh` executable and `.md` companion document, and
- the existence of `autotest/helpers/` for shared shell helpers used by multiple cases, and
- an appendix with key parameters plus input/output file inventory.

The README SHALL link to `autotest/run_autotest.sh`, the pack-local `autotest/case-*.md` files, and explain how each matching `autotest/case-*.sh` script executes that case from the tutorial-pack directory itself.

#### Scenario: Reader can discover the canonical real-agent autotest path from the tutorial pack
- **WHEN** a maintainer reads the tutorial-pack README
- **THEN** the README identifies the real-agent HTT/autotest path as the canonical live roundtrip flow
- **AND THEN** it distinguishes `autotest/run_autotest.sh` from `run_demo.sh`
- **AND THEN** it links to the pack-local `autotest/case-*.md` companion docs and matching `autotest/case-*.sh` executables for case-specific steps and evidence

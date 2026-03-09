## ADDED Requirements

### Requirement: Demo prerequisite failures use fork-backed CAO installation guidance
When the launcher tutorial pack requires `cao-server` and the executable is not
available, the demo runner SHALL surface actionable guidance that points users
at a fork-backed CAO installation source.

That guidance SHALL NOT point users at `awslabs/cli-agent-orchestrator` or the
ambiguous package-name install `uv tool install cli-agent-orchestrator`.

#### Scenario: Missing `cao-server` points reader at fork-backed install guidance
- **WHEN** a developer runs the launcher tutorial-pack runner without `cao-server` on `PATH`
- **THEN** the demo exits or skips before attempting launcher actions
- **AND THEN** the reported remediation guidance points at the fork-backed CAO source

## MODIFIED Requirements

### Requirement: Demo README SHALL provide a complete step-by-step usage tutorial
The demo README SHALL document:

- title + question/problem statement,
- prerequisites checklist,
- canonical fork-backed CAO installation guidance when `cao-server` is required,
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

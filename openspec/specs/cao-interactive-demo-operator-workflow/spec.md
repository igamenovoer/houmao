# cao-interactive-demo-operator-workflow Specification

## Purpose
Define the archive boundary for the former CAO interactive demo operator workflow.

## Requirements
### Requirement: Archived CAO demo materials SHALL NOT define the supported operator workflow

The active system contract SHALL NOT require maintainers to keep archived CAO interactive demo wrappers, README walkthroughs, or `run_demo.sh` call shapes under `scripts/demo/legacy/` runnable or synchronized with current runtime behavior.

Archived materials MAY preserve historical recipe-first terms, wrapper names, session-control examples, or debugging notes for reference, but supported operator guidance SHALL come from live CLI, runtime, fixture, and explore surfaces rather than from the archived demo pack.

#### Scenario: Archived demo drift does not block the live contract

- **WHEN** a maintainer finds that an archived interactive demo README or wrapper under `scripts/demo/legacy/` no longer matches the current runtime behavior
- **THEN** that drift does not create a supported operator-workflow regression by itself
- **AND THEN** current operator guidance continues to be defined by the live non-archived docs and runtime contracts

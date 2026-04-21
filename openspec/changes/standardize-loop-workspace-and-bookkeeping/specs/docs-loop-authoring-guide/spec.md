## ADDED Requirements

### Requirement: Loop authoring guide documents workspace and bookkeeping contracts
The loop authoring guide at `docs/getting-started/loop-authoring.md` SHALL explain that authored loop plans carry both a workspace contract and a bookkeeping contract.

The guide SHALL describe:

- the difference between `standard` and `custom` contract postures,
- that standard workspace mode reuses the existing in-repo and out-of-repo workspace-manager styles,
- that standard bookkeeping mode requires explicit declared locations,
- that standard bookkeeping mode does not imply a fixed Houmao-owned subtree under per-agent `kb/`.

#### Scenario: Reader understands standard contract posture
- **WHEN** a reader uses the loop authoring guide to plan a loop run
- **THEN** the guide explains how standard workspace mode maps to the workspace-manager postures
- **AND THEN** it explains that bookkeeping locations are explicit plan-owned paths rather than a fixed directory tree

### Requirement: Loop authoring guide distinguishes bookkeeping from managed memory guidance
The loop authoring guide SHALL explain that managed memory and pairwise-v2 initialize material remain guidance surfaces, not the default mutable bookkeeping ledger for a run.

#### Scenario: Reader does not confuse memo pages with bookkeeping ledgers
- **WHEN** a reader compares pairwise-v2 initialize guidance with the bookkeeping contract model
- **THEN** the guide explains that managed memory carries run guidance and references
- **AND THEN** it does not present managed memory as the default home for mutable loop bookkeeping

# Split Focused and Long-Horizon Test Suites

Status: accepted
Date: 2026-07-13
Related: none

The original plan mixed focused state-transition qualification with long-session pressure testing. These tests have different purposes, operation budgets, and acceptance signals, so the plan now defines two explicit suites.

## Current Decision

TUI state-tracking qualification has two test suites:

1. The short-to-medium suite tests detector state classification and focused transition correctness. A session normally contains one to four user interactions and must stay below five unless the plan records a specific reason that the focused transition cannot be isolated more narrowly. Existing `PS-*` and `MS-*` cases belong to this suite. Harness actions such as waiting, capture, resizing for a resize-specific case, process control, and cleanup do not count as user interactions unless they are the transition stimulus under test.
2. The long-horizon suite applies sustained pressure to state tracking. It contains five `ST-*` sessions, each with at least 20 recorded user operations in one maintained provider session. Each session combines several transition families, and the five-session suite collectively covers every in-scope state-transition family while checking for stale state, drift, oscillation, duplicated outcomes, lost authority, and downstream-consumer failures.

Each suite has its own use case file and acceptance gate. UC-01 owns focused correctness; UC-02 owns long-horizon pressure.

The long-horizon suite complements rather than replaces focused cases. A focused case identifies the first incorrect transition; a long-horizon case tests whether correct behavior survives accumulated history and varied capture cadence.

## Affected Artifacts

- `usecases/README.md`: states the two-suite taxonomy and their separate purposes.
- `usecases/uc-01-qualify-focused-tui-state-transitions.md`: defines focused state/transition coverage, the one-to-four-interaction norm, shared unattended/capture/replay rules, outputs, and acceptance criteria.
- `usecases/uc-02-pressure-test-long-horizon-tui-state-tracking.md`: defines five long-horizon procedures, the 20-operation minimum, aggregate transition-family coverage, pressure oracles, outputs, and acceptance criteria.

## Refinement History

### 2026-07-13 - Initial Decision

- Instruction: Split the test cases into short-to-medium runs, usually fewer than five user interactions, for TUI state detection and transition correctness, and long-horizon tasks with at least 20 steps that cover transition cases and pressure the tracker.
- Applied changes: Classified `PS-*` and `MS-*` as short-to-medium tests, retained `ST-*` as five long-horizon sessions, separated their goals and acceptance gates, and clarified which actions count toward each operation budget.

### 2026-07-13 - Split Use Case Ownership

- Instruction: Represent the two suites as two use case files.
- Applied changes: Assigned focused `PS-*` and `MS-*` qualification to UC-01 and long-horizon `ST-*` pressure testing to UC-02. UC-02 references UC-01 for the shared unattended launch, recording, labeling, and replay contracts.

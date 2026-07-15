# Use Vendored Boltons for Long-Horizon Sessions

Status: accepted
Date: 2026-07-13
Related: `0001-split-focused-and-long-horizon-test-suites.md`

The long-horizon procedures need a realistic, stable codebase so exact prompts and engineering checkpoints do not depend on the Houmao checkout or a network clone. The existing dummy projects are intentionally too small for sustained repository inspection and multi-file tool use.

## Current Decision

UC-02 uses the vendored fixture at `tests/fixtures/test-projects/boltons`, imported from upstream revision `979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe`.

Each provider/session variant receives a fresh run-local copy. The coordinator initializes that copy as a standalone Git repository with a `houmao-baseline` commit and launches the provider from the copied project root. The vendored source remains immutable and contains no nested Git metadata, upstream `.github` automation, or upstream `.omp` skills.

The five ST procedures define exact prompts, key sequences, terminal-control actions, file scopes, response markers, and engineering checkpoints. Runtime expansion is limited to the declared safety prefix, provider-specific placeholder literal, owned tmux pane, and resolved unattended launch command. The coordinator may not improvise a recovery prompt during recording.

Engineering-task outcomes and tracker outcomes remain separate. A missed file, command, response-marker, or test checkpoint is `scenario_task_divergence`; it is not a tracker defect when the visible state sequence remains coherent. Network access, package installation, mutation of the vendored source, or changes outside a procedure's allowed paths are `unsafe_mutation_scope` failures.

## Affected Artifacts

- `usecases/uc-02-pressure-test-long-horizon-tui-state-tracking.md`: defines the copied-project preflight, exact ST-01 through ST-05 operations, project checkpoints, acceptance criteria, outputs, and exception flows.
- `tests/fixtures/test-projects/boltons/README.md`: records the upstream source, pinned revision, import date, and refresh procedure.

## Refinement History

### 2026-07-13 - Adopt the Concrete Test Project

- Instruction: Use the vendored Boltons project to make every long-horizon test case concrete with exact prompts and actions.
- Applied changes: Replaced generic prompt and scratch-file steps with 101 exact Boltons operations, required a fresh baseline copy per session, added deterministic file/test checkpoints, and separated engineering divergence from tracker correctness.

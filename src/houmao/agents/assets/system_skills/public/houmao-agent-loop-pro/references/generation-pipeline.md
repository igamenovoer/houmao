# Generation Pipeline

## Purpose

Use this page for execplan generation stages, one-pass generation, step-by-step generation, finalization, validation, and updates.

## Stage Order

The process model is the first generated authority. Generate stages in this order:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-harness
          -> execplan-skills
              -> execplan-agent-bindings
                  -> execplan-finalize
```

## Process Authority

- `execplan-specs-process` emits the canonical process overview at `execplan/specs/collab/collab-overview.md`.
- The process overview captures phases, events, handoffs, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant, message, state, or record families.
- The process overview includes:
  - Python-style pseudocode in fenced `python` blocks;
  - inline `#` comments explaining conditions, actions, state effects, and stopping points;
  - a high-level Mermaid `sequenceDiagram` in a fenced `mermaid` block.
- Later stages derive concrete contracts and operational surfaces from the process model.
- Do not use a flat `execplan/specs/process.md` as the primary process document.

## Stage Responsibilities

- `execplan-specs-contract`: derive objective, participant, topology, communication, state, record, workspace, and run contracts from the process model.
- `execplan-harness`: generate loop-local harness commands and implementation surfaces from contracts.
- `execplan-skills`: generate shared, event, tick, and operator skills from process, contracts, and harness.
- `execplan-agent-bindings`: generate concrete Houmao agent bindings after generated skills exist.
- `execplan-finalize`: fill support docs, package README, final manifest, metadata, omission notes, and consistency notes.

## High-Level Commands

- `execplan-fast-forward` first materializes `execplan-shell`, then runs all stages in order without optional design questions.
- `execplan-step-by-step` first materializes `execplan-stepwise-shell`, then runs all stages with one-question-at-a-time decisions recorded under `execplan/adrs/`.
- `update-execplan` chooses the earliest affected stage and reruns downstream stages.
- `execplan-finalize` is last and must not add new authoritative behavior that bypasses process, contracts, harness, skills, or agent bindings.

## Update Dependencies

- If the process model changes, rerun all downstream stages.
- If derived contracts change but the process model is stable, rerun harness, skills, agent bindings, and finalization.
- If harness surfaces change, rerun generated skills, agent bindings, and finalization.
- If generated skills change, rerun agent bindings and finalization.
- If only agent bindings change, rerun finalization.
- If only support docs or manifest metadata are stale, rerun finalization only.

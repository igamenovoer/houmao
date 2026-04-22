## Context

Pairwise-v3 extends pairwise-v2 by adding an authored workspace contract, but its current authoring surfaces stop at declaring bookkeeping paths and reporting expectations. Bundle plans can carry supporting files such as `workspace-contract.md`, `reporting.md`, and agent notes, yet there is no plan-owned place to store reusable report or bookkeeping scaffolds that runtime participants can follow.

That gap causes two problems:

1. The authoring agent can describe reporting and bookkeeping obligations without leaving reusable forms behind, so downstream participants must improvise the shape of reports and notes.
2. The workspace-contract guidance correctly avoids imposing one fixed bookkeeping subtree, but the absence of plan-owned templates makes it harder to standardize task-specific bookkeeping for one run while still honoring that flexibility.

This change affects the pairwise-v3 skill assets, its bundle-plan structure, the reporting/workspace guidance, and the user-facing loop-authoring documentation. It does not introduce a new runtime subsystem or a new storage class.

## Goals / Non-Goals

**Goals:**

- Make plan-owned reusable templates a first-class part of pairwise-v3 bundle plans.
- Teach the authoring flow to generate sensible reporting templates from the authored reporting contract.
- Teach the authoring flow to generate sensible bookkeeping templates from the task objective, topology, participant roles, and declared bookkeeping paths.
- Preserve the existing rule that bookkeeping structure is task-specific rather than one fixed global subtree.
- Preserve the separation between authored plan artifacts, mutable run outputs, and runtime-owned recovery files.

**Non-Goals:**

- Defining one universal bookkeeping file layout for all pairwise-v3 runs.
- Replacing runtime-owned recovery records with plan-bundle files.
- Requiring templates for every pairwise-v3 plan, including compact single-file plans.
- Changing pairwise-v3 lifecycle verbs or mail-based control behavior.

## Decisions

### Decision: Template generation belongs to bundle plans, not single-file plans

Pairwise-v3 should treat generated templates as authored support artifacts under the plan output directory. That fits naturally in the existing bundle-plan shape and keeps `plan.md` as the canonical entrypoint while allowing reusable scaffolds to live beside the other authored support files.

When a run needs reusable reporting or bookkeeping templates, the authoring guidance should direct the planner to use bundle form and include a `<plan-output-dir>/templates/` directory. Compact single-file plans remain valid for small runs that do not need this support material.

Alternatives considered:

- Put template bodies inline inside `plan.md`: rejected because it bloats the canonical control contract and makes templates harder to reuse or revise.
- Generate templates into bookkeeping paths directly: rejected because those paths are mutable run surfaces, not authored plan sources.

### Decision: Generated templates are categorized by function, not by one fixed path recipe

The plan-owned template directory should organize reusable artifacts by role, with reporting templates and bookkeeping templates as the primary categories. The exact filenames can be task-shaped, but the guidance should make it easy for readers to find:

- canonical reporting templates derived from the reporting contract
- task-shaped bookkeeping templates derived from the task and declared bookkeeping posture

This gives the authoring agent room to generate useful artifacts such as status reports, handoff notes, checklist-driven review forms, result ledgers, or per-edge bookkeeping scaffolds without freezing the system into one universal schema.

Alternatives considered:

- Require one exact filename set for all runs: rejected because tasks vary too much and existing v3 guidance explicitly avoids one fixed bookkeeping subtree.
- Leave template naming completely unconstrained: rejected because users still need a discoverable structure in the authored plan bundle.

### Decision: Reporting templates should be driven by the reporting contract

The reporting contract already defines the expected fields for peek, completion, recovery, stop, and hard-kill summaries. The authoring guidance should use that contract to synthesize corresponding report templates when those report surfaces are part of the run.

This keeps the generated templates aligned with the normative reporting contract rather than inventing a second reporting model in the template directory.

Alternatives considered:

- Let the authoring agent invent report templates without referencing the reporting contract: rejected because it creates drift between normative reporting expectations and the reusable forms given to participants.

### Decision: Bookkeeping templates should be derived from task posture and ownership boundaries

Bookkeeping templates should be generated only from information the plan already owns:

- objective and completion posture
- topology and delegation shape
- participant roles and responsibilities
- declared bookkeeping paths and write ownership

The guidance should explicitly state that these templates are authored examples or reusable scaffolds, while mutable copies or filled-in artifacts belong in the declared bookkeeping surfaces during execution.

Alternatives considered:

- Standardize bookkeeping around per-agent `kb/` defaults: rejected because v3 intentionally supports custom operator-owned bookkeeping paths.
- Treat templates as runtime state: rejected because templates are authored plan assets, not live execution records.

### Decision: Recovery boundaries remain unchanged

The new template bundle should not change the existing runtime boundary. Runtime-owned recovery state remains under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/...`, and neither reporting templates nor bookkeeping templates should be described as substitutes for those recovery records.

This keeps the storage model simple:

- authored plan bundle: reusable contract and templates
- declared bookkeeping paths: mutable run artifacts
- runtime root: Houmao-owned recovery state

Alternatives considered:

- Reusing template files as live recovery ledgers: rejected because it would blur authored-plan and runtime-owned responsibilities.

## Risks / Trade-offs

- [Template overgeneration] → Mitigation: limit requirements to sensible templates justified by the reporting contract, task objective, topology, and declared bookkeeping posture rather than generating arbitrary files.
- [Boundary confusion between templates and live artifacts] → Mitigation: state explicitly in the skill, spec, and docs that `templates/` is authored source material while mutable filled-in outputs belong in declared bookkeeping paths.
- [Accidental pressure toward bundle form for every run] → Mitigation: keep single-file plans valid for compact runs and require templates only when the run needs reusable support artifacts.
- [Inconsistent template naming across tasks] → Mitigation: require discoverable categories and inventory guidance without imposing one rigid global filename set.

## Migration Plan

1. Add an OpenSpec delta for `houmao-agent-loop-pairwise-v3-skill` covering generated plan-owned template bundles and boundary rules.
2. Update the pairwise-v3 skill assets to add template guidance to bundle-plan structure, authoring instructions, reporting guidance, and workspace-contract guidance.
3. Update `docs/getting-started/loop-authoring.md` so users understand when pairwise-v3 bundle plans should include templates and how those templates relate to bookkeeping paths.
4. Existing plans remain valid; plans without `templates/` continue to work unless an operator explicitly revises them to adopt the new bundle support.
5. Rollback is straightforward: the skill can stop generating `templates/` without changing runtime data formats because the new artifacts are plan-owned authoring outputs.

## Open Questions

- None for proposal scope. The remaining choices are authoring-shape details that can be settled during implementation as long as the spec-level boundaries above are preserved.

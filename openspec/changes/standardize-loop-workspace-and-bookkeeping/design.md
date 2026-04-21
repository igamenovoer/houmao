## Context

Houmao's loop skills already standardize control-plane behavior such as topology, lifecycle vocabulary, reporting, and pairwise-v2 prestart material. What they do not standardize is the operator-facing contract for where agents are expected to work and where they are expected to keep inspection-friendly notes during a run.

That gap is especially visible because Houmao already has an explicit multi-agent workspace surface in `houmao-utils-workspace-mgr`. The workspace-manager skill distinguishes in-repo and out-of-repo layouts, private mutation surfaces, shared visibility surfaces, and launch-profile cwd expectations. Loop plans currently do not reuse that vocabulary, so loop-planned teams can drift into repo-root edits, ad hoc worktrees, and inconsistent bookkeeping locations.

There is also an important repository constraint: Houmao managed memory is not the right home for mutable bookkeeping ledgers. Recent memory guidance deliberately keeps `houmao-memo.md` and contained pages focused on live-agent instructions and durable readable notes, and warns against turning managed memory into runtime scratch or supervision state. That means issue `#29` should not be solved by introducing fixed ledgers under managed memory.

The design therefore needs to:

- reuse the workspace-manager split instead of inventing a loop-only workspace model,
- add a first-class loop contract for workspace and bookkeeping,
- avoid prescribing a fixed subtree under per-agent `kb/`,
- keep the first step at the guidance/spec/template layer rather than requiring new runtime machinery.

## Goals / Non-Goals

**Goals:**

- Give every authored loop plan a first-class workspace contract and bookkeeping contract.
- Provide a standard workspace mode that reuses the existing in-repo and out-of-repo workspace-manager styles.
- Provide a standard bookkeeping mode that defines obligations and visibility without imposing a fixed directory tree.
- Make loop plans declare whether ad hoc worktrees are allowed, where code edits belong, and which shared surfaces are writable.
- Make bookkeeping locations explicit plan-owned paths so operators and participants know where to read and write.
- Let loop plans reference prepared workspace-manager outputs instead of duplicating or improvising workspace posture.
- Update authoring templates and docs so these contracts are visible before a run starts.

**Non-Goals:**

- Do not introduce a new runtime loop engine or filesystem enforcement layer in this change.
- Do not redefine Houmao managed memory as the home for mutable run bookkeeping.
- Do not impose one Houmao-owned subtree shape under per-agent `kb/`.
- Do not require every team to use the standard modes; custom contracts remain supported when the user needs them.
- Do not redesign the existing in-repo or out-of-repo workspace-manager flavors.

## Decisions

### Decision: Add a cross-cutting loop-run contract vocabulary

Loop plans will gain two explicit contract surfaces:

- `workspace_contract`
- `bookkeeping_contract`

These are authored-plan concepts, not runtime-only hidden conventions. They belong in canonical loop plan surfaces and in the corresponding skill references/templates, so operators can inspect them before launch and before handoff.

Why this over embedding the rules inside free-form reporting guidance:

- reporting describes what a master reports, not where participants may mutate state;
- workspace posture must be visible before the run begins, not discovered mid-run;
- bookkeeping needs operator-facing semantics and locations, not only output summaries.

Alternative considered: keep workspace/bookkeeping as loose prose in plan notes. Rejected because that reproduces the current ambiguity and makes standardization impossible to test.

### Decision: Standard workspace mode reuses workspace-manager flavors

The standard workspace mode will not invent a new loop-specific layout. Instead, it will explicitly reuse the existing `houmao-utils-workspace-mgr` postures:

- `standard/in-repo`
- `standard/out-of-repo`

For each standard posture, loop guidance will summarize the loop-relevant operator contract:

- launch visibility surface,
- source-mutation surface,
- shared writable surfaces,
- read-only shared surfaces,
- ad hoc worktree policy,
- relationship to a prepared workspace or to a referenced `workspace.md`.

Why this over a new loop-specific workspace model:

- the workspace-manager skill already owns these semantics;
- a third layout would drift from the existing in-repo/out-of-repo guidance;
- users asked for determinism, not another competing workspace abstraction.

Alternative considered: define a loop-only workspace layout separate from workspace-manager. Rejected because it duplicates responsibility and would quickly diverge from the existing utility skill.

### Decision: Standard bookkeeping mode standardizes semantics, not tree shape

The standard bookkeeping mode will define:

- required bookkeeping categories,
- ownership and visibility expectations,
- update triggers or cadence,
- the rule that every bookkeeping surface must have an explicit declared path.

It will not define a universal directory schema such as `kb/loop-runs/<run_id>/...`.

Why this over a fixed subtree:

- bookkeeping structure is task-specific and user-specific;
- the user explicitly rejected assuming a fixed layout under per-agent `kb/`;
- forcing a universal tree would make the "standard" mode too rigid for real loop workflows.

Alternative considered: standardize a fixed set of files under per-agent `kb/`. Rejected because it overfits one bookkeeping style and conflicts with the need for user-owned task-specific note structure.

### Decision: Explicit bookkeeping paths are mandatory for standard bookkeeping mode

Standard bookkeeping mode will still require the plan to name concrete paths or files for the bookkeeping it expects. The plan may point at one file, several files, or paths outside `kb/`, as long as they are explicit and compatible with the workspace contract.

The authoring guidance should not silently invent a Houmao-owned subtree. When the user has not supplied enough information to identify safe bookkeeping locations, the authoring flow should resolve that explicitly in the plan rather than pretending one fixed layout exists.

Why this over implicit default paths:

- operators need to know where to look without guessing;
- the path is part of the contract between planner, operator, and participants;
- implicit defaults would smuggle a directory policy back into the system.

Alternative considered: keep paths optional in standard mode and let agents choose. Rejected because it does not solve issue `#29`; it simply preserves improvisation.

### Decision: Pairwise, pairwise-v2, and generic all adopt the same contract seams

All three current loop skills will adopt the same high-level contract vocabulary, but each skill will apply it at its own lifecycle seams:

- stable pairwise: authoring, start charter, status/stop reporting contract,
- pairwise-v2: authoring, initialize, start, peek/stop summaries,
- generic: authoring, start charter, status/stop reporting contract.

This keeps the loop family coherent while respecting the different lifecycle surfaces already present in each skill.

Why this over changing only pairwise-v2:

- issue `#28` and `#29` are about loop-planned runs generally, not only enriched pairwise runs;
- limiting the change to v2 would leave stable pairwise and generic with the same ambiguity.

Alternative considered: solve this only in pairwise-v2 because it already has `initialize`. Rejected because workspace and bookkeeping are authored-plan concerns across the whole loop family.

### Decision: Workspace-manager adds a loop-facing summary, not a second planning mode

`houmao-utils-workspace-mgr` will be extended so its existing plans and `workspace.md` can act as loop-facing references for standard workspace mode. The goal is not to give workspace-manager ownership of loop planning, but to let loop plans reuse prepared workspace posture without restating the full layout from scratch.

The summary should cover:

- selected flavor and root,
- per-agent launch cwd or visibility surface,
- writable source location,
- writable shared knowledge location when applicable,
- default read-only shared surfaces,
- ad hoc worktree posture,
- any workspace-specific cautions relevant to loop participants.

Why this over teaching loop skills to restate workspace-manager semantics from memory:

- it keeps workspace semantics owned by the workspace skill;
- it reduces drift between prepared workspaces and loop-plan expectations;
- it avoids teaching multiple loop skills to duplicate in-repo/out-of-repo details.

Alternative considered: have each loop skill restate the full workspace-manager guidance inline. Rejected because it creates copy drift and weakens the separation of responsibilities.

## Risks / Trade-offs

- [Risk] Users may read "standard bookkeeping mode" as a fixed file tree even though the design intends semantic standardization only. -> Mitigation: make the spec and templates state explicitly that bookkeeping locations are declared paths, not a Houmao-owned subtree.
- [Risk] Requiring explicit bookkeeping paths can add friction during authoring. -> Mitigation: keep the standard mode lightweight and let authors declare one small set of concrete files instead of a large structure.
- [Risk] Standard workspace mode could drift from the workspace-manager skill over time. -> Mitigation: make loop plans reference workspace-manager postures and summaries instead of copying the full layout into each loop skill.
- [Risk] This first step improves contracts but does not enforce them at runtime. -> Mitigation: frame the change honestly as a guidance/spec/template change and leave future enforcement as separate follow-up work if still needed.
- [Risk] Operators may expect managed memory to carry bookkeeping because pairwise-v2 already writes initialize material there. -> Mitigation: keep the docs explicit that managed memory is for run guidance and references, while bookkeeping lives in declared workspace paths.

## Migration Plan

1. Add the new `loop-run-contracts` capability spec.
2. Update the loop skill specs to require workspace and bookkeeping contracts in authored plans and run-control guidance.
3. Update the workspace-manager skill spec so prepared workspaces can expose loop-facing standard posture summaries.
4. Update loop plan templates, references, and the loop authoring guide to show the new contract sections.
5. Implement the packaged skill and docs changes without changing the runtime engine.

Rollback is documentation/spec/asset rollback only. No persisted runtime data migration is required for this change.

## Open Questions

None for this proposal. The main contract boundary is now clear: standardize workspace posture and bookkeeping semantics, but keep bookkeeping file placement explicit and plan-owned.

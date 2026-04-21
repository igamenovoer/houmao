# Revise A Pairwise Loop Plan

Use this page when a pairwise-v3 plan already exists, but the user wants to tighten, move, or update it without changing the skill family.

## Inputs

Resolve the current plan location first:
- `<plan-output-dir>/plan.md` for the single-file form
- `<plan-output-dir>/plan.md` plus supporting files for the bundle form

If the user wants a revision but no writable plan directory is known yet, ask for the plan output directory before rewriting files.

## What May Change

- plan output directory or relocation request
- workspace contract mode or declared workspace paths
- objective
- master
- participant set
- delegation authority
- authored topology or descendant relationships
- prestart procedure
- prestart strategy
- routing packet inventory, root packet location, packet freshness marker, or child dispatch tables
- durable initialize page namespace or durable start-charter page namespace
- memo sentinel convention for run-owned blocks
- explicit `operator_preparation_wave` target policy
- gateway mail-notifier interval for `operator_preparation_wave`
- acknowledgement posture
- lifecycle vocabulary or reporting-state terminology
- completion condition
- stop posture
- reporting contract
- timeout-watch policy
- scripts or bundle layout

## Workflow

1. Read the current canonical plan entrypoint first.
2. Preserve the current output directory unless the user explicitly asks to move the plan.
3. Preserve the canonical entrypoint:
   - `plan.md` for the single-file form
   - `plan.md` for the bundle form
4. Re-read the plan as a control contract, not just as prose. Confirm whether the requested change affects:
   - the workspace contract mode or its declared paths and write rules
   - the master or participant set
   - topology or descendant relationships
   - delegation rules
   - routing packet coverage
   - durable initialize or charter material
   - lifecycle vocabulary
   - reporting or stop posture
   - scripts or supporting files
5. If the workspace contract is changing, normalize it again through `references/workspace-contract.md`.
6. If topology or packet coverage changes, revisit graph-tool structural preflight and packet expectations before the plan returns to `ready`.
7. If a current field is materially unclear or would need invention, stop and ask for that exact field.
8. Rewrite the plan so the canonical plan path remains stable and the control fields stay synchronized across `plan.md`, `workspace-contract.md` when present, `prestart.md`, routing packets, reporting, and scripts.
9. Keep runtime-owned recovery files outside the authored workspace contract. If the requested revision would blur that boundary, reject the change or rewrite it explicitly.
10. Write the revised plan back under the selected output directory.
11. Report the canonical revised plan path and any supporting files that changed.

## Guardrails

- Do not invent the plan output directory when the user has not provided one.
- Do not move the plan to a new directory unless the user asked for relocation.
- Do not leave the single-file form without `plan.md`.
- Do not leave the bundle form without `plan.md`.
- Do not leave descendant relationships ambiguous when `initialize` needs to validate routing-packet coverage or explicit preparation-wave targets.
- Do not leave the workspace contract ambiguous when `initialize`, `start`, or `recover_and_continue` must point participants at specific workspace or bookkeeping paths.
- Do not describe explicit `operator_preparation_wave` as the default prestart strategy.
- Do not skip durable initialize page and memo reference-block materialization when managed memory is being used.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text.
- Do not require acknowledgement by default; use `fire_and_proceed` unless the plan explicitly selects `require_ack`.
- Do not use a gateway mail-notifier interval other than `5s` for `operator_preparation_wave` unless the user or plan specifies another interval.
- Do not require runtime intermediate agents to recompute subtree slices that should have been prepared during authoring.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
- Do not store mutable recovery ledgers only inside the authored plan bundle; the recovery record belongs under the runtime root.

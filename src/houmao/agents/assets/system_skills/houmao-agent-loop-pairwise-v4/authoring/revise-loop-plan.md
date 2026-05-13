# Revise A Tree Loop Plan

Use this page when a pairwise-v4 plan already exists, but the user wants to tighten, move, or update it without changing the skill family.

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
- launch-profile references for participants
- routing packet inventory, root packet location, packet freshness marker, or child dispatch tables
- initialize memo-slot expectations or continuation page namespace
- memo sentinel convention for run-owned blocks
- gateway mail-notifier interval
- lifecycle vocabulary or reporting-state terminology
- completion condition
- stop posture
- reporting contract
- source contract summary and carried-forward constraints table
- constraint coverage audit
- generated template inventory or bundle template layout
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
   - source constraints, policy-bearing verbs, and coverage-audit status
   - generated report or bookkeeping templates under the plan bundle
   - scripts or supporting files
5. If the workspace contract is changing, normalize it again through `references/workspace-contract.md`.
6. If topology or packet coverage changes, revisit graph-tool structural preflight and packet expectations before the plan returns to `ready`.
7. If source task notes, user-provided documents with schema-like policy verb patterns, commons, or rulebooks changed, re-run the source-constraint extraction pass, preserve policy verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH`, and update stable `SC-*` IDs only when the old mapping is no longer valid.
8. If a current field is materially unclear or would need invention, write `UNRESOLVED - <reason>` in the affected strict template slot or stop and ask for that exact field when execution would be unsafe.
9. Rewrite the plan so the canonical plan path remains stable and the control fields stay synchronized across `plan.md`, `workspace-contract.md` when present, `prestart.md`, routing packets, reporting, generated templates, agent notes, `constraint-coverage-audit.md`, and scripts.
10. Keep runtime-owned recovery files outside the authored workspace contract. If the requested revision would blur that boundary, reject the change or rewrite it explicitly.
11. Write the revised plan back under the selected output directory.
12. Report the canonical revised plan path and any supporting files that changed.

## Guardrails

- Do not invent the plan output directory when the user has not provided one.
- Do not move the plan to a new directory unless the user asked for relocation.
- Do not leave the single-file form without `plan.md`.
- Do not leave the bundle form without `plan.md`.
- Do not leave a template-bearing run in single-file form; move it to bundle form if the revision adds reusable reporting or bookkeeping templates.
- Do not leave descendant relationships ambiguous when `initialize` needs to validate routing-packet coverage.
- Do not leave the workspace contract ambiguous when `initialize`, `start`, or `recover_and_continue` must point participants at specific workspace or bookkeeping paths.
- Do not remove strict template sections just because a revision does not touch them.
- Do not drop source-constraint IDs, policy-bearing source rules, or `UNRESOLVED - <reason>` markers from a revised plan.
- Do not claim coverage if `constraint-coverage-audit.md` is missing high-salience source rules or has unresolved rows without reasons.
- Do not confuse authored template files with mutable bookkeeping outputs or runtime-owned recovery files.
- Do not skip initialize memo materialization when managed memory is being used.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text.
- Do not require acknowledgement replies before ordinary `start`.
- Do not require runtime intermediate agents to recompute subtree slices that should have been prepared during authoring.
- Do not mix lifecycle action names and observed state names into one ambiguous status field.
- Do not hide plan-critical policy only inside an unreferenced support file.
- Do not omit the Mermaid control graph from the canonical plan surface.
- Do not store mutable recovery ledgers only inside the authored plan bundle; the recovery record belongs under the runtime root.

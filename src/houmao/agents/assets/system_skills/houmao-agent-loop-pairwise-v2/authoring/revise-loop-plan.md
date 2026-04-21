# Revise A Pairwise Loop Plan

Use this page when a pairwise-v2 plan already exists, but the user wants to tighten, move, or update it without changing the skill family.

## Inputs

Resolve the current plan location first:
- `<plan-output-dir>/plan.md` for the single-file form
- `<plan-output-dir>/plan.md` plus supporting files for the bundle form

If the user wants a revision but no writable plan directory is known yet, ask for the plan output directory before rewriting files.

## What May Change

- plan output directory or relocation request
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
4. Keep the control-plane versus execution-plane split intact while revising.
5. Re-validate delegation policy. Silence is not authorization.
6. Re-validate routing packets:
   - `houmao-mgr internals graph high analyze --input <graph.json>`
   - `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants`
   - `houmao-mgr internals graph high packet-expectations --input <graph.json>`
   - one root packet exists for the designated master
   - one child packet exists for each parent-to-child pairwise edge
   - each packet records packet id, intended recipient, immediate driver, plan id plus revision or digest, local role and objective, allowed delegation targets, result-return contract, obligations, and forbidden actions
   - each non-leaf packet has a child dispatch table and exact child packet text or exact references for each allowed child
   - no runtime recipient must infer descendants or recompute graph slices from the full plan
7. Re-validate the selected prestart strategy:
   - `precomputed_routing_packets` remains the default unless the user explicitly selects `operator_preparation_wave`
   - durable initialize pages and exact-sentinel memo reference blocks remain part of the default initialize path when managed memory is being used
   - gateway mail-notifier interval remains `5s` unless the user or plan specifies another interval for `operator_preparation_wave`
   - `operator_preparation_wave` targets delegating or non-leaf participants by default unless the user or plan explicitly changes the set
   - `fire_and_proceed` remains the acknowledgement posture unless the user explicitly selects `require_ack`
8. Re-validate graph semantics:
   - the user agent stays outside the execution loop
   - the master owns the supervision loop
   - pairwise execution edges close locally
9. Re-render the Mermaid graph if topology, completion, or stop posture changed.
10. Refresh the normalized run-charter summary if any user-visible control field changed.
11. Write the revised plan back under the selected output directory, keeping `plan.md` as the canonical entrypoint and the supporting files beside it when the plan uses the bundle form.

## Revision Guardrails

- Do not quietly widen delegation authority while revising another part of the plan.
- Do not drift away from the canonical action names or observed state names while revising related wording.
- Do not change `precomputed_routing_packets` into `operator_preparation_wave` unless the revision says so explicitly.
- Do not move the plan to a new directory unless the revision explicitly asks for relocation.
- Do not silently remove durable initialize pages or exact-sentinel memo reference blocks while revising another part of the plan.
- Do not silently narrow or widen `operator_preparation_wave` targets while revising another part of the plan.
- Do not change `fire_and_proceed` into `require_ack` unless the revision says so explicitly.
- Do not leave stale routing packets or stale plan revisions in place after changing topology, participants, or delegation authority.
- Do not let intermediate runtime agents repair missing, mismatched, or stale packets by graph reasoning from memory or by running graph analysis after `start`.
- Do not leave a stale graph in place after changing the run topology.
- Do not move completion evaluation away from the designated master unless the plan explicitly changes the master.
- Do not default a revised stop posture to graceful termination; keep `interrupt-first` unless the user explicitly changed it.

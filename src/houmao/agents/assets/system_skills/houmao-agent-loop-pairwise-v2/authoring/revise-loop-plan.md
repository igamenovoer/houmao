# Revise A Pairwise Loop Plan

Use this page when a plan already exists, but the user wants to tighten delegation boundaries, change the designated master, revise preparation posture, adjust participant preparation material, revise completion or stop policy, add or remove scripts, or re-render the final graph.

## Workflow

1. Read the current canonical plan entrypoint first:
   - the plan file itself for the single-file form
   - `plan.md` first for the bundle form
2. Identify what is changing:
   - objective
   - master
   - participant set
   - delegation authority
   - authored topology or descendant relationships
   - prestart procedure
   - preparation target policy
   - lifecycle vocabulary or reporting-state terminology
   - standalone participant preparation briefs
   - completion condition
   - stop posture
   - reporting contract
   - timeout-watch policy
   - scripts or plan bundle layout
3. Keep the control-plane versus execution-plane split intact while revising.
4. Preserve the canonical entrypoint:
   - the original plan file for single-file form
   - `plan.md` for bundle form
5. Re-validate the delegation policy. Silence is not authorization.
6. Re-validate participant preparation material:
   - each participant brief remains standalone
   - each brief describes local resources and obligations only
   - no brief depends on hidden upstream assumptions
7. Re-validate the preparation target policy:
   - preparation material may remain available for all participants
   - preparation mail targets delegating/non-leaf participants by default
   - leaf participants are included only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set
8. Re-validate the graph semantics:
   - the user agent stays outside the execution loop
   - the master owns the supervision loop
   - pairwise execution edges close locally
9. Re-render the Mermaid graph if topology, completion, or stop posture changed.
10. Refresh the normalized run-charter summary if any user-visible control field changed.

## Revision Guardrails

- Do not quietly widen delegation authority while revising another part of the plan.
- Do not drift away from the canonical action names or observed state names while revising related wording.
- Do not turn default fire-and-proceed preparation into acknowledgement-gated preparation unless the revision says so explicitly.
- Do not silently widen preparation mail to leaf participants while revising another part of the plan.
- Do not leave a stale graph in place after changing the run topology.
- Do not move completion evaluation away from the designated master unless the plan explicitly changes the master.
- Do not default a revised stop posture to graceful termination; keep `interrupt-first` unless the user explicitly changed it.

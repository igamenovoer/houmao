# Revise A Pairwise Loop Plan

Use this page when a plan already exists, but the user wants to tighten delegation boundaries, change the designated master, revise completion or stop policy, add or remove scripts, or re-render the final graph.

## Workflow

1. Read the current canonical plan entrypoint first:
   - the plan file itself for the single-file form
   - `plan.md` first for the bundle form
2. Identify what is changing:
   - objective
   - master
   - participant set
   - delegation authority
   - completion condition
   - stop posture
   - reporting contract
   - scripts or plan bundle layout
3. Keep the control-plane versus execution-plane split intact while revising.
4. Preserve the canonical entrypoint:
   - the original plan file for single-file form
   - `plan.md` for bundle form
5. Re-validate the delegation policy. Silence is not authorization.
6. Re-validate the graph semantics:
   - the user agent stays outside the execution loop
   - the master owns the supervision loop
   - pairwise execution edges close locally
7. Re-render the Mermaid graph if topology, completion, or stop posture changed.
8. Refresh the normalized run-charter summary if any user-visible control field changed.

## Revision Guardrails

- Do not quietly widen delegation authority while revising another part of the plan.
- Do not leave a stale graph in place after changing the run topology.
- Do not move completion evaluation away from the designated master unless the plan explicitly changes the master.
- Do not default a revised stop posture to graceful termination; keep `interrupt-first` unless the user explicitly changed it.

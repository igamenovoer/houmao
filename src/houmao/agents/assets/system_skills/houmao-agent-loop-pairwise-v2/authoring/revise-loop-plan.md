# Revise A Pairwise Loop Plan

Use this page when a plan already exists, but the user wants to tighten delegation boundaries, change the designated master, revise prestart strategy, adjust routing packets or explicit preparation-wave material, revise completion or stop policy, add or remove scripts, or re-render the final graph.

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
   - prestart strategy
   - routing packet inventory, root packet location, packet freshness marker, or child dispatch tables
   - preparation target policy, when explicit `operator_preparation_wave` is selected
   - lifecycle vocabulary or reporting-state terminology
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
6. Re-validate routing packets:
   - one root packet exists for the designated master
   - one child packet exists for each parent-to-child pairwise edge
   - each packet records packet id, intended recipient, immediate driver, plan id plus revision or digest, local role and objective, allowed delegation targets, result-return contract, obligations, and forbidden actions
   - each non-leaf packet has a child dispatch table and exact child packet text or exact references for each allowed child
   - no runtime recipient must infer descendants or recompute graph slices from the full plan
7. Re-validate the selected prestart strategy:
   - `precomputed_routing_packets` remains the default unless the user explicitly asks for preparation mail, participant warmup, or acknowledgement-gated readiness
   - `operator_preparation_wave` preserves preparation mail targeting to delegating/non-leaf participants by default
   - leaf participants are included in the explicit preparation wave only when the user asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set
8. Re-validate the graph semantics:
   - the user agent stays outside the execution loop
   - the master owns the supervision loop
   - pairwise execution edges close locally
9. Re-render the Mermaid graph if topology, completion, or stop posture changed.
10. Refresh the normalized run-charter summary if any user-visible control field changed.

## Revision Guardrails

- Do not quietly widen delegation authority while revising another part of the plan.
- Do not drift away from the canonical action names or observed state names while revising related wording.
- Do not change `precomputed_routing_packets` into `operator_preparation_wave` unless the revision says so explicitly.
- Do not silently widen explicit preparation-wave mail to leaf participants while revising another part of the plan.
- Do not leave stale routing packets or stale plan revisions in place after changing topology, participants, or delegation authority.
- Do not let intermediate runtime agents repair missing, mismatched, or stale packets by graph reasoning from memory.
- Do not leave a stale graph in place after changing the run topology.
- Do not move completion evaluation away from the designated master unless the plan explicitly changes the master.
- Do not default a revised stop posture to graceful termination; keep `interrupt-first` unless the user explicitly changed it.
